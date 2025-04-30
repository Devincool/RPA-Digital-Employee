import base64
import json
import os
import time

from datetime import datetime, timedelta
import re
from core.config import Config
import hashlib
import http.client
from tqdm import tqdm
from core.secure import secure_storage
from core.api_key_manager import APIKeyManager
from core.llm_tools import call_llm_api_for_tools, summary_order_detail_by_llm
from core.cache import DialogCache

def remove_special_characters(s):
    return re.sub(r"[\\/:*?\"<>|]", "", s)

def save_base64_image(base64_str, filename):
    """将base64字符串保存为图片文件
    
    Args:
        base64_str: str, base64编码的图片字符串
        filename: str, 保存的文件名
        
    Returns:
        bool: 保存成功返回True,失败返回False 
    """
    try:
        # base64解码
        img_data = base64.b64decode(base64_str)
        
        # 写入文件
        with open(filename, 'wb') as f:
            f.write(img_data)
            
        return True
    except Exception as e:
        print(f"保存图片失败: {str(e)}")
        return False

def trans_csv_2_prompt_json(csv_string):
    """
    调用 大模型api进行转换
    csv格式：
    一级类目,二级类目,三级类目,四级类目,价格
    Joycon手柄,手柄左右一对,基本全新,,258
    Joycon手柄,手柄左右一对,99新,,238
    Joycon手柄,手柄左右一对,95新,,228
    Joycon手柄,手柄左右一对,9新,,218

    转换后：
    **Joycon手柄价格详情:**
    1. **手柄左右一对:**
        - 基本全新:258元
        - 99新:238元
        - 95新:228元
        - 9新:218元
        - 5-8新:198元
    """
    query = """输入示例：
一级类目,二级类目,三级类目,四级类目,价格
Switch游戏机,全套,日版普通版,不破解,1000
Switch游戏机,全套,日版普通版,不带卡,1050
Switch游戏机,全套,日版普通版,128G,1100
Switch游戏机,全套,日版普通版,256G,1200
Switch游戏机,全套,日版普通版,512G,1300
Switch游戏机,全套,日版普通版,1T,1550
Switch游戏机,全套,国行续航版,不破解,1050
Switch游戏机,全套,国行续航版,不带卡,1100
Switch游戏机,全套,国行续航版,128G,1150
Switch游戏机,全套,国行续航版,256G,1250
Switch游戏机,全套,国行续航版,512G,1350
Switch游戏机,全套,国行续航版,1T,1600
请将我之后输出的信息整理成如下格式：**Switch游戏机价格详情:**
1. **全套:**
   - **日版普通版:**
     - 正版:999元
     - 不带卡:1050元
     - 128G:1099元
     - 256G:1199元
     - 512G:1299元
     - 1T:1549元
   - **国行续航版:**
     - 正版:999元
     - 不带卡:1049元
     - 128G:1099元
     - 256G:1199元
     - 512G:1299元
     - 1T:1549元
    """
    
    return call_llm_api_for_tools(
        content=csv_string,
        system_prompt=query,
        output_type="text"
    )

