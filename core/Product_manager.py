from typing import Dict, List, Optional, Union, Any
from fuzzywuzzy import fuzz, process
import json
import os
import requests
from itertools import combinations
import pandas as pd
import jieba
import re

class ProductManager:
    def __init__(self):
        self.products = {}
        self.sku_database = {}  # 存储所有可能的SKU组合及其价格
        self.sku_df = None  # 用于存储SKU DataFrame
        self.load_sku_database()
        self._init_jieba()

    def _init_jieba(self):
        """初始化jieba分词"""
        custom_words = [
            "OLED", "硬破", "95新", "99新", "9新", "5-8新",
            "基本全新", "续航版", "国行版", "日版", "限定版",
            "单主机", "全套", "带128G", "带256G", "带512G",
            "Switch", "游戏机", "手柄", "JoyCon", "Pro手柄",
            "双系统", "不破解"
        ]
        for word in custom_words:
            jieba.add_word(word)

    def _preprocess_text(self, text: str) -> str:
        """
        预处理文本
        - 转换为小写
        - 移除特殊字符
        - 标准化空格
        """
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _get_keywords(self, text: str) -> List[str]:
        """
        获取文本的关键词列表
        """
        text = self._preprocess_text(text)
        return [word for word in jieba.cut(text) if word.strip()]

    def _calculate_similarity(self, query_keywords: List[str], target_keywords: List[str]) -> float:
        """
        计算两组关键词的相似度
        """
        # 如果任一关键词列表为空，返回0
        if not query_keywords or not target_keywords:
            return 0

        # 计算关键词匹配数
        matches = sum(1 for q in query_keywords if any(
            fuzz.ratio(q, t) > 90 for t in target_keywords
        ))

        # 计算加权得分
        query_length = len(query_keywords)
        match_ratio = matches / query_length if query_length > 0 else 0
        
        # 使用token_sort_ratio作为基础分数
        base_score = fuzz.token_sort_ratio(
            ' '.join(query_keywords), 
            ' '.join(target_keywords)
        )

        # 综合评分
        final_score = (base_score * 0.7 + match_ratio * 100 * 0.3)
        return final_score

    def add_category(self, category_name: str) -> None:
        """
        添加商品类别
        
        Args:
            category_name: 类别名称
        """
        if category_name not in self.products:
            self.products[category_name] = {}

    def add_product(self, category: str, product_name: str, base_price: float, description: str) -> None:
        """
        添加商品
        
        Args:
            category: 商品类别
            product_name: 商品名称
            base_price: 基础价格
            description: 商品描述
        """
        if category not in self.products:
            self.add_category(category)
            
        self.products[category][product_name] = {
            "base_price": base_price,
            "specs": {},
            "description": description
        }

    def add_spec(self, category: str, product_name: str, spec_name: str, 
                 price_modifier: Union[Dict[str, Union[float, str]], str], description: str) -> None:
        """
        添加商品规格，支持更灵活的价格修改规则
        
        Args:
            category: 商品类别
            product_name: 商品名称
            spec_name: 规格名称
            price_modifier: 价格修改规则，可以是字典格式或字符串描述
            description: 规格描述
        """
        if (category in self.products and 
            product_name in self.products[category]):
            
            # 如果price_modifier是字符串，转换为标准格式
            if isinstance(price_modifier, str):
                price_modifier = {
                    "type": "expression",
                    "value": price_modifier
                }
                
            self.products[category][product_name]["specs"][spec_name] = {
                "price_modifier": price_modifier,
                "description": description
            }

    
    def search_product(self, query: str, threshold: int = 65) -> List[Dict[str, Any]]:
        """
        搜索商品，返回匹配度超过阈值的所有商品
        使用token_sort_ratio进行匹配，忽略关键词顺序
        
        Args:
            query: 搜索关键词
            threshold: 匹配度阈值(0-100)
            
        Returns:
            匹配的商品列表
        """
        results = []
        
        for category, category_items in self.products.items():
            for product_name, product_info in category_items.items():
                # 使用token_sort_ratio代替partial_ratio
                ratio = fuzz.token_sort_ratio(query.lower(), product_name.lower())
                if ratio >= threshold:
                    results.append({
                        "category": category,
                        "product_name": product_name,
                        "match_ratio": ratio,
                        "info": product_info
                    })
        
        return sorted(results, key=lambda x: x["match_ratio"], reverse=True)

    def search_spec(self, product_name: str, spec_query: str, threshold: int = 65) -> List[Dict[str, Any]]:
        """
        搜索商品的具体规格
        使用token_sort_ratio进行匹配，忽略关键词顺序
        
        Args:
            product_name: 商品名称
            spec_query: 规格搜索关键词
            threshold: 匹配度阈值(0-100)
            
        Returns:
            匹配的规格列表
        """
        results = []
        product = self.find_exact_product(product_name)
        
        if not product:
            return results
            
        for spec_name, spec_info in product["specs"].items():
            # 使用token_sort_ratio代替partial_ratio
            ratio = fuzz.token_sort_ratio(spec_query.lower(), spec_name.lower())
            if ratio >= threshold:
                price = self.calculate_price(product["base_price"], spec_info["price_modifier"])
                results.append({
                    "spec_name": spec_name,
                    "match_ratio": ratio,
                    "price": price,
                    "info": spec_info
                })
        
        return sorted(results, key=lambda x: x["match_ratio"], reverse=True)
    

    def load_sku_database(self, filepath: str = "config/sku_list.csv"):
        """
        从CSV文件加载SKU数据库
        
        Args:
            filepath: CSV文件路径
        """
        try:
            self.sku_df = pd.read_csv(filepath)
        except Exception as e:
            print(f"加载SKU数据库失败: {str(e)}")
            self.sku_df = pd.DataFrame(columns=['sku_name', 'price', 'stock', 'product_name', 'keywords'])

    def save_sku_database(self, filepath: str = "config/sku_list.csv"):
        """
        保存SKU数据库到CSV文件
        
        Args:
            filepath: CSV文件路径
        """
        try:
            self.sku_df.to_csv(filepath, index=False)
        except Exception as e:
            print(f"保存SKU数据库失败: {str(e)}")

    def search_sku(self, query: str, threshold: int = 65) -> List[Dict[str, Any]]:
        """
        搜索SKU，使用改进的匹配算法
        
        Args:
            query: 搜索关键词
            threshold: 匹配度阈值(0-100)
            
        Returns:
            匹配的SKU列表
        """
        if self.sku_df is None or self.sku_df.empty or not query.strip():
            return []

        # 获取查询关键词
        query_keywords = self._get_keywords(query)
        
        results = []
        for _, row in self.sku_df.iterrows():
            # 对keywords列进行分词
            target_keywords = self._get_keywords(str(row['keywords']))
            
            # 计算相似度
            similarity = self._calculate_similarity(query_keywords, target_keywords)
            
            if similarity >= threshold:
                results.append({
                    "sku_name": row['sku_name'],
                    "price": row['price'],
                    "stock": row['stock'],
                    "product_name": row['product_name'],
                    "match_ratio": similarity
                })
        
        # 按匹配度降序排序
        return sorted(results, key=lambda x: x["match_ratio"], reverse=True)


    def filter_sku_by_category_price(self, category: str = None, min_price: float = None, 
                                   max_price: float = None) -> pd.DataFrame:
        """
        根据商品类别和价格区间筛选SKU信息
        
        Args:
            category: 商品类别，如果为None则不筛选类别
            min_price: 最低价格，如果为None则不设下限
            max_price: 最高价格，如果为None则不设上限
            
        Returns:
            符合条件的SKU信息DataFrame
        """
        if self.sku_df is None or self.sku_df.empty:
            return pd.DataFrame()
        
        # 创建筛选条件
        mask = pd.Series(True, index=self.sku_df.index)
        
        # 按类别筛选
        if category is not None:
            mask &= self.sku_df['product_name'].str.contains(category, case=False, na=False)
        
        # 按价格下限筛选
        if min_price is not None:
            mask &= self.sku_df['price'] >= min_price
        
        # 按价格上限筛选
        if max_price is not None:
            mask &= self.sku_df['price'] <= max_price
        
        # 应用筛选条件并按价格排序
        filtered_df = self.sku_df[mask].sort_values('price')
        
        return filtered_df

    def get_recommendation(self, budget: float = None, preferences: Dict[str, str] = None) -> List[Dict]:
        """
        基于预算和偏好推荐商品
        
        Args:
            budget: 预算上限
            preferences: 偏好字典，例如 {"screen": "OLED", "condition": "95新"}
            
        Returns:
            推荐商品列表
        """
        # 1. 首先按预算筛选
        results = self.filter_sku_by_category_price(
            max_price=budget
        )
        
        # 2. 根据偏好进一步筛选
        if preferences:
            for key, value in preferences.items():
                results = results[results['keywords'].str.contains(value, case=False)]
                
        return results.to_dict('records')
