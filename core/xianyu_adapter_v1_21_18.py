from core.xianyu_adapter_base import IMAdapterBase, IMAdapterFactory
import uiautomation

class IMAdapterV1_21_18(IMAdapterBase):
    """1.21.18版本的适配器实现"""
    
    @property
    def MainWindow_touxiang_group(self):
        return uiautomation.PaneControl(Name='闲鱼客服-IM聊天', ClassName='Chrome_WidgetWin_0', Depth=1).GroupControl(Depth=10)
    
    @property
    def MainWindow_chat_windowx(self):
        return uiautomation.PaneControl(Name='闲鱼客服-IM聊天', ClassName='Chrome_WidgetWin_0', Depth=1).GroupControl(foundIndex=11, Depth=8).GroupControl(foundIndex=3, Depth=6).BoundingRectangle.left

    @property
    def Search_Good_Flow_search_button(self):
        return uiautomation.PaneControl(Name='闲鱼客服-IM聊天', ClassName='Chrome_WidgetWin_0', Depth=1).GroupControl(foundIndex=11, Depth=8).GroupControl(foundIndex=3, Depth=6).GroupControl(foundIndex=5, Depth=1)
    
    @property
    def Search_Good_Flow_input_control(self):
        return uiautomation.PaneControl(Name='闲鱼客服-IM聊天', ClassName='Chrome_WidgetWin_0', Depth=1).GroupControl(foundIndex=2, Depth=3).GroupControl(foundIndex=2, Depth=1).EditControl(Depth=2)
    
    @property
    def Search_Good_Flow_sendgood_button(self):
        return uiautomation.PaneControl(Name='闲鱼客服-IM聊天', ClassName='Chrome_WidgetWin_0', Depth=1).GroupControl(foundIndex=2, Depth=3).GroupControl(foundIndex=4, Depth=1).ButtonControl(Name='发送商品', Depth=1)

    @property
    def Check_Order_Flow_order_table_control(self):
        return uiautomation.PaneControl(Name='闲鱼客服-IM聊天', ClassName='Chrome_WidgetWin_0', Depth=1).GroupControl(foundIndex=11, Depth=8).GroupControl(foundIndex=2, Depth=3).GroupControl(foundIndex=2, Depth=1).GroupControl(foundIndex=3, Depth=1).TabItemControl(Name='订单', Depth=6)
    
    @property
    def Check_Order_Flow_order_id(self):
        return uiautomation.PaneControl(Name='闲鱼客服-IM聊天', ClassName='Chrome_WidgetWin_0', Depth=1).GroupControl(foundIndex=11, Depth=8).GroupControl(foundIndex=2, Depth=3).GroupControl(foundIndex=2, Depth=1).GroupControl(foundIndex=3, Depth=1).GroupControl(foundIndex=2, Depth=2).GroupControl(foundIndex=2, Depth=3).GroupControl(Depth=3).TextControl().Name

    @property
    def MessageList_Control_msg_label(self):
        return uiautomation.PaneControl(Name='闲鱼客服-IM聊天', ClassName='Chrome_WidgetWin_0', Depth=1).GroupControl(foundIndex=11, Depth=8).TextControl(Name='消息', Depth=7)
    
    @property
    def MessageList_Control_msg_list(self):
        return uiautomation.PaneControl(Name='闲鱼客服-IM聊天', ClassName='Chrome_WidgetWin_0', Depth=1).GroupControl(foundIndex=11, Depth=8).GroupControl(foundIndex=2, Depth=6).GroupControl(Depth=2)

    @property
    def DialogWindow_screen_shot_control_x(self):
        return uiautomation.PaneControl(Name='闲鱼客服-IM聊天', ClassName='Chrome_WidgetWin_0', Depth=1).GroupControl(foundIndex=11, Depth=8).GroupControl(foundIndex=3, Depth=6).GroupControl(foundIndex=2, Depth=3).ImageControl(Depth=1).BoundingRectangle.right
    
    @property
    def DialogWindow_user_id_in_chat_control(self):
        return uiautomation.PaneControl(Name='闲鱼客服-IM聊天', ClassName='Chrome_WidgetWin_0', Depth=1).GroupControl(foundIndex=11, Depth=8).GroupControl(foundIndex=3, Depth=6).TextControl()
    
    @property
    def DialogWindow_last_message_group_control(self):
        return uiautomation.PaneControl(Name='闲鱼客服-IM聊天', ClassName='Chrome_WidgetWin_0', Depth=1).GroupControl(foundIndex=11, Depth=8).GroupControl(foundIndex=3, Depth=6).GroupControl(foundIndex=3, Depth=3).GroupControl(Depth=3)
    
    @property
    def DialogWindow_last_message(self):
        return uiautomation.PaneControl(Name='闲鱼客服-IM聊天', ClassName='Chrome_WidgetWin_0', Depth=1).GroupControl(foundIndex=11, Depth=8).GroupControl(foundIndex=3, Depth=6).GroupControl(foundIndex=3, Depth=3).GroupControl(Depth=3).TextControl().Name
    
    @property
    def DialogWindow_last_i_message_group_control(self, i):
        return uiautomation.PaneControl(Name='闲鱼客服-IM聊天', ClassName='Chrome_WidgetWin_0', Depth=1).GroupControl(foundIndex=11, Depth=8).GroupControl(foundIndex=3, Depth=6).GroupControl(foundIndex=3, Depth=3).GroupControl(Depth=3, foundIndex=i)
    
    @property
    def DialogWindow_last_i_message(self, i):
        return uiautomation.PaneControl(Name='闲鱼客服-IM聊天', ClassName='Chrome_WidgetWin_0', Depth=1).GroupControl(foundIndex=11, Depth=8).GroupControl(foundIndex=3, Depth=6).GroupControl(foundIndex=3, Depth=3).GroupControl(Depth=3, foundIndex=i).TextControl().Name
    
    @property
    def DialogWindow_input_control(self):
        return uiautomation.PaneControl(Name='闲鱼客服-IM聊天', ClassName='Chrome_WidgetWin_0', Depth=1).GroupControl(foundIndex=11, Depth=8).GroupControl(foundIndex=3, Depth=6).GroupControl(foundIndex=8, Depth=1)

    @property
    def ManageWindow_good_name(self):
        return uiautomation.PaneControl(Name='闲鱼客服-IM聊天', ClassName='Chrome_WidgetWin_0', Depth=1).GroupControl(foundIndex=11, Depth=8).GroupControl(foundIndex=2, Depth=3).GroupControl(foundIndex=2, Depth=1).GroupControl(foundIndex=3, Depth=1).GroupControl(foundIndex=2, Depth=2).CustomControl(Name='商品', Depth=1).GroupControl(Depth=2).TextControl(foundIndex=3).TextControl().Name
    
    @property
    def ManageWindow_good_table_control(self):
        return uiautomation.PaneControl(Name='闲鱼客服-IM聊天', ClassName='Chrome_WidgetWin_0', Depth=1).GroupControl(foundIndex=11, Depth=8).GroupControl(foundIndex=2, Depth=3).GroupControl(foundIndex=2, Depth=1).GroupControl(foundIndex=3, Depth=1).TabItemControl(Name='商品', Depth=6)
    
    @property
    def ManageWindow_order_table_control(self):
        return uiautomation.PaneControl(Name='闲鱼客服-IM聊天', ClassName='Chrome_WidgetWin_0', Depth=1).GroupControl(foundIndex=11, Depth=8).GroupControl(foundIndex=2, Depth=3).GroupControl(foundIndex=2, Depth=1).GroupControl(foundIndex=3, Depth=1).TabItemControl(Name='订单', Depth=6)
    
    @property
    def ManageWindow_service_name(self):
        return None
    
    @property
    def ManageWindow_modify_price_button(self):
        return uiautomation.PaneControl(Name='闲鱼客服-IM聊天', ClassName='Chrome_WidgetWin_0', Depth=1).GroupControl(foundIndex=11, Depth=8).GroupControl(foundIndex=2, Depth=3).GroupControl(foundIndex=2, Depth=1).GroupControl(foundIndex=3, Depth=1).GroupControl(foundIndex=2, Depth=2).GroupControl(foundIndex=2, Depth=3).ButtonControl(Name='修改价格', Depth=2)

    @property
    def Price_Editwindow_price_edit_control(self):
        return uiautomation.PaneControl(Name='闲鱼客服-IM聊天', ClassName='Chrome_WidgetWin_0', Depth=1).GroupControl(foundIndex=3, Depth=3).GroupControl(Depth=2).GroupControl(Depth=1).GroupControl(foundIndex=2, Depth=1).EditControl(Depth=2)
    
    @property
    def Price_Editwindow_confirm_button(self):
        return uiautomation.PaneControl(Name='闲鱼客服-IM聊天', ClassName='Chrome_WidgetWin_0', Depth=1).GroupControl(foundIndex=3, Depth=3).GroupControl(Depth=2).ButtonControl(Name='确定', Depth=1)

    def get_message_by_index(self, index):
        """根据索引获取消息"""
        try:
            control = uiautomation.PaneControl(
                Name='闲鱼客服-IM聊天', 
                ClassName='Chrome_WidgetWin_0', 
                Depth=1
            ).GroupControl(
                foundIndex=10, 
                Depth=8
            ).GroupControl(
                foundIndex=3, 
                Depth=6
            ).GroupControl(
                foundIndex=3, 
                Depth=3
            ).GroupControl(
                Depth=3, 
                foundIndex=index
            )
            return control.TextControl().Name
        except Exception as e:
            self.logger.error(f"获取第{index}条消息失败: {str(e)}")
            return None

    def get_message_group_by_index(self, index):
        """根据索引获取消息组控件"""
        try:
            return uiautomation.PaneControl(
                Name='闲鱼客服-IM聊天', 
                ClassName='Chrome_WidgetWin_0', 
                Depth=1
            ).GroupControl(
                foundIndex=10, 
                Depth=8
            ).GroupControl(
                foundIndex=3, 
                Depth=6
            ).GroupControl(
                foundIndex=3, 
                Depth=3
            ).GroupControl(
                Depth=3, 
                foundIndex=index
            )
        except Exception as e:
            self.logger.error(f"获取第{index}条消息组控件失败: {str(e)}")
            return None

# 注册1.21.18版本适配器
IMAdapterFactory.register_adapter("1.21.18", IMAdapterV1_21_18)