class XianGuanJia:
    """
    闲管家开放平台API封装类
    
    用于访问闲管家开放平台的API接口，提供商品管理、订单管理等功能。
    
    使用示例:
        xgj = XianGuanJia()
        
        # 调用API接口
        data = {
            "page": 1,
            "size": 20
        }
        response = xgj._request("/api/v1/products", data)
    
    属性:
        appKey (str): 闲管家开放平台的应用Key，需配置环境变量XIAN_GUAN_JIA_APP_KEY
        appSecret (str): 闲管家开放平台的应用Secret，需配置环境变量XIAN_GUAN_JIA_APP_SECRET 
        domain (str): API域名地址，默认为正式环境 https://open.goofish.pro
        
    方法:
        _request(url: str, data: json): 发送API请求
            参数:
                url: API接口路径
                data: 请求参数(JSON格式)
            返回:
                str: API响应内容
                
        _genSign(bodyJson: str, timestamp: int): 生成API签名
            参数:
                bodyJson: 请求体JSON字符串
                timestamp: 时间戳(秒)
            返回:
                str: 签名字符串
    """
    def __init__(self):
        self.appKey = os.environ.get('XIAN_GUAN_JIA_APP_KEY')
        self.appSecret = os.environ.get('XIAN_GUAN_JIA_APP_SECRET')
        self.domain = "https://open.goofish.pro"
        
        # 设置归档根目录
        self.archive_root = os.path.join(os.getenv('LOCALAPPDATA'), 'yimai', 'xianguanjia')
        if not os.path.exists(self.archive_root):
            os.makedirs(self.archive_root)

    # 请求函数
    def _request(self, url: str, data: json):
        # 将json对象转成json字符串
        # 特别注意：使用 json.dumps 函数时必须补充第二个参数 separators=(',', ':') 用于过滤空格，否则会签名错误
        body = json.dumps(data, separators=(",", ":"))

        # 时间戳秒
        timestamp = int(time.time())

        # 生成签名
        sign = self._genSign(body, timestamp)

        # 拼接地址
        url = f"{self.domain}{url}?appid={self.appKey}&timestamp={timestamp}&sign={sign}"

        # 设置请求头
        headers = {"Content-Type": "application/json"}

        # 请求接口
        conn = http.client.HTTPSConnection("api.goofish.pro")
        conn.request(
            "POST",
            url,
            body,
            headers,
        )
        res = conn.getresponse()
        reps = res.read().decode("utf-8")
        print(type(reps))

        return reps


    # 签名函数
    def _genSign(self, bodyJson: str, timestamp: int):
        # 将请求报文进行md5
        m = hashlib.md5()
        m.update(bodyJson.encode("utf8"))
        bodyMd5 = m.hexdigest()

        # 拼接字符串生成签名-自研模式
        s = f"{self.appKey},{bodyMd5},{timestamp},{self.appSecret}"
        
        #商务对接模式
        #s = f"{appKey},{bodyMd5},{timestamp},{sellerId},{appSecret}"
        
        m = hashlib.md5()
        m.update(s.encode("utf8"))
        sign = m.hexdigest()

        return sign


    def _get_archive_path(self, product_id: str) -> str:
        """获取商品归档路径"""
        return os.path.join(self.archive_root, str(product_id))

    def _save_product_info(self, product_id: str, info: dict):
        """保存加密的商品信息"""
        archive_path = self._get_archive_path(product_id)
        if not os.path.exists(archive_path):
            os.makedirs(archive_path)
            
        # 加密保存商品信息
        secure_storage.save_json(
            os.path.join(archive_path, "product_info.json"),
            info
        )

    def _load_product_info(self, product_id: str) -> dict:
        """加载加密的商品信息"""
        try:
            info_path = os.path.join(self._get_archive_path(product_id), "product_info.json")
            return secure_storage.load_json(info_path)
        except Exception as e:
            print(f"加载商品信息失败: {str(e)}")
            return None

    def _save_index(self, index: dict):
        """保存加密的索引文件"""
        secure_storage.save_json(
            os.path.join(self.archive_root, "index.json"),
            index
        )
        
        # 同时保存处理后的索引
        processed_index = self._process_index(index)
        secure_storage.save_json(
            os.path.join(self.archive_root, "index_processed.json"),
            processed_index
        )

    def _load_index(self) -> dict:
        """加载加密的索引文件"""
        try:
            return secure_storage.load_json(
                os.path.join(self.archive_root, "index.json")
            )
        except Exception as e:
            print(f"加载索引失败: {str(e)}")
            return None

    def _process_index(self, index: dict) -> dict:
        """处理索引文件，生成优化后的结构"""
        processed = {
            "products": [],
            "categories": set()
        }
        
        for product in index["products"]:
            # 提取关键信息
            processed["products"].append({
                "id": product["id"],
                "title": product["title"],
                "archive_name": str(product["id"]),
                "category": product.get("category", []),
                "price": product.get("price", 0),
                "status": product.get("status", "active")
            })
            
            # 收集分类信息
            if "category" in product:
                for cat in product["category"]:
                    processed["categories"].add(cat)
                    
        # 转换set为list
        processed["categories"] = list(processed["categories"])
        return processed

    def save_product_images(self, product_id: str, images: list):
        """保存商品图片"""
        archive_path = self._get_archive_path(product_id)
        if not os.path.exists(archive_path):
            os.makedirs(archive_path)
            
        for i, img_data in enumerate(images):
            img_path = os.path.join(archive_path, f"image_{i}.jpg")
            save_base64_image(img_data, img_path)

    def get_product_detail_by_title(self, title: str) -> dict:
        """根据商品标题获取详情"""
        try:
            index = secure_storage.load_json(
                os.path.join(self.archive_root, "index_processed.json")
            )
            
            if not index:
                return None
                
            # 查找匹配的商品
            for product in index["products"]:
                if product["title"] == title:
                    # 加载完整商品信息
                    return self._load_product_info(product["archive_name"])
                    
            return None
            
        except Exception as e:
            print(f"获取商品详情失败: {str(e)}")
            return None

    def get_product_summary_by_category(self, category: str) -> str:
        """获取分类商品摘要"""
        try:
            index = secure_storage.load_json(
                os.path.join(self.archive_root, "index_processed.json")
            )
            
            if not index:
                return ""
                
            # 收集该分类下的商品信息
            products = []
            for product in index["products"]:
                if category in product["category"]:
                    products.append(product)
                    
            if not products:
                return ""
                
            # 生成摘要
            summary = f"找到{len(products)}个{category}商品:\n"
            for p in products:
                summary += f"- {p['title']}: ¥{p['price']}\n"
            return summary
            
        except Exception as e:
            print(f"获取分类摘要失败: {str(e)}")
            return ""

    def get_order_detail(self, order_id):
        """
        该接口可在请求闲管家之后使用大模型自动总结返回信息，反馈给请求方

        重要参数说明：
        @param order_status  enum<integer> <int32>  订单状态
            枚举值：
            11 : 待付款
            12 : 待发货
            21 : 已发货
            22 : 交易成功
            23 : 已退款
            24 : 交易关闭

        @param pay_time   integer <int32> 订单支付时间

        @param waybill_no string 快递单号
            示例值:
            SF23817389113

        @param express_name string 快递公司名称
            示例值:
            顺丰速运
        
        @param seller_remark  string  卖家备注
            示例值:
            疫情期间暂停发货
            
        """

        order_detail_raw = self._request("/api/open/order/detail", {"order_no": order_id})
        print(f"闲管家接口响应：{order_detail_raw}")
        return summary_order_detail_by_llm(order_detail_raw)
        
    def get_product_title_by_good_name(self, good_name: str) -> str:
        """根据商品名称获取商品标题
        
        Args:
            good_name: 用户输入的商品名称
            
        Returns:
            str: 匹配到的商品标题，如果没有匹配到返回原始输入
        """
        try:
            # 读取处理后的索引文件
            index = secure_storage.load_json(
                os.path.join(self.archive_root, "index_processed.json")
            )
            
            if not index:
                print("未找到索引文件")
                return good_name
                
            # 1. 构建简版索引表
            product_index = []
            for product in index["products"]:
                product_index.append({
                    "title": product["title"],
                    "archive_name": product["archive_name"],
                    "category": " > ".join(product["category"])
                })
                
            # 2. 构建提示词
            prompt = f"""
我有一个商品索引表，格式如下:
{json.dumps(product_index, ensure_ascii=False, indent=2)}

用户说要找"{good_name}"，请判断用户需要的是哪个商品的链接。
只需返回对应商品的title，如果找不到匹配的商品就返回空字符串。
不要返回任何解释，只返回title或空字符串。
"""
            
            # 3. 调用大模型判断
            response = call_llm_api_for_tools(
                content=prompt,
                output_type="text"
            )
            
            # 4. 验证返回结果是否在索引中
            for product in product_index:
                if product["title"] == response:
                    return response
                    
            # 5. 如果没有匹配到，返回原始输入
            return good_name
                
        except Exception as e:
            print(f"获取商品标题失败: {str(e)}")
            return good_name

    def get_onsell_product_list(self):
        """获取商品列表"""
        product_list = json.loads(self._request("/api/open/product/list", {"product_status": 22, "page_size": 100}))["data"]["list"]
        return product_list

    def docking_shop_ERP_system(self):
        """对接店铺ERP系统，获取商品信息并保存"""
        try:
            # 获取在售商品列表
            product_list = self.get_onsell_product_list()
            
            # 构建索引数据
            index_data = {
                "products": [],
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 处理每个商品
            for product in tqdm(product_list, desc="同步商品信息"):
                try:
                    # 获取商品详情
                    product_detail = json.loads(
                        self._request("/api/open/product/detail", {"product_id": product["product_id"]})
                    )["data"]
                    
                    # 提取商品信息
                    product_info = {
                        "id": product["product_id"],
                        "title": product["title"],
                        "price": product["price"],
                        "category": product_detail.get("category_path", []),
                        "status": "active",
                        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    # 保存商品信息
                    self._save_product_info(product["product_id"], product_info)
                    
                    # 保存商品图片
                    if "images" in product_detail:
                        self.save_product_images(product["product_id"], product_detail["images"])
                    
                    # 添加到索引
                    index_data["products"].append(product_info)
                    
                except Exception as e:
                    print(f"处理商品 {product['product_id']} 失败: {str(e)}")
                    continue
                
            # 保存索引文件
            self._save_index(index_data)
            
            return True
            
        except Exception as e:
            print(f"同步商品信息失败: {str(e)}")
            return False

    def generate_summary_and_archive_name_from_products(self):
        """遍历商品目录，为每个商品生成summary和archive_name，并更新索引文件"""
        try:
            print("\n=== 开始生成商品摘要和型号简称 ===")
            
            # 1. 读取索引文件
            root_dir = os.path.join(os.path.dirname(__file__), "product_archive")
            index_path = os.path.join(root_dir, "index.json")
            
            with open(index_path, "r", encoding="utf-8") as f:
                index_data = json.load(f)
            
            print("√ 索引文件读取完成")
            
            # 2. 处理每个商品
            print("\n开始处理商品...")
            for product in tqdm(index_data["products"]):
                try:
                    product_id = product["product_id"]
                    product_path = os.path.join(root_dir, f"product_{product_id}", "info.json")
                    
                    # 读取商品详细信息
                    with open(product_path, "r", encoding="utf-8") as f:
                        product_info = json.load(f)
                    
                    # 获取商品描述，处理可能的嵌套结构
                    description = ""
                    if product_info.get("detail", {}).get("publish_shop"):
                        description = product_info["detail"]["publish_shop"][0].get("content", "")
                    elif product_info.get("publish_shop"):
                        description = product_info["publish_shop"][0].get("content", "")
                    
                    # 如果描述内容少于200字，直接使用原文作为摘要
                    if len(description) <= 200:
                        summary = description
                        print(f"\n√ 商品 {product_id} 使用原文作为摘要")
                    else:
                        # 生成商品摘要
                        summary_prompt = f"""
                        基于以下商品信息生成专业的商品摘要：
                        商品标题: {product_info["title"]}
                        商品描述: {description}

                        要求：
                        1. 摘要要专业、准确、完整
                        2. 包含商品的关键特征和优势
                        3. 长度控制在100-200字
                        4. 便于客服快速了解商品信息
                        5. 适合用于后续的商品推荐

                        只返回摘要文本。
                        """
                        
                        summary = call_llm_api_for_tools(summary_prompt, output_type="text").strip()
                    
                    # 生成商品简称
                    archive_prompt = f"""
                    基于以下信息生成商品的规范简称：
                    商品标题: {product_info["title"]}
                    商品摘要: {summary}

                    要求：
                    1. 简称要规范、易识别
                    2. 包含商品的关键特征
                    3. 便于分类和检索
                    4. 长度控制在5-15个字符
                    5. 不要使用特殊字符
                    6. 参考格式：
                       - "NS国行续航版"
                       - "NS日版OLED版"
                       - "JC白色OLED"
                       - "NSPro手柄"

                    只返回简称文本。
                    """
                    
                    archive_name = call_llm_api_for_tools(archive_prompt, output_type="text").strip()
                    
                    # 更新商品信息
                    product_info["summary"] = summary
                    product_info["archive_name"] = archive_name
                    product["summary"] = summary
                    product["archive_name"] = archive_name
                    
                    # 保存更新后的商品信息
                    with open(product_path, "w", encoding="utf-8") as f:
                        json.dump(product_info, f, ensure_ascii=False, indent=2)
                    
                    print(f"\n√ 已处理商品: {archive_name}")
                    if len(description) <= 200:
                        print(f"  使用原文作为摘要: {summary[:100]}...")
                    else:
                        print(f"  生成的摘要: {summary[:100]}...")
                    
                except Exception as e:
                    print(f"\n× 处理商品 {product_id} 失败: {str(e)}")
                    continue
            
            # 3. 保存更新后的索引文件
            index_data["update_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print("\n保存索引文件...")
            save_path = os.path.join(root_dir, "index_processed.json")
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(index_data, f, ensure_ascii=False, indent=2)
            
            print("\n=== 商品摘要和型号简称生成完成 ===")
            return True
            
        except Exception as e:
            print(f"\n× 生成商品摘要和型号简称失败: {str(e)}")
            return False

    def update_products_summary(self):
        try:
            print("\n=== 开始同步商品信息 ===")
            root_dir = os.path.join(os.path.dirname(__file__), "product_archive")
            os.makedirs(root_dir, exist_ok=True)
            
            # 1. 读取现有索引
            print("\n1. 读取本地索引文件...")
            index_path = os.path.join(root_dir, "index_processed.json")
            existing_index = {}
            if os.path.exists(index_path):
                with open(index_path, "r", encoding="utf-8") as f:
                    existing_index = json.load(f)
                    print(f"√ 已读取现有商品数: {len(existing_index.get('products', []))}")
            
            # 2. 获取在售商品列表
            print("\n2. 获取在售商品列表...")
            current_products = self.get_onsell_product_list()
            if not current_products:
                print("× 获取在售商品列表失败")
                return False
            print(f"√ 获取在售商品数: {len(current_products)}")
            
            # 3. 创建新的索引数据
            index_data = {
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "categories": existing_index.get("categories", {}),
                "products": []
            }
            
            # 创建现有商品映射，用于快速查找
            existing_products = {p["product_id"]: p for p in existing_index.get("products", [])}
            
            # 4. 处理每个商品
            print("\n3. 开始处理商品信息...")
            for product in tqdm(current_products, desc="同步商品信息"):
                try:
                    product_id = product["product_id"]
                    
                    # 获取商品详情
                    product_detail = json.loads(self._request("/api/open/product/detail", {"product_id": product_id}))
                    if not product_detail or "data" not in product_detail:
                        continue
                    
                    product_data = product_detail["data"]
                    
                    # 检查商品是否需要更新
                    needs_update = True
                    if product_id in existing_products:
                        old_product = existing_products[product_id]
                        # 检查关键信息是否变化
                        if (product_data["title"].strip().replace(" ", "") == old_product["title"].strip().replace(" ", "") and
                            product_data["price"] == old_product["base_price"] * 100 and
                            product_data["stock"] == old_product["stock_total"]):
                            # 复用现有信息
                            index_data["products"].append(old_product)
                            needs_update = False
                            print(f"\n- 商品 {product_id} 无需更新")
                            continue
                        else:
                            print(f"\n- 商品 {product_id} 需要更新:")
                            if product_data["title"].strip().replace(" ", "") != old_product["title"].strip().replace(" ", ""):
                                print(f"  标题变化: {old_product['title']} -> {product_data['title']}")
                            if product_data["price"] != old_product["base_price"] * 100:
                                print(f"  价格变化: {old_product['base_price']} -> {product_data['price']/100}")
                            if product_data["stock"] != old_product["stock_total"]:
                                print(f"  库存变化: {old_product['stock_total']} -> {product_data['stock']}")

                    if product_data.get("sku_items"):
                        sku_info = []
                        for sku in product_data["sku_items"]:
                            sku_info.append({
                                "sku_id": sku["sku_id"],
                                "price": sku["price"] / 100,
                                "stock": sku["stock"],
                                "sku_text": sku["sku_text"]
                            })
                    
                    if needs_update:
                        # 获取商品描述内容
                        content = product_data["publish_shop"][0]["content"] if product_data["publish_shop"] else ""
                        
                        # 如果描述内容少于200字，直接使用原文作为摘要
                        if len(content) <= 200:
                            summary = content
                            print(f"\n√ 商品 {product_id} 使用原文作为摘要")
                        else:
                            # 生成新的商品摘要
                            if product_data.get("sku_items"):
                                summary_prompt = f"""
                                在掌握以下知识的前提下：{Config.SWITCH_BASE_CATEGORIES}
                                请根据以下商品信息生成专业的商品摘要：

                                标题：{product_data["title"]}
                                多规格信息：{json.dumps(sku_info, ensure_ascii=False)}
                                描述：{content}

                                要求：
                                1. 描述专业简洁
                                2. 包含完整的价格信息，如果描述中写的是加价，保存加价后的价格
                                3. 突出商品特点
                                4. 使用规范的产品术语
                                5. 不超过200字
                                """
                            else:
                                summary_prompt = f"""
                                在掌握以下知识的前提下：{Config.SWITCH_BASE_CATEGORIES}
                                请根据以下商品信息生成专业的商品摘要：

                                标题：{product_data["title"]}
                                价格：{product_data["price"]/100}元
                                描述：{content}

                                要求：
                                1. 描述专业简洁
                                2. 包含完整的价格信息
                                3. 突出商品特点
                                4. 使用规范的产品术语
                                5. 不超过200字
                                """
                            
                            summary = call_llm_api_for_tools(summary_prompt, output_type="text").strip()
                            print(f"\n√ 商品 {product_id} 生成新的摘要")


                        if product_data.get("sku_items"):
                            # 生成型号简称
                            archive_prompt = f"""
                            在掌握以下知识的前提下：{Config.SWITCH_BASE_CATEGORIES}
                            请根据以下商品信息生成一个清晰明确的产品型号简称：

                            标题：{product_data["title"]}
                            摘要：{summary}
                            价格配置：{json.dumps(sku_info, ensure_ascii=False)}

                            要求：
                            1. 简称要包含产品类型和关键特征
                            2. 使用规范的产品术语
                            3. 便于分类和检索
                            4. 长度控制在5-15个字符
                            5. 不要使用特殊字符
                            6. 示例格式：
                            - "NS国行续航版"
                            - "NS日版OLED版"
                            - "NS国行普通版"
                            - "JC白色"

                            只返回简称文本。
                            """
                        else:
                            archive_prompt = f"""
                            在掌握以下知识的前提下：{Config.SWITCH_BASE_CATEGORIES}
                            请根据以下商品信息生成一个清晰明确的产品型号简称：

                            标题：{product_data["title"]}
                            摘要：{summary}

                            要求：
                            1. 简称要包含产品类型和关键特征
                            2. 使用规范的产品术语
                            3. 便于分类和检索
                            4. 长度控制在5-15个字符
                            5. 不要使用特殊字符
                            6. 示例格式：
                            - "NS国行续航版"
                            - "NS日版OLED版"
                            - "NS国行普通版"
                            - "JC白色"

                            只返回简称文本。
                            """
                        
                        archive_name = call_llm_api_for_tools(archive_prompt, output_type="text").strip()
                        
                        # 构建新的商品信息
                        new_product = {
                            "product_id": product_id,
                            "title": product_data["title"],
                            "path": f"product_{product_id}",
                            "summary": summary,
                            "archive_name": archive_name,
                            "base_price": product_data["price"] / 100,
                            "stock_total": product_data["stock"],
                            "status": product_data["product_status"],
                            "spec_type": product_data["spec_type"],
                            "sku_info": []
                        }
                        
                        # 处理多规格信息
                        if product_data.get("sku_items"):
                            for sku in product_data["sku_items"]:
                                new_product["sku_info"].append({
                                    "sku_id": sku["sku_id"],
                                    "price": sku["price"] / 100,
                                    "stock": sku["stock"],
                                    "sku_text": sku["sku_text"]
                                })
                            
                            # 计算价格区间
                            prices = [sku["price"] / 100 for sku in product_data["sku_items"]]
                            new_product["price_range"] = {
                                "min": min(prices),
                                "max": max(prices)
                            }
                        
                        index_data["products"].append(new_product)
                        print(f"\n√ 已更新商品: {new_product['archive_name']}")
                    
                except Exception as e:
                    print(f"\n× 处理商品 {product_id} 失败: {str(e)}")
                    continue
            
            # 5. 检查是否存在分类体系
            if not existing_index.get("categories"):
                print("\n4. 未找到分类体系，先保存更新后调用分类函数...")
                # 保存当前更新的商品信息
                with open(index_path, "w", encoding="utf-8") as f:
                    json.dump(index_data, f, ensure_ascii=False, indent=2)
                # 调用分类函数生成分类体系
                self.classify_products_in_index_json()
            else:
                print("\n4. 使用现有分类体系更新商品分类...")
                # 准备所有商品数据用于分类
                products_for_prompt = []
                for product in index_data["products"]:
                    products_for_prompt.append({
                        "product_id": product["product_id"],
                        "title": product["title"],
                        "summary": product.get("summary", ""),
                        "archive_name": product.get("archive_name", "")
                    })

                # 使用现有分类体系
                existing_categories = existing_index["categories"]
                
                # 生成分类提示
                category_prompt = f"""
                基于以下现有分类体系，为所有商品分配最合适的分类标签：

                现有分类体系：
                {json.dumps(existing_categories, ensure_ascii=False, indent=2)}

                待分类商品：
                {json.dumps(products_for_prompt, ensure_ascii=False, indent=2)}

                要求：
                1. 必须严格使用现有分类体系中的分类名称
                2. 每个商品必须分配完整的三级分类路径
                3. 根据商品标题和摘要信息准确判断商品类型
                4. 返回格式为json：
                {{
                    "商品分类": [
                        {{
                            "product_id": "商品ID",
                            "category": ["一级分类", "二级分类", "三级分类"]
                        }}
                    ]
                }}
                """

                print("正在为商品分配分类标签...")
                reply = call_llm_api_for_tools(
                    category_prompt, 
                    output_type="json_object"
                )
                
                try:
                    categorization = json.loads(reply)
                    print(f"分类体系生成结果: {categorization}")
                    
                    # 更新所有商品的分类信息
                    product_categories = {
                        str(item["product_id"]): item["category"] 
                        for item in categorization["商品分类"]
                    }
                    
                    # 更新商品分类
                    updated_count = 0
                    for product in index_data["products"]:
                        if str(product["product_id"]) in product_categories:
                            product["category"] = product_categories[str(product["product_id"])]
                            updated_count += 1
                            
                    print(f"成功为 {updated_count} 个商品更新分类信息")
                    
                    # 保存分类体系
                    index_data["categories"] = existing_categories
                    
                    # 保存更新后的索引文件
                    print("\n5. 保存索引文件...")
                    with open(index_path, "w", encoding="utf-8") as f:
                        json.dump(index_data, f, ensure_ascii=False, indent=2)
                    
                except Exception as e:
                    print(f"更新商品分类失败: {str(e)}")
                    return False

            print(f"\n=== 商品同步完成 ===")
            print(f"- 总商品数: {len(index_data['products'])}")
            print(f"- 更新时间: {index_data['update_time']}")
            return True
            
        except Exception as e:
            print(f"\n× 同步商品信息失败: {str(e)}")
            return False

    def classify_products_in_index_json(self):
        """对index_processed.json中的商品做分类，方便以后rag检索"""
        try:
            print("\n=== 开始商品分类 ===")
            
            # 1. 读取索引文件
            root_dir = "product_archive"
            index_path = os.path.join(os.path.dirname(__file__), root_dir, "index_processed.json")
            
            with open(index_path, "r", encoding="utf-8") as f:
                index_data = json.load(f)
            
            # 2. 准备商品数据用于提示
            products_for_prompt = []
            for product in index_data["products"]:
                products_for_prompt.append({
                    "product_id": product["product_id"],
                    "title": product["title"],
                    "summary": product.get("summary", ""),
                    "archive_name": product.get("archive_name", ""),
                    "price_info": product.get("sku_info", []) or [{"price": product["base_price"]}]
                })

            
            # 3. 生成分类体系
            category_prompt = f"""
            结合以下知识：{Config.SWITCH_DETIAL_CATEGORIES}
            请为以下商品设计合理的分类体系：

            商品列表：
            {json.dumps(products_for_prompt, ensure_ascii=False, indent=2)}
            
            要求：
            1. 分类层级不超过3级
            2. 理解商品标题和summary中对产品的分类方法，分类要专业
            3. 分类名称要简洁清晰
            4. 便于后续RAG检索
            5. 返回格式为json格式：
            {{
                "分类体系": {{
                    "一级分类1": {{
                        "二级分类1": ["三级分类1", "三级分类2"],
                        "二级分类2": ["三级分类3", "三级分类4"]
                    }},
                    "一级分类2": {{
                        "二级分类3": ["三级分类5", "三级分类6"]
                    }}
                }},
                "商品分类": [
                    {{
                        "product_id": "商品ID",
                        "category": ["一级分类", "二级分类", "三级分类"]
                    }}
                ]
            }}
            """
            
            print("\n正在生成分类体系...")
            reply = call_llm_api_for_tools(
                category_prompt, 
                output_type="json_object"
            )
            print(f"分类体系生成结果: {reply}")
            categorization = json.loads(reply)
            
            # 4. 更新索引数据
            index_data["categories"] = categorization["分类体系"]
            
            # 5. 为每个商品添加分类信息
            product_categories = {
                item["product_id"]: item["category"] 
                for item in categorization["商品分类"]
            }
            
            for product in index_data["products"]:
                product["category"] = product_categories.get(
                    str(product["product_id"]), 
                    []  # 默认空列表
                )
            
            # 6. 保存更新后的索引文件
            print("\n保存更新后的索引文件...")
            with open(index_path, "w", encoding="utf-8") as f:
                json.dump(index_data, f, ensure_ascii=False, indent=2)
            
            print("\n=== 商品分类完成 ===")
            print(f"- 分类体系已更新")
            print(f"- 商品分类已添加")
            return True
            
        except Exception as e:
            print(f"\n× 商品分类失败: {str(e)}")
            return False

    def generate_knowledge_json_by_llm(self):
        """根据index_processed.json中的商品信息，生成知识库json文件"""
        try:
            print("\n=== 开始生成公共知识库 ===")
            
            # 1. 读取索引文件
            root_dir = "product_archive"
            index_path = os.path.join(os.path.dirname(__file__), root_dir, "index_processed.json")
            
            with open(index_path, "r", encoding="utf-8") as f:
                index_data = json.load(f)
            
            # 2. 提取商品信息和分类体系
            products_info = [{
                "title": p["title"],
                "sku": p.get("sku_info", []),
                "summary": p.get("summary", ""),
                "category": p.get("category", []),
                "archive_name": p.get("archive_name", "")
            } for p in index_data["products"]]
            
            categories = index_data.get("categories", {})
            
            # 3. 设置system prompt增强知识生成效果
            system_prompt = """
            你是一位资深的任天堂Switch产品专家和二手游戏机商家，具有以下专业背景：

            1. 专业知识储备：
               - 精通任天堂Switch全系列产品的技术规格和功能特点
               - 熟悉各版本Switch（OLED/续航版/Lite）的差异和优势
               - 了解Joycon和Pro手柄的性能参数和使用特点
               - 掌握Switch系统和游戏运行的技术细节
               - 熟悉二手游戏机的评估标准和定价策略

            2. 行业经验：
               - 有多年Switch产品销售和售后服务经验
               - 精通二手游戏机的品质评估和价值判断
               - 了解市场动态和用户需求变化
               - 具备丰富的客户服务和问题解决经验

            3. 信息整合能力：
               - 能够准确理解和分析商品数据
               - 善于提取和归纳关键产品信息
               - 能够构建清晰的知识体系
               - 注重信息的实用性和可操作性

            4. 专业素养：
               - 保持客观中立的专业态度
               - 注重信息的准确性和时效性
               - 关注用户体验和实际需求
               - 具备商品定价和市场分析能力

            5. 数据结构理解：
               商品信息(products_info)包含以下字段：
               - title: 商品标题，包含商品的基本信息和关键特征
               - sku: 商品的具体规格信息，包含：
                 * sku_id: 规格ID
                 * price: 规格对应价格
                 * stock: 库存数量
                 * sku_text: 规格描述文本
               - summary: 商品的详细描述和特点总结
               - category: 商品所属分类数组，如["游戏机", "Switch", "OLED版"]
               - archive_name: 商品的简称，用于快速识别，如"NS日版OLED"

            任务目标：
            基于提供的商品数据，构建一个专业、完整、实用的Switch产品知识库，确保：
            1. 价格体系的完整性和准确性
            2. 产品信息的专业性和实用性
            3. 知识结构的清晰性和可读性
            4. 售前售后服务信息的实用性
            5. 技术参数和使用指南的准确性

            在处理数据时需要：
            1. 从title和sku_text中提取商品的版本、成色等关键信息
            2. 利用category信息准确归类商品
            3. 通过summary了解商品的详细特点
            4. 使用archive_name识别商品类型
            5. 基于sku信息构建完整的价格体系
            """

            # 4. 生成商品通识知识
            knowledge_prompt = f"""
            请基于以下信息，生成一个专业的商品知识库：

            商品信息：
            {json.dumps(products_info, ensure_ascii=False, indent=2)}

            基础分类信息：
            {Config.SWITCH_BASE_CATEGORIES}
            
            固定答案问题：
            {Config.SWITCH_AFTER_SALES_FIXED_ANSWER}

            要求：
            1. 生成的知识库应包含以下部分：
               - 产品品类概述：对各类产品的基本介绍和定位
               - 专业术语说明：解释行业专业术语和重要概念
               - 产品参数标准：各类产品的规格参数和评估标准
               - 使用维护指南：基本使用方法和维护建议
               - 购买建议指南：不同场景的选购建议
               - 常见问题解答：产品相关的常见问题和解答
               - 品质评估标准：二手商品的成色评估标准

            2. 知识要专业、准确、实用
            3. 理解总结各项附加项目的价格
            4. 适用于售前售后客服使用
            5. 便于后续大模型Prompt理解
            6. 分类清晰，结构合理

            请返回JSON格式的知识库，确保价格体系完整准确，可根据商品信息对价格体系扩充。
            """
            
            print("\n正在生成知识库...")
            knowledge_base = json.loads(call_llm_api_for_tools(
                knowledge_prompt,
                system_prompt=system_prompt,
                output_type="json_object"
            ))
            
            # 5. 保存知识库文件
            knowledge_path = "knowledge_base.json"
            print(f"\n保存知识库到 {knowledge_path}...")
            
            with open(knowledge_path, "w", encoding="utf-8") as f:
                json.dump(knowledge_base, f, ensure_ascii=False, indent=2)
            
            print("\n=== 知识库生成完成 ===")
            print("知识库包含以下部分：")
            for section in knowledge_base.keys():
                print(f"- {section}")
            return True
            
        except Exception as e:
            print(f"\n× 知识库生成失败: {str(e)}")
            return False

   
import shutil
def test_dialog_cache():
    # 创建测试目录
    test_cache_dir = "test_cache"
    if os.path.exists(test_cache_dir):
        shutil.rmtree(test_cache_dir)  # 清理旧的测试目录
    os.makedirs(test_cache_dir)

    # 初始化缓存对象，设置较短的过期时间便于测试
    dlg = DialogCache(test_cache_dir)
    dlg.cache_expire_hours = 1/3600  # 设置为1秒钟，方便测试

    print("=== 测试1: 添加初始消息 ===")
    for i in range(5):
        dlg.add_dialog("user1", "user", f"消息{i}")
        print(f"添加消息{i}")
    
    print("\n当前缓存内容:")
    print(dlg.get_history("user1"))
    
    print("\n=== 测试2: 等待缓存过期 ===")
    print("等待2秒让缓存过期...")
    print(f"当前pending_archive内容: {dlg.pending_archive}")
    time.sleep(3)
    
    # 添加新消息触发清理
    print("\n添加新消息触发清理机制")
    print(f"清理前pending_archive内容: {dlg.pending_archive}")
    dlg.add_dialog("user2", "user", "触发清理的消息")
    print(f"清理后pending_archive内容: {dlg.pending_archive}")
    time.sleep(0.5)
    
    print("\n=== 测试3: 检查归档文件 ===")
    archive_dir = os.path.join(test_cache_dir, "user1")
    print(f"归档目录路径: {archive_dir}")
    print(f"归档目录是否存在: {os.path.exists(archive_dir)}")
    
    if os.path.exists(archive_dir):
        files = os.listdir(archive_dir)
        print(f"归档文件列表: {files}")
        
        if files:  # 确保有文件才继续
            # 读取最新的归档文件
            latest_file = sorted(files)[-1]
            with open(os.path.join(archive_dir, latest_file), "r", encoding="utf-8") as f:
                archived_data = json.load(f)
                print("\n归档的对话内容:")
                print(json.dumps(archived_data, indent=2, ensure_ascii=False))
        else:
            print("归档目录为空，没有找到归档文件")
    else:
        print("未找到归档目录")

    print("\n=== 测试4: 添加新的消息 ===")
    for i in range(3):
        dlg.add_dialog("user1", "user", f"新消息{i}")
        print(f"添加新消息{i}")
    
    print("\n最终缓存内容:")
    print(dlg.get_history("user1"))

    import sys
    try:
        sys.exit(1)
    except Exception as e:
        while True:
            time.sleep(1)

def test_xianguanjia():
    xianguanjia = XianGuanJia()
    # 获取订单详情  
    xianguanjia.get_order_detail("4184985457118571618")

    """ 自动归档商品信息步骤  这些信息和店铺强相关  在问答会用到 """
    # 对接店铺ERP系统  这一步会自动获取店铺上架的商品，并生成商品档案
    xianguanjia.docking_shop_ERP_system()
    # 根据商品档案生成总结概述和商品简称
    xianguanjia.generate_summary_and_archive_name_from_products()
    # 生成商品分类体系
    xianguanjia.classify_products_in_index_json()

    """ 自动生成公共知识库步骤 用于提高认知水平 """
    # 生成公共知识库
    xianguanjia.generate_knowledge_json_by_llm()



if __name__ == "__main__":
    xianguanjia = XianGuanJia()
    # xianguanjia.get_order_detail("4184985457118571618")
    xianguanjia.docking_shop_ERP_system()
    xianguanjia.generate_summary_and_archive_name_from_products()
    xianguanjia.classify_products_in_index_json()
    # xianguanjia.generate_knowledge_json_by_llm()
    # xianguanjia.update_products_summary()