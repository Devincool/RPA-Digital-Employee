"""
社区版客服服务
未完全移除UI界面信号接口
"""
import json
import requests
from core.config import Config
import uiautomation 
import time
import subprocess
import sys
import re
from PyQt5.QtCore import QObject, pyqtSignal

from core.tools import *
from core.cache import DialogCache
from core.tools import XianGuanJia
from core.api_key_manager import APIKeyManager
from core.Product_manager import ProductManager
from core.xianyu_adapter_base import IMAdapterFactory
if Config.IM_VERSION == "1.21.36":
    from core.xianyu_adapter_v1_21_36 import *
elif Config.IM_VERSION == "1.21.18":
    from core.xianyu_adapter_v1_21_18 import *


# TEST
APIKeyManager.set_api_key(os.getenv("DPSK_API_KEY"))

class CustomerService(QObject):
    """客服服务类"""
    
    # 定义信号
    message_received = pyqtSignal(str)  # 接收到新消息的信号
    message_sent = pyqtSignal(str)      # 发送消息的信号
    error_occurred = pyqtSignal(str)    # 错误信号
    # 添加新的状态更新信号
    stats_updated = pyqtSignal(dict)    # 状态更新信号
    
    def __init__(self):
        import time
        start_time = time.time()
        
        super().__init__()  # 必须调用父类的初始化
        super_init_time = time.time()
        print(f"父类初始化耗时: {super_init_time - start_time:.2f}秒")
        
        self.config = Config()
        config_time = time.time()
        print(f"配置加载耗时: {config_time - super_init_time:.2f}秒")
        
        self.app = None
        self.main_window = None
        self.first_message_record = {}
        # 初始化对话缓存 - 使用单例模式
        self.dialog_cache = DialogCache(parent=self)
        cache_time = time.time()
        print(f"对话缓存初始化耗时: {cache_time - config_time:.2f}秒")

        self.price_qutoer = ProductManager()
        
        self.xianguanjia = XianGuanJia()
        xianguanjia_time = time.time()
        print(f"闲管家初始化耗时: {xianguanjia_time - cache_time:.2f}秒")
        
        # 根据版本创建 prompt 生成器并使用缓存
        with open("core/prompt-250205.txt", "r", encoding="utf-8") as f:
                self.system_prompt = f.read()
        prompt_time = time.time()
        print(f"Prompt加载耗时: {prompt_time - xianguanjia_time:.2f}秒")
        
        # 触发确认价格流程但当前需进一步沟通 bool 字典
        self.confirming_price_flag_lut = {}
        # 已给客户报价，需要客户回复确认  bool 字典
        self.client_confirm_flag_lut  = {}
        # 改价缓存
        self.final_price_lut = {}
        # 改价过程客户有异议，经过一轮沟通后再次回复已完成
        self.confirm_price_again_flag = False
        # 自定义前置信息触发记录
        self.custom_pre_message_triggered_record = {}
        # 人工介入次数
        self.human_intervention_times_record = {}
        
        # 从配置获取IM版本并创建对应的适配器
        self.im_adapter = IMAdapterFactory.get_adapter(self.config.IM_VERSION)
        adapter_time = time.time()
        print(f"IM适配器初始化耗时: {adapter_time - prompt_time:.2f}秒")
        
        print(f"总初始化耗时: {adapter_time - start_time:.2f}秒")
        
        # 添加状态计数器
        self._message_count = 0
        self._user_count = set()  # 使用集合存储唯一用户ID
        
    def launch_im_app(self):
        """启动IM软件"""
        import time
        start_time = time.time()
        
        print("[CustomerService] 开始启动IM软件")
        try:
            # 先尝试连接已运行的应用
            try:
                print("[CustomerService] 尝试查找已运行的应用窗口...")
                # 查找闲鱼客服窗口
                self.main_window = uiautomation.PaneControl(Name='闲鱼客服-IM聊天', ClassName='Chrome_WidgetWin_0', Depth=1)
                find_time = time.time()
                print(f"[CustomerService] 查找窗口耗时: {find_time - start_time:.2f}秒")
                
                if self.main_window.Exists(maxSearchSeconds=3):
                    print(f"[CustomerService] 找到已运行的窗口: {self.main_window.Name}")
                    # 确保窗口没有最小化
                    self.main_window.SwitchToThisWindow()
                    self.main_window.SetFocus()
                    self.main_window.SetTopmost(False)
                    switch_time = time.time()
                    print(f"窗口切换耗时: {switch_time - find_time:.2f}秒")
                    return True
                    
            except Exception as e:
                print(f"[CustomerService] 连接已运行应用失败: {str(e)}")
                import traceback
                traceback.print_exc()
                
            # 如果连接失败，则启动新实例
            print("尝试启动新实例...")
            subprocess.Popen(self.config.IM_APP_PATH)
            launch_time = time.time()
            print(f"启动新实例耗时: {launch_time - start_time:.2f}秒")
            print("启动命令已执行")
            
            # 等待应用启动
            print("等待应用启动...")
            time.sleep(5)
            
            # 重新查找窗口
            for i in range(3):  # 尝试3次
                print(f"第{i+1}次尝试查找窗口...")
                try:
                    self.main_window = uiautomation.PaneControl(Name='闲鱼客服-IM聊天', ClassName='Chrome_WidgetWin_0', Depth=1) 
                    if self.main_window.Exists(maxSearchSeconds=3):
                        print(f"找到新启动的窗口: {self.main_window.Name}")
                        # 确保窗口可见
                        self.main_window.SwitchToThisWindow()
                        self.main_window.SetFocus()
                        find_new_time = time.time()
                        print(f"新窗口查找和切换耗时: {find_new_time - launch_time:.2f}秒")
                        return True
                except Exception as e:
                    print(f"第{i+1}次查找窗口失败: {str(e)}")
                time.sleep(2)
                
            print("启动失败: 未能找到应用窗口")
            return False
                
        except Exception as e:
            print(f"[CustomerService] 启动过程发生异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        
    def _search_good_workflow(self, goodname):
        """搜索商品工作流"""
        search_button = self.im_adapter.Search_Good_Flow_search_button
        search_button.Click(simulateMove=False)
        time.sleep(2)  # 延时2s等待窗口加载完成
        
        input_control = self.im_adapter.Search_Good_Flow_input_control
        uiautomation.SetClipboardText(goodname)
        input_control.SendKeys('{Ctrl}v')
        input_control.SendKeys('{Enter}')
        time.sleep(1)  # 延迟一秒等搜索结果
        
        try:
            sendgood_button = self.im_adapter.Search_Good_Flow_sendgood_button
            sendgood_button.Click(simulateMove=False)
            return f"商品{goodname}的链接已发送给客户"
        except Exception as e:
            # TODO: 在输入窗口点一下关闭检索窗
            return "未检索到该商品链接"

    def _check_order_workflow(self, client_id, order_id=""):
        """检查订单工作流"""
        if Config.IM_VERSION == "1.21.31":
            service_button = self.im_adapter.ManageWindow_service_button
            service_button.Click(simulateMove=False)
            
        if order_id != "":
            order_summary = self.xianguanjia.get_order_detail(order_id)
            print(f"大模型解读：{order_summary}")
            return order_summary
        else:
            try:
                # 判断订单是否存在
                order_table_control = self.im_adapter.Check_Order_Flow_order_table_control
                order_table_control.Click(simulateMove=False)
                order_id = self.im_adapter.Check_Order_Flow_order_id
                print(order_id)
                order_summary = self.xianguanjia.get_order_detail(order_id)
                print(f"大模型解读：{order_summary}")
                return order_summary
            except Exception as e:
                print(f"该用户不存在订单")
                return "该用户不存在订单"
            

    def _is_point_in_rect(self, point_x, point_y, rect_x1, rect_y1, rect_x2, rect_y2):
        """ 判断点是否在矩形区域内
        
        Args:
            point_x: 点的x坐标
            point_y: 点的y坐标  
            rect_x1: 矩形左上角x坐标
            rect_y1: 矩形左上角y坐标
            rect_x2: 矩形右下角x坐标
            rect_y2: 矩形右下角y坐标
            
        Returns:
            bool: 点在矩形内返回True,否则返回False
        """
        if (point_x >= rect_x1 and point_x <= rect_x2 and 
            point_y >= rect_y1 and point_y <= rect_y2):
            return True
        return False
    
    def _is_buyer_content(self, point_x, label_x):
        """ 根据聊天对话框最左侧坐标和聊天窗口用户id左侧坐标来判断是不是买家发言
        
        Args:
            point_x: 聊天框左侧坐标
            label_x: 聊天界面用户id左侧坐标
        
        2K 分辨率下 聊天对话框左侧和窗口间距是93  窗口左侧和商品简图右侧间距是74
        """
        if abs(point_x - label_x) <  self._is_buyer_chat_distance*1.04  and abs(point_x - label_x) > self._is_buyer_chat_distance*0.96:
            return True
        return False
    
    def _check_lost_messages(self, client_id, client_last_msg):
        new_msg_cache = []
        try:
            text_msg = self.im_adapter.DialogWindow_last_message_group_control
            if text_msg.TextControl().Name == "我已拍下，待付款":
                self._confirm_price(client_id)
                return new_msg_cache
            
            if self._is_buyer_content(text_msg.BoundingRectangle.left, self.chat_windowx):
                text_msg = text_msg.TextControl().Name
                back_read_index = 2
                while text_msg != client_last_msg:
                    new_msg_cache.append(text_msg)
                    text_msg = self.im_adapter.get_message_group_by_index(back_read_index)
                    if self._is_buyer_content(text_msg.BoundingRectangle.left, self.chat_windowx):
                        text_msg = text_msg.TextControl().Name
                        back_read_index += 1
                    else:
                        break
        except Exception as e:
            print(f"因最后一条是图像信息，获取漏掉消息失败: {str(e)}")
        return new_msg_cache

    def _locate_first_msglistitem(self, bias_x=40, bias_y=80):
        """定位第一个消息列表项"""
        # 以"消息"label为定位，点击消息列表第一个展示的对话窗口
        msg_label = self.im_adapter.MessageList_Control_msg_label
        # 获取msg_label的位置
        x, y = msg_label.BoundingRectangle.left, msg_label.BoundingRectangle.top

        # 获取点击位置的组件信息
        msg_list = self.im_adapter.MessageList_Control_msg_list
        
        msg_index = 0
        for msg_element in msg_list.GetChildren():
            msg_index += 1
            if self._is_point_in_rect(x + bias_x, y + bias_y, msg_element.BoundingRectangle.left, msg_element.BoundingRectangle.top, msg_element.BoundingRectangle.right, msg_element.BoundingRectangle.bottom):
                self.current_msg_index = msg_index
                break
        return msg_element
    
    def stop(self):
        """停止服务"""
        self._is_running = False
        print("正在停止客服服务...")

    def check_new_messages(self):
        """检查新消息"""
        self._is_running = True
        while self._is_running:
            try:
                uiautomation.SetGlobalSearchTimeout(Config.TIMEOUT)
                # 使用适配器替换直接的 uiautomation 调用
                touxiang_group = self.im_adapter.MainWindow_touxiang_group
                
                try:
                    self.chat_windowx = self.im_adapter.MainWindow_chat_windowx
                    screen_shot_control_x = self.im_adapter.DialogWindow_screen_shot_control_x
                    user_id_in_chat_control = self.im_adapter.DialogWindow_user_id_in_chat_control
                    # 理论上的买家聊天框与聊天窗口左侧距离
                    self._is_buyer_chat_distance = (screen_shot_control_x - self.chat_windowx) * self.config.IS_BUYER_CHAT_DISTANCE_RATIO
                except Exception as e:
                    # 刚打开的聊天软件不会显示和用户的聊天界面，获取不到以上数据，需要先点击一下聊天列表
                    clicked_element = self._locate_first_msglistitem()
                    clicked_element.Click(simulateMove=False)
                    screen_shot_control_x = self.im_adapter.DialogWindow_screen_shot_control_x
                    user_id_in_chat_control = self.im_adapter.DialogWindow_user_id_in_chat_control
                    # 理论上的买家聊天框与聊天窗口左侧距离
                    self._is_buyer_chat_distance = (screen_shot_control_x - self.chat_windowx) * self.config.IS_BUYER_CHAT_DISTANCE_RATIO

                while self._is_running:
                    if not self._is_running:
                        break
                    uiautomation.SetGlobalSearchTimeout(Config.TIMEOUT)
                    self.chat_windowx = self.im_adapter.MainWindow_chat_windowx
                    try:
                        # 判断touxiang_group是否有TextControl类型子元素
                        text_controls = touxiang_group.TextControl()
                        
                        new_msg_widget = text_controls
                        new_msg_count = int(new_msg_widget.Name)
                        print(f"新消息条数: {new_msg_count}")
                        while new_msg_count > 0 and self._is_running:
                            msg_count_cache = new_msg_count
                            # 定位到未读消息
                            new_msg_widget.Click(simulateMove=False)
                              
                            clicked_element = self._locate_first_msglistitem()
                            # 获取用户id
                            client_id = remove_special_characters(clicked_element.TextControl(foundIndex=1, Depth=2).Name)

                            # 人工介入超过最大值，不再服务该客户
                            if client_id in self.human_intervention_times_record:
                                if self.human_intervention_times_record[client_id] > self.config.MAX_HUMAN_INTERVENTION_TIMES:
                                    print(f"人工介入超过最大值，不再服务该客户: {client_id}")
                                    time.sleep(1)
                                    continue

                            print(f"用户名称：{client_id}")
    
                            # 获取新消息条数
                            uiautomation.SetGlobalSearchTimeout(self.config.CHAT_SERARH_INTERVAL) # 加快消息读取速度
                            try:
                                client_msg_count = clicked_element.GroupControl(Depth=3).TextControl().Name
                                print(f"用户新消息条数：{client_msg_count}")
                            except Exception as e:
                                print(f"获取新消息条数失败: {str(e)}")
                                client_msg_count = msg_count_cache
                                print(f"用户新消息条数：{client_msg_count}")

                            # 点击打开客户对应的聊天页面
                            clicked_element.Click(simulateMove=False)

                            # 开通闲管家的用户可读取商品链接
                            try:
                                self.good_name = self.im_adapter.ManageWindow_good_name
                                # self.good_name = uiautomation.PaneControl(Name='闲鱼客服-IM聊天', ClassName='Chrome_WidgetWin_0', Depth=1).GroupControl(foundIndex=10, Depth=8).GroupControl(foundIndex=2, Depth=3).GroupControl(foundIndex=2, Depth=1).GroupControl(foundIndex=3, Depth=1).GroupControl(foundIndex=2, Depth=2).TextControl(foundIndex=2, Depth=4)
                                print(f"当前咨询商品标题：{self.good_name}")
                            except Exception as e:
                                n = 0 
                                while n < self.config.CHAT_SEARCH_TIMES:
                                    try:
                                        if Config.IM_VERSION == "1.21.31":
                                            service_button = self.im_adapter.ManageWindow_service_name
                                            service_button.Click(simulateMove=False)
                                            time.sleep(1)
                                        good_table_control = self.im_adapter.ManageWindow_good_table_control
                                        good_table_control.Click(simulateMove = False)
                                        self.good_name = self.im_adapter.ManageWindow_good_name
                                        print(f"当前咨询商品标题：{self.good_name}")
                                        break
                                    except Exception as e:
                                        self.good_name = ""
                                        print(f"未获取到商品标题")    
                                        time.sleep(1) 
                                        n+=1

                            # # TODO： 这里添加个读订单的步骤，一块输入到用户对话前
                            # # 开通闲管家的用户可读取订单状态
                            # try:
                            #     order_table_control = uiautomation.PaneControl(Name='闲鱼客服-IM聊天', ClassName='Chrome_WidgetWin_0', Depth=1).GroupControl(foundIndex=10, Depth=8).GroupControl(foundIndex=2, Depth=3).GroupControl(foundIndex=2, Depth=1).GroupControl(foundIndex=3, Depth=1).TabItemControl(Name='订单', Depth=6)
                            #     order_table_control.Click(simulateMove=False)

                            #     # 读取订单信息
                                

                            # except Exception as e:
                            #     # 未读取到订单
                            #     self.client_order[client_id] = {}

                            # 切换到用户对话页面后至少停留10s钟，如果未到时间则在当前页面持续读取消息
                            start_in_chat_time = time.time()

                            # 获取消息内容  考虑会有多条消息过来，进行合并回复
                            msg_cache = []
                            get_image_msg = False
                            i = 1
                            while i <int(client_msg_count):
                                try:
                                    text_msg = ""
                                    if i == 1:
                                        text_msg = self.im_adapter.DialogWindow_last_message
                                    else:
                                        # text_msg = self.im_adapter.DialogWindow_last_i_message(i)
                                        text_msg = self.im_adapter.get_message_by_index(i)
                                    # 添加触发改价确认流程的判断
                                    if text_msg == "我已拍下，待付款":
                                        self._confirm_price(client_id)
                                        continue
                                    i += 1
                                    # 过滤闲鱼系统消息
                                    for system_message in self.config.SYSTEM_MESSAGE_FILTER:
                                        if system_message in text_msg:
                                            text_msg = ""
                                    print(f"读取消息：{text_msg}")
                                except Exception as e:
                                    pass
                                    # get_image_msg = True
                                    # try:
                                    #     image_msg = uiautomation.PaneControl(Name='闲鱼客服-IM聊天', ClassName='Chrome_WidgetWin_0', Depth=1).GroupControl(foundIndex=10, Depth=8).GroupControl(foundIndex=3, Depth=6).GroupControl(foundIndex=3, Depth=3).GroupControl(Depth=2).GroupControl(foundIndex=i).ImageControl()
                                    #     if image_msg:
                                    #         bitmap = uiautomation.Bitmap.FromControl(image_msg)
                                    #         if not bitmap:
                                    #             print("获取图片Bitmap失败")
                                    #     else:
                                    #         print("获取图片控件失败") 
                                    # except Exception as e:
                                    #     print(f"处理图片消息失败: {str(e)}")
                                    #     bitmap = None
                                    
                                    # # 转换为base64
                                    # image_base64 = bitmap_to_base64(bitmap)
                                    # if image_base64:
                                    #     print("图片转换成功")
                                    #     # 这里可以把base64字符串发送给AI处理
                                    # else:
                                    #     print("图片转换失败")
                                    
                                    # # 调试时可以保存图片
                                    # save_base64_image(image_base64, f"debug_{i}.png")
                                    # # save_bitmap(bitmap, f"debug_{i}.png")
                                    
                                if text_msg != "":
                                    msg_cache.append(text_msg)
                            
                            # 把消息合并后请求大模型回复
                            if len(msg_cache) > 0:
                                last_message = ".".join(msg_cache)
                                print(f"获取到新消息: {last_message}")
                                while last_message != "":
                                    # 添加检查是否处于客户回复"确认"流程
                                    if client_id in self.client_confirm_flag_lut:
                                        if self.client_confirm_flag_lut[client_id]:
                                            if "确认" in last_message:
                                                # 用户已确认最终价格，触发改价流程
                                                self._modify_price(client_id, self.final_price_lut[client_id])
                                                break

                                    # 请求大模型接口回答
                                    reply_msg = self._call_llm_api(client_id, last_message)

                                    # 发送消息之前再检查一下是否有漏掉的用户消息
                                    new_msg_cache = self._check_lost_messages(client_id, msg_cache[0])

                                    if "||" in reply_msg:
                                        # 处理分段回复
                                        first_sentence_to_reply = reply_msg.split("||")[0]
                                        self._send_reply(first_sentence_to_reply)
                                        
                                        second_sentence_to_reply = reply_msg.split("||")[1]
                                        self._send_reply(second_sentence_to_reply)
                                    else:
                                        # 发送回复
                                        self._send_reply(reply_msg)

                                    # 用户已下单，但是未能明确需要怎么改价
                                    if client_id in self.confirming_price_flag_lut:
                                        if self.confirming_price_flag_lut[client_id]:
                                            self._confirm_price(client_id)
                        
                                    if len(new_msg_cache) > 0:
                                        last_message = ".".join(new_msg_cache)
                                        print(str(sys._getframe().f_lineno) + f"获取到漏掉的消息：{last_message}")
                                        new_msg_cache.clear                              
                                    else:
                                        print("回复前无遗漏消息")
                                        last_message = ""

                            # 在首次对话时更新用户信息
                            if not client_id in self.first_message_record:
                                self.first_message_record[client_id] = True
                                self.dialog_cache.update_user_info(client_id, {
                                    "first_chat_time": time.time(),
                                    "last_chat_time": time.time()
                                })
                                if get_image_msg:
                                    self._send_reply("在的")
                                    self.dialog_cache.add_dialog(client_id, "assistant", "在的")

                            # 停留在当前页面并持续读取数据
                            end_in_chat_time = time.time()
                            while end_in_chat_time - start_in_chat_time < self.config.CHAT_STAY_TIME_MIN:
                                msg_cache = []
                                try:
                                    text_msg = ""
                                    for j in range(int(self.config.CHAT_SEARCH_TIMES)):
                                        try:
                                            text_msg = self.im_adapter.DialogWindow_last_message_group_control
                                            if self._is_buyer_content(text_msg.BoundingRectangle.left, self.chat_windowx):
                                                print(f"[debug], l:244 {text_msg.BoundingRectangle.left}   {self.chat_windowx}")
                                                text_msg = text_msg.TextControl().Name
                                                break
                                        except Exception as e:
                                            continue
                                    # 过滤闲鱼系统消息
                                    for system_message in self.config.SYSTEM_MESSAGE_FILTER:
                                        if system_message in text_msg:
                                            text_msg = ""
                                    print(f"读取消息：[debug], l:413, {text_msg}")
                                except Exception as e:
                                    pass
                                   
                                if text_msg != "":
                                    msg_cache.append(text_msg)
                                
                                # 把消息合并后请求大模型回复
                                if len(msg_cache) > 0:
                                    last_message = ".".join(msg_cache)
                                    print(f"获取到新消息: {last_message}")
                                    while last_message != "":
                                        # 添加检查是否处于客户回复"确认"流程
                                        if client_id in self.client_confirm_flag_lut:
                                            if self.client_confirm_flag_lut[client_id]:
                                                if "确认" in last_message:
                                                    # 用户已确认最终价格，触发改价流程
                                                    self._modify_price(client_id, self.final_price_lut[client_id])
                                                    break

                                        # 请求大模型接口回答
                                        reply_msg = self._call_llm_api(client_id, last_message)

                                        # 发送消息之前再检查一下是否有漏掉的用户消息
                                        new_msg_cache = self._check_lost_messages(client_id, msg_cache[0])

                                        if "||" in reply_msg:
                                            # 处理分段回复
                                            first_sentence_to_reply = reply_msg.split("||")[0]
                                            self._send_reply(first_sentence_to_reply)
                                            
                                            second_sentence_to_reply = reply_msg.split("||")[1]
                                            self._send_reply(second_sentence_to_reply)
                                        else:
                                            # 发送回复
                                            self._send_reply(reply_msg)

                                        # 用户已下单，但是未能明确需要怎么改价
                                        if client_id in self.confirming_price_flag_lut and self.confirming_price_flag_lut[client_id]:
                                            self._confirm_price(client_id)
                                        
                                        if len(new_msg_cache) > 0:
                                            last_message = ".".join(new_msg_cache)
                                            print(f"获取到漏掉的消息：{last_message}")
                                            new_msg_cache.clear
                                        else:
                                            last_message = ""
                                end_in_chat_time = time.time()

                            new_msg_count = new_msg_widget.Name
                            print(f"新消息条数: {new_msg_count}")
                            uiautomation.SetGlobalSearchTimeout(self.config.TIMEOUT)


                    except Exception as e:
                        print("no new message")
                         # 没有新消息时检测当前页面是否有客户新消息
                        try:
                            uiautomation.SetGlobalSearchTimeout(self.config.CHAT_SERARH_INTERVAL) # 加快消息读取速度
                            user_id_in_chat_control = self.im_adapter.DialogWindow_user_id_in_chat_control
                            client_id = remove_special_characters(user_id_in_chat_control.Name)

                            # 人工介入超过最大值，不再服务该客户
                            if client_id in self.human_intervention_times_record:
                                if self.human_intervention_times_record[client_id] > self.config.MAX_HUMAN_INTERVENTION_TIMES:
                                    print(f"人工介入超过最大值，不再服务该客户: {client_id}")
                                    time.sleep(1)
                                    continue

                            if not self.dialog_cache.is_client_in_memcache(client_id):
                                # 首次打开软件或手动切换聊天窗口时走该流程
                                # 开通闲管家的用户可读取商品链接
                                try:
                                    self.good_name = self.im_adapter.ManageWindow_good_name
                                    # self.good_name = uiautomation.PaneControl(Name='闲鱼客服-IM聊天', ClassName='Chrome_WidgetWin_0', Depth=1).GroupControl(foundIndex=10, Depth=8).GroupControl(foundIndex=2, Depth=3).GroupControl(foundIndex=2, Depth=1).GroupControl(foundIndex=3, Depth=1).GroupControl(foundIndex=2, Depth=2).TextControl(foundIndex=2, Depth=4)
                                    print(f"当前咨询商品标题：{self.good_name}")

                                    # TEST-TEMP
                                    # self._call_llm_api(client_id, "那你给我算算33台oled 日版128G多少钱")
                                except Exception as e:
                                    n = 0 
                                    while n < self.config.CHAT_SEARCH_TIMES:
                                        try:
                                            if Config.IM_VERSION == "1.21.31":
                                                service_button = self.im_adapter.ManageWindow_service_name
                                                service_button.Click(simulateMove=False)
                                                time.sleep(1)
                                            good_table_control = self.im_adapter.ManageWindow_good_table_control
                                            good_table_control.Click(simulateMove = False)
                                            self.good_name = self.im_adapter.ManageWindow_good_name
                                            print(f"当前咨询商品标题：{self.good_name}")
                                            break
                                        except Exception as e:
                                            self.good_name = ""
                                            print(f"未获取到商品标题")    
                                            time.sleep(1) 
                                            n+=1


                            try:
                                last_message_control = self.im_adapter.DialogWindow_last_message_group_control
                                
                                # 检查最新消息是否为图片
                                is_image = False
                                try:
                                    last_message = last_message_control.TextControl().Name
                                except Exception as e:
                                    is_image = True
                                    last_message = ""
                                    print("检测到图片消息")

                                 # 触发改价确认流程：
                                if last_message == "我已拍下，待付款":
                                    self._confirm_price(client_id)
                                    continue

                                # 在用户确认改价环节，用户对价格有异议，重新报价
                                if client_id in self.confirming_price_flag_lut and client_id in self.final_price_lut and not self.confirm_price_again_flag:
                                    if self.confirming_price_flag_lut[client_id] and self.final_price_lut[client_id] == 0:
                                        self._confirm_price(client_id)
                                        continue

                                # 过滤闲鱼系统消息
                                for system_message in self.config.SYSTEM_MESSAGE_FILTER:
                                    if system_message in last_message:
                                        last_message = ""

                                # 增加人工介入处理逻辑
                                if not self._is_buyer_content(last_message_control.BoundingRectangle.left, self.chat_windowx):
                                    if self.dialog_cache.is_client_in_memcache(client_id):
                                        # 判断是否是人工回复
                                        last_cache_message = self.dialog_cache.get_last_message(client_id)
                                        if last_message != "" and last_message != last_cache_message and last_message not in last_cache_message:
                                            print(f"检测到人工介入，对话内容：{last_message}")
                                            if client_id in self.human_intervention_times_record:
                                                self.human_intervention_times_record[client_id] += 1
                                            else:
                                                self.human_intervention_times_record[client_id] = 1
                                            if self.human_intervention_times_record[client_id] > self.config.MAX_HUMAN_INTERVENTION_TIMES:
                                                # 人工回复，需要遵守人工输入的规则
                                                self.dialog_cache.add_dialog(client_id, "system", "<人工介入>"+ last_message + "</人工介入>")
                                            else:
                                                # 记录人工回复
                                                self.dialog_cache.add_dialog(client_id, "record_only", "<人工介入>"+ last_message + "</人工介入>")

                                # 收集所有买家消息（包括图片标记）
                                msg_cache = []
                                image_detected = False
                                j = 1  # 从最新消息开始
                                while True:
                                    try:
                                        if j == 1:
                                            message_control = last_message_control
                                        else:
                                            message_control = self.im_adapter.get_message_group_by_index(j)

                                        if self._is_buyer_content(message_control.BoundingRectangle.left, self.chat_windowx):
                                            try:
                                                text_msg = message_control.TextControl().Name
                                                # 过滤闲鱼系统消息
                                                for system_message in self.config.SYSTEM_MESSAGE_FILTER:
                                                    if system_message in text_msg:
                                                        text_msg = ""
                                                if text_msg != "":
                                                    msg_cache.append(text_msg)
                                            except Exception as e:
                                                # 标记遇到图片消息
                                                image_detected = True
                                                print(f"检测到图片消息，位置: {j}")
                                            j += 1
                                        else:
                                            break
                                    except Exception as e:
                                        break

                                # 处理消息
                                if len(msg_cache) > 0 or image_detected:
                                    # 如果有图片消息，添加提示
                                    if image_detected:
                                        if len(msg_cache) == 0:
                                            # 只有图片没有文字，请求用文字描述
                                            self._send_reply("抱歉，我收不到图片呢，能用文字描述一下吗？")
                                            self.dialog_cache.add_dialog(client_id, "assistant", "抱歉，我收不到图片呢，能用文字描述一下吗？")
                                            return
                                        # else:
                                        #     # 有图片也有文字，处理文字部分，但提醒图片需要文字描述
                                        #     msg_cache.append("（注：检测到图片消息，如果图片包含重要信息，请用文字描述）")

                                    # 合并所有文字消息
                                    last_message = ".".join(msg_cache)
                                    print(f"获取到新消息: {last_message}")

                                    while last_message != "":
                                        # 检查是否处于客户回复流程
                                        if client_id in self.client_confirm_flag_lut and self.client_confirm_flag_lut[client_id]:
                                            if "确认" in last_message:
                                                # 用户已确认最终价格，触发改价流程
                                                self._modify_price(client_id, self.final_price_lut[client_id])
                                                break

                                        # 请求大模型接口回答
                                        reply_msg = self._call_llm_api(client_id, last_message)

                                        # 发送消息之前再检查一下是否有漏掉的用户消息
                                        new_msg_cache = self._check_lost_messages(client_id, msg_cache[0])

                                        if "||" in reply_msg:
                                            # 处理分段回复
                                            first_sentence_to_reply = reply_msg.split("||")[0]
                                            self._send_reply(first_sentence_to_reply)
                                            
                                            second_sentence_to_reply = reply_msg.split("||")[1]
                                            self._send_reply(second_sentence_to_reply)
                                        else:
                                            # 发送回复
                                            self._send_reply(reply_msg)

                                        # 用户已下单，但是未能明确需要怎么改价
                                        if client_id in self.confirming_price_flag_lut and self.confirming_price_flag_lut[client_id]:
                                            self._confirm_price(client_id)

                                        if len(new_msg_cache) > 0:
                                            last_message = ".".join(new_msg_cache)
                                            print(f"获取到漏掉的消息：{last_message}")
                                            new_msg_cache.clear
                                        else:
                                            last_message = ""
                            except Exception as e:
                                print(f"处理消息失败: {str(e)}")
                                time.sleep(1)

                        except Exception as e:
                            print("获取聊天界面用户id失败")
                            if not self._is_running:
                                break

            except Exception as e:
                print(f"检查新消息失败: {str(e)}")
                if not self._is_running:
                    break
                time.sleep(1)  # 添加短暂延时避免CPU占用过高
                continue  # 继续下一次循环而不是递归调用

    def _send_reply(self, reply):
        """发送回复"""
        try:
            uiautomation.SetClipboardText(reply)
            input_control = self.im_adapter.DialogWindow_input_control
            input_control.SendKeys('{Ctrl}v')
            input_control.SendKeys('{Enter}')
            return True
        except Exception as e:
            print(f"发送回复失败: {str(e)}")
            return False
        

    def _call_llm_api(self, client_id, messages):    
        """调用LLM API进行对话"""
        try:
            print("--------------Call llm to reply---------------")

            # 构建消息列表和工具列表保持不变
            messages_list = []
            messages_list.append({"role": "system", "content": self.system_prompt})
            messages_list.append({"role": "system", "content": self.config.SWITCH_PROMPT_ENDING})

            if not hasattr(self, "good_name"):
                try:
                    self.good_name = self.im_adapter.ManageWindow_good_name
                    # self.good_name = uiautomation.PaneControl(Name='闲鱼客服-IM聊天', ClassName='Chrome_WidgetWin_0', Depth=1).GroupControl(foundIndex=10, Depth=8).GroupControl(foundIndex=2, Depth=3).GroupControl(foundIndex=2, Depth=1).GroupControl(foundIndex=3, Depth=1).GroupControl(foundIndex=2, Depth=2).TextControl(foundIndex=2, Depth=4)
                    print(f"当前咨询商品标题：{self.good_name}")

                    # TEST-TEMP
                    # self._call_llm_api(client_id, "那你给我算算33台oled 日版128G多少钱")
                except Exception as e:
                    n = 0 
                    while n < self.config.CHAT_SEARCH_TIMES:
                        try:
                            if Config.IM_VERSION == "1.21.31":
                                service_button = self.im_adapter.ManageWindow_service_name
                                service_button.Click(simulateMove=False)
                                time.sleep(1)
                            good_table_control = self.im_adapter.ManageWindow_good_table_control
                            good_table_control.Click(simulateMove = False)
                            self.good_name = self.im_adapter.ManageWindow_good_name
                            print(f"当前咨询商品标题：{self.good_name}")
                            break
                        except Exception as e:
                            self.good_name = ""
                            print(f"未获取到商品标题")    
                            time.sleep(1) 
                            n+=1
            
            # 获取历史对话记录
            history = self.dialog_cache.get_history(client_id)
            if len(history):
                # 添加历史对话
                check_current_link_changed = True
                for msg in history:
                    if msg["role"] == "record_only":
                        continue
                    messages_list.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
                    if msg["role"] == "system" and "客户更换访问链接" in msg["content"]:
                        if not self.good_name in msg["content"]:
                            check_current_link_changed = True
                            print("商品链接切换")
                        else:
                            check_current_link_changed = False
                    if msg["role"] == "system" and "客户访问链接标题" in msg["content"]:
                        if self.good_name in msg["content"]:
                           check_current_link_changed = False 
                # 循环退出的时候check_current_link_changed 为False表明未切换进入链接

                if check_current_link_changed:
                    if self.config.SERVICE_VERSION == "PRO":
                        product_detail = self.xianguanjia.get_product_detail_by_title(self.good_name)
                        if product_detail is not None:
                            # 获取商品信息
                            good_info = json.dumps(product_detail, ensure_ascii=False)
                        
                            # 根据商品标题判断商品类别
                            category = product_detail["category"]
                            description = ""
                            if "手柄" in category and "限定版" in category or "游戏卡" in category:
                                description = f"客户更换访问链接，链接标题：{self.good_name},商品详情：{good_info}"
                            else:
                                if "游戏机" in category:
                                    description = ""
                                else:
                                    description = f"客户更换访问链接，链接标题：{self.good_name}"
                            if description:
                                messages_list.append({"role": "system", "content": f"{description}"})
                                # 保存对话记录
                                self.dialog_cache.add_dialog(client_id, "system", f"{description}")

                    elif self.config.SERVICE_VERSION == "BASE":
                        description = f"客户更换访问链接，链接标题：{self.good_name}"
                        messages_list.append({"role": "system", "content": f"{description}"})
                                # 保存对话记录
                        self.dialog_cache.add_dialog(client_id, "system", f"{description}")
            else: 
                if self.config.SERVICE_VERSION == "PRO":
                    # 获取商品信息
                    product_detail = self.xianguanjia.get_product_detail_by_title(self.good_name)
                    if product_detail is not None:
                        good_info = json.dumps(product_detail, ensure_ascii=False)

                        # 根据商品标题判断商品类别
                        category = product_detail["category"]
                        description = ""
                        if "手柄" in category and "限定版" in category or "游戏卡" in category:
                            description = f"客户访问链接标题：{self.good_name},商品详情：{good_info}"
                        else:
                            if "游戏机" in category:
                                description = ""
                            else:
                                description = f"客户访问链接标题：{self.good_name}"
                        if description:
                            messages_list.append({"role": "system", "content": f"{description}"})
                            # 保存对话记录
                            self.dialog_cache.add_dialog(client_id, "system", f"{description}")
                elif self.config.SERVICE_VERSION == "BASE":
                    description = f"客户访问链接标题：{self.good_name}"
                    messages_list.append({"role": "system", "content": f"{description}"})
                    # 保存对话记录
                    self.dialog_cache.add_dialog(client_id, "system", f"{description}")

       
            # 添加当前消息
            messages_list.append({
                "role": "user", 
                "content": f"{messages}"
            })

            # print(f"构建消息列表：{messages_list}")

            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "get_product_price",
                        "description": "查询商品价格，当用户咨询商品价格时触发，用户必须提供要咨询的商品规格",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "product_name": {
                                    "type": "string",
                                    "description": "商品规格，用户咨询时必须提供商品名称或规格",
                                }
                            },
                            "required": ["product_name"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "modify_price",
                        "description": "修改订单价格，当用户下单后要求改价再触发，需要根据用户下单的商品信息修改订单价格",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "new_price": {
                                    "type": "string",
                                    "description": "新的订单价格，用户下单后，需要根据用户下单的商品信息修改订单价格",
                                }
                            },
                            "required": ["new_price"]
                        }
                    }
                },
                {
                    "type": "function", 
                    "function": {
                        "name": "calculate_total_price",
                        "description": "计算多个商品的总价，支持加减乘除基本运算",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "expression": {
                                    "type": "string",
                                    "description": "数学表达式，例如: '258+129' 或 '258*2+129'等",
                                }
                            },
                            "required": ["expression"]
                        }
                    }
                }
            ]
            if self.config.IS_USE_SEND_OTHER_GOOD_LINK:
                tools.append({
                    "type": "function",
                    "function": {
                        "name": "send_other_good_link",
                        "description": "发送其他商品链接，用户需要先给出商品名称，或根据上下文判断出用户需要的版本和型号，但仅在用户要求推送链接时调用。",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "good_name": {
                                    "type": "string",
                                    "description": "商品名称，或根据上下文判断出用户需要的版本和型号",
                                }
                            },
                            "required": ["good_name"]
                        },
                    }
                })
            if self.config.IS_USE_GET_SPECIAL_GOOD_INFO:
                tools.append({
                    "type": "function",
                    "function": {
                        "name": "get_special_good_info",
                        "description": "获取以链接价格来定价的商品信息。该工具为内部工具，使用该工具需要先根据用户咨询判断所咨询商品知识库中是否写明以商品链接报价为准。",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "category": {
                                    "type": "string",
                                    "description": "商品类别，用户咨询的商品类别，如游戏卡带、限定版等",
                                }
                            },
                            "required": ["category"]
                        }
                    }
                })

            if self.config.IS_USE_SEND_CUSTOM_PRE_MESSAGE:
                tools.append({
                    "type": "function",
                    "function": {
                        "name": "send_custom_pre_message",
                        "description": self.config.CUSTOM_PRE_MESSAGE_TRIGGERED_CONDITION,
                    }
                })
            # print(f"构建工具列表：{tools}")

            print("开始请求LLM API...")
            headers = {
            "Authorization": f"Bearer {APIKeyManager.get_api_key()}",
            'Accept': 'application/json',
            "Content-Type": "application/json"
            }
            
            data = {
                "model": self.config.model_name,
                "messages": messages_list,
                "stream": False,
                "frequency_penalty": 1.6,
                "max_tokens": 4096,
                "presence_penalty": 0,
                "response_format": {
                    "type": "text"
                },
                "stop": None,
                "stream": False,
                "stream_options": None,
                "temperature": 1.3,
                "top_p": 1,
                "tools": tools,
                "tool_choice": "auto",
                "logprobs": False,
                "top_logprobs": None
            }

            response = requests.post(self.config.API_BASE_URL + "/chat/completions", headers=headers, json=data)
            response_json = response.json()

            try:
                if 'choices' in response_json:
                    reply = ""
                    if 'content' in response_json['choices'][0]['message']:
                        reply = response_json['choices'][0]['message']['content']

                    if 'tool_calls' in response_json['choices'][0]['message'] and response_json['choices'][0]['message']['tool_calls']:
                        tool_calls = response_json['choices'][0]['message']['tool_calls']
                        if not isinstance(tool_calls, list):
                            tool_calls = [tool_calls]
                        msg_list_added_tool = self._FunctionCall_online(client_id, messages_list, reply, tool_calls)
                        
                        # 使用更新后的消息列表重新请求
                        data["messages"] = msg_list_added_tool
                        response_json = requests.post(self.config.API_BASE_URL + "/chat/completions", headers=headers, json=data).json()
                        print("tool_calls 后", response_json)
                        if 'content' in response_json['choices'][0]['message']:
                            reply = response_json['choices'][0]['message']['content']

                    # 打印思考过程
                    if "<思考>" in reply and "</思考>" in reply:
                        think_content = reply[reply.find("<思考>") + len("<思考>"):reply.find("</思考>")]
                        print(f"思考过程：{think_content}")
                    
                    # 只保留回答内容
                    if "<回答>" in reply:
                        reply = reply[reply.find("<回答>") + len("<回答>"): reply.find("</回答>")].strip()
                    else:
                        if "</思考>" in reply:  
                            reply = reply[reply.find("</思考>") + len("</思考>"):].strip()
                        else:
                            reply = reply.strip()

                    # 再检查一遍xml标签
                    reply = reply.replace("<回答>", "").replace("</回答>", "")
                    # 保存对话记录
                    self.dialog_cache.add_dialog(client_id, "user", messages)
                    self.dialog_cache.add_dialog(client_id, "assistant", reply)
                    
                    # 发送统计数据更新信号
                    self.stats_updated.emit(self.dialog_cache.get_current_stats())

                    print(f"大模型回复：{reply}")
                    return reply
                
            except Exception as e:
                print(f"\n请求API失败，错误信息：{str(e)}")
                if "No valid content received" in str(e):
                    print("继续等待响应...")
                # sys.exit(1)


        except Exception as e:
            print(f"\n请求API失败，错误信息：{str(e)}")
            if "No valid content received" in str(e):
                print("继续等待响应...")
            # sys.exit(1)

                   
    def _confirm_price(self, client_id):
        """价格确认流程, 暂时不使用，尝试大模型改价"""
        # 升级版 触发functioncall 改价
        print("触发改价流程")
        reply = self._call_llm_api(client_id, "我已下单，帮我改价")
        self._send_reply(reply)

        # # 如果已经确认最终价格，只是用户提出了异议，经过沟通后确认可以改价
        # if client_id in self.confirming_price_flag_lut  and client_id in self.final_price_lut:
        #     if self.confirming_price_flag_lut[client_id] and self.final_price_lut[client_id]:
        #         yes_or_no = self._call_llm_api(client_id, "请判断用户是否已确认可以改价.确认请回复True，无法确认请回复False")
        #         if yes_or_no == "True":
        #             self._modify_price(client_id, self.final_price_lut[client_id])
        #         else:
        #             # 重新报价
        #             self.final_price_lut[client_id] = 0
        #             return
            
        #     # 报价环节用户有异议重新确认用户意向
        #     if self.confirming_price_flag_lut[client_id] and not self.final_price_lut[client_id]:
        #         # 重新确认用户意向产品并给出报价
        #         self.final_price_lut[client_id] = int(self._call_llm_api(client_id, "我有意向购买，请根据前面的聊天记录告知我最终价格，只输出数字不含其他信息。如果你不能确认当前我要采购的产品价格，请输出0"))
        #         if self.final_price_lut[client_id] != 0:
        #             # 直接改价无需客户再次确认
        #             self._modify_price(client_id, self.final_price_lut[client_id])
        #             self.confirm_price_again_flag = False  # 重置标志位
        #         else:
        #             print("当前无法确认客户要购买产品的总价，需继续沟通")
        #             # self._send_reply("不好意思，麻烦说下完整的名称")
        #             # self.dialog_cache.add_dialog(client_id, "assistant", "不好意思，麻烦说下完整的名称")
        #             self.confirm_price_again_flag = True

        # else:
        #     # 调用大模型确认改价价格
        #     final_price = int(self._call_llm_api(client_id, "我有意向购买，请根据前面的聊天记录告知我最终价格，只输出数字不含其他信息。如果你不能确认当前我要采购的产品价格，请输出0"))
        #     if final_price != 0:
        #         self._send_reply(f"您要购买的商品总价为{final_price}元，请回复"确认"")
        #         self.dialog_cache.add_dialog(client_id, "assistant", "您要购买的商品总价为{final_price}元，请回复"确认"")
        #         self.client_confirm_flag_lut[client_id]  = True
        #         self.final_price_lut[client_id] = final_price
        #         # 给出最终价格客户有可能还会继续讨价还价或报价有误，此处不能置confirming_price_flag 为False
        #     else:
        #         print("当前无法确认客户要购买产品的总价，需继续沟通")
        #         self._send_reply("需要哪个版本？麻烦说下完整的名称")
        #         self.dialog_cache.add_dialog(client_id, "assistant", "需要哪个版本？麻烦说下完整的名称")

        #     self.confirming_price_flag_lut[client_id] = True

    def _modify_price(self, client_id, new_price):
        """价格修改流程
        注：因IM软件设计问题，有时候用户下单了但是右侧订单并没有订单显示，需要切换聊天窗口再切换来才能显示
        """
        try:
            if Config.IM_VERSION == "1.21.31":
                service_button = self.im_adapter.ManageWindow_service_name
                service_button.Click(simulateMove=False)
                time.sleep(1)
            # 点击订单 Tab 选项卡
            order_table_control = self.im_adapter.ManageWindow_order_table_control
            order_table_control.Click(simulateMove=False)
            try:
                # 查找价格修改按钮
                modify_button = self.im_adapter.ManageWindow_modify_price_button
                modify_button.Click()
                price_edit_control = self.im_adapter.Price_Editwindow_price_edit_control
                price_edit_control.SendKeys(f"{new_price}")
           
                confirm_button = self.im_adapter.Price_Editwindow_confirm_button
                confirm_button.Click()
                self.client_confirm_flag_lut[client_id]  = False
                self.confirming_price_flag_lut[client_id] = False
                return "价格修改成功，可以引导用户付款了"
            except Exception as e:
                # 切换聊天窗口后切回   这里如果切换的聊天窗口如果有消息容易漏，所以改完价后再切换到刚才点击的窗口处理消息
                msg_list = self.im_adapter.MessageList_Control_msg_list
                current_msg_listItem = msg_list.ListItemControl(foundIndex=self.current_msg_index)
                temp_turn_msg_listItem = msg_list.ListItemControl(foundIndex=self.current_msg_index+3)
                temp_turn_msg_listItem.Click(simulateMove=False)
                current_msg_listItem.Click(simulateMove=False)

                if Config.IM_VERSION == "1.21.31":
                    service_button = self.im_adapter.ManageWindow_service_name
                    service_button.Click(simulateMove=False)
                    time.sleep(1)

                # 点击订单 Tab 选项卡
                order_table_control = self.im_adapter.Check_Order_Flow_order_table_control
                order_table_control.Click(simulateMove=False)
                try:
                    # 查找价格修改按钮
                    modify_button = self.im_adapter.ManageWindow_modify_price_button
                    modify_button.Click()
                    price_edit_control = self.im_adapter.Price_Editwindow_price_edit_control
                    price_edit_control.SendKeys(f"{new_price}")
            
                    confirm_button = self.im_adapter.Price_Editwindow_confirm_button
                    confirm_button.Click()
                    self.client_confirm_flag_lut[client_id]  = False
                    self.confirming_price_flag_lut[client_id] = False
                    return "价格修改成功，可以引导用户付款了"

                except Exception as e:
                    print(f"价格修改失败: 无法找到订单")
                    return "价格修改失败，确认用户是否下单"


        except Exception as e:
            print(f"价格修改失败: {str(e)}")
            return "价格修改失败，确认用户是否下单"
        
    def _send_custom_pre_message(self, client_id):
        if client_id not in self.custom_pre_message_triggered_record:
            self.custom_pre_message_triggered_record[client_id] = True
            for message in self.config.CUSTOM_PRE_MESSAGE:
                self._send_reply(message)
            return f"已将商家配置的前置消息发送给用户，请根据用户问题进一步解答。前置消息为：{self.config.CUSTOM_PRE_MESSAGE}"
        else:
            return "已发送过自定义前置信息，直接回答用户问题"

    def _FunctionCall_factory(self, client_id, tool_call, args):
        text_response = ""
        if tool_call['function']['name'] == 'send_other_good_link':
            good_title = self.xianguanjia.get_product_title_by_good_name(args["good_name"])
            if good_title is None:
                text_response = "找不到该商品"
            else:
                text_response = self._search_good_workflow(good_title)
        elif tool_call['function']['name'] == 'get_special_good_info':
            if "游戏机" in args["category"]:
                text_response = "游戏机相关问题请根据上文给出信息解答"
            else:
                text_response = self.xianguanjia.get_product_summary_by_category(args["category"])
        elif tool_call['function']['name'] == 'send_custom_pre_message':
            text_response = self._send_custom_pre_message(client_id)
        elif tool_call['function']['name'] == 'modify_price':
            text_response = self._modify_price(client_id, args["new_price"])
        elif tool_call['function']['name'] == 'calculate_total_price':
            try:
                # 使用eval安全地计算表达式
                result = eval(args["expression"], {"__builtins__": {}}, {})
                text_response = str(result)
            except Exception as e:
                text_response = f"计算错误: {str(e)}"
        elif tool_call['function']['name'] == 'get_product_price':
            related_products = self.price_qutoer.search_sku(args["product_name"])
            print(f"相关商品信息：{related_products}")
            if related_products:
                text_response = f"相关商品信息：{related_products}"
            else:
                text_response = "找不到相关商品"

        return text_response
    
    def _FunctionCall_online(self, client_id, context, reply, tool_calls):
        # # 因deepseek 现在function call 有bug，所以采用临时策略
        # """临时策略："""
        # print(tool_calls)
        # for tool_call in tool_calls:
        #     arguments = tool_call['function']['arguments']
        #     if tool_call['function']['arguments']:
        #         arguments = json.loads(tool_call['function']['arguments'])
        #     text_response = self._FunctionCall_factory(client_id, tool_call, arguments)
        #     context.append({"role": "assistant", "content": f"调用工具：{tool_call['id']}"})
        #     context.append({"role": "user", "content": f"调用工具：{tool_call['id']}, 返回结果为：{text_response}, 请根据返回结果回答问题"})
            
        """正常策略："""
        context.append({"role": "assistant", "content": reply, "tool_calls": tool_calls})
        print(f"获取到工具调用：{tool_calls}")
        for tool_call in tool_calls:
            print(f"工具调用：{tool_call['function']}")
            arguments = tool_call['function']['arguments']
            if tool_call['function']['arguments']:
                arguments = json.loads(tool_call['function']['arguments'])
            text_response = self._FunctionCall_factory(client_id, tool_call, arguments)
            print(f"调用工具：{tool_call['id']}, 返回结果为：{text_response}")
    
            if 'id' in tool_call:   # 绝大部分模型都会返回id并要求填写tool_call_id，但总有那么一两个模型没有
                # noinspection PyTypeChecker
                context.append({"role": "tool", "content": f"{text_response}", "tool_call_id": tool_call['id']})
            else:
                context.append({"role": "tool", "content": f"{text_response}"})

        return context    

    def run(self):
        print("[CustomerService] 开始运行服务")
        try:
            if self.launch_im_app():
                print("[CustomerService] IM应用启动成功，开始检查消息")
                self.check_new_messages()
                # self._confirm_price("gulu")
                # self._modify_price("gulu", 100)
                
                print("[CustomerService] 客服服务已停止")
            else:
                print("[CustomerService] IM应用启动失败")
                sys.exit(1)
        except Exception as e:
            print(f"[CustomerService] 运行服务时发生异常: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    cs = CustomerService()
    try:
        if cs.launch_im_app():
            print("IM app launched successfully")
            cs.check_new_messages()
            # cs._confirm_price()
            # cs._modify_price(100)
        else:
            print("IM app failed to launch")
            # sys.exit(1)
    except KeyboardInterrupt:
        print("\n检测到退出信号，正在停止服务...")
        cs.stop()
        # sys.exit(0)


    # TEST

    # cs._modify_price(200)
    # cs._search_good_workflow("OCR")
    # cs._send_reply("你好，我是客服小明。有什么可以帮您的？")
    # cs._confirm_price()
    # cs._modify_price(100)
    # cs.get_active_customers()
    # cs.chat_with_ai_agent("你好，我是客服小明。有什么可以帮您的？")

    # print(_call_llm_api("ctx-20241220214910-qchq6", "你好，这个怎么卖"))

#     csv_string = """一级类目,二级类目,三级类目,四级类目,价格
# Joycon手柄,手柄左右一对,基本全新,,258
# Joycon手柄,手柄左右一对,99新,,238
# Joycon手柄,手柄左右一对,95新,,228
# Joycon手柄,手柄左右一对,9新,,218
# Joycon手柄,手柄左右一对,5-8新,,198
# Joycon手柄,手柄单左,基本全新,,129
# Joycon手柄,手柄单左,99新,,119
# Joycon手柄,手柄单左,95新,,114
# Joycon手柄,手柄单左,9新,,109
# Joycon手柄,手柄单左,5-8新,,99
# Joycon手柄,手柄单右,基本全新,,144
# Joycon手柄,手柄单右,99新,,134
# Joycon手柄,手柄单右,95新,,129
# Joycon手柄,手柄单右,9新,,124
# Joycon手柄,手柄单右,5-8新,,114
# """
#     prompt = trans_csv_2_prompt(csv_string)
    