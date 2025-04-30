"""
社区版文件存储工具
移除了加密操作，使用普通文件存储方式，方便配置和调试
"""

from datetime import datetime
import json
import os
import csv
from typing import Any, Dict, List
import pandas as pd
from io import BytesIO

# 定义默认缓存目录
DEFAULT_CACHE_DIR = os.path.join(os.environ.get('LOCALAPPDATA'), 'Programs', 'yimai')


class SecureStorage:
    def __init__(self, cache_dir=None):
        """初始化存储
        
        Args:
            cache_dir: 可选的缓存目录路径。如果不指定，使用 AppData/Local/Programs/yimai
        """

        self.user_name = ""
        self.minio_client = None

        if cache_dir is None:
            self.cache_dir = DEFAULT_CACHE_DIR
        else:
            self.cache_dir = cache_dir
        
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
        except Exception as e:
            print(f"[SecureStorage] 初始化失败: {str(e)}")
            raise

    def _get_file_path(self, file_path, user_name=""):
        """获取完整的文件路径
        
        如果传入的是相对路径且不在 cache_dir 中，则将其放在 cache_dir 下
        如果传入的是绝对路径，则直接使用
        """
        if os.path.isabs(file_path):
            target_dir = os.path.dirname(file_path)
            os.makedirs(target_dir, exist_ok=True)
            return file_path
        else:
            # 如果文件路径已经包含 cache_dir，则不再添加
            if self.cache_dir in file_path:
                return file_path

            if user_name!="":
                os.makedirs(os.path.join(self.cache_dir, user_name), exist_ok=True)
                return os.path.join(self.cache_dir, user_name, file_path)
            else:
                return os.path.join(self.cache_dir, file_path)

    def save_json(self, file_path, data, upload=True):
        """保存 JSON 数据到文件"""
        try:
            # 确保目标目录存在
            full_path = self._get_file_path(file_path, self.user_name)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # 将数据保存为JSON文件
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"[保存] 保存文件失败: {str(e)}")
            print(f"[保存] 异常类型: {type(e)}")
            raise

    def load_json(self, file_path):
        """从文件加载 JSON 数据"""
        try:
            full_path = self._get_file_path(file_path, self.user_name)
            if not os.path.exists(full_path):
                print(f"[加载] 文件不存在: {full_path}")
                return None
            
            with open(full_path, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            print(f"[加载] 加载文件失败: {str(e)}")
            print(f"[加载] 异常类型: {type(e)}")
            print(f"[加载] 文件大小: {os.path.getsize(full_path) if os.path.exists(full_path) else 'N/A'} 字节")
            return None

    def save_csv(self, filename: str, df: pd.DataFrame):
        """保存 DataFrame 到 CSV
        
        Args:
            filename: 文件名
            df: pandas DataFrame 对象
        """
        try:
            # 确保目标目录存在
            full_path = self._get_file_path(filename)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # 保存为CSV文件
            df.to_csv(full_path, index=False)
                
        except Exception as e:
            print(f"[保存] 保存CSV文件失败: {str(e)}")
            raise

    def load_csv(self, filename: str) -> pd.DataFrame:
        """从文件加载 DataFrame
        
        Args:
            filename: 文件名
            
        Returns:
            pandas DataFrame 对象，如果加载失败则返回 None
        """
        try:
            full_path = self._get_file_path(filename)
            if not os.path.exists(full_path):
                print(f"[加载] 文件不存在: {full_path}")
                return None
                
            return pd.read_csv(full_path)
                
        except Exception as e:
            print(f"[加载] 加载CSV文件失败: {str(e)}")
            return None

    def save_text(self, text: str, filename: str):
        """保存文本数据"""
        try:
            # 确保目标目录存在
            full_path = self._get_file_path(filename)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # 保存文本文件
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(text)
                
        except Exception as e:
            print(f"保存文本文件失败: {str(e)}")
            raise
    
    def load_text(self, filename: str) -> str:
        """加载文本数据"""
        try:
            full_path = self._get_file_path(filename)
            if not os.path.exists(full_path):
                return ""
                
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
                
        except Exception as e:
            print(f"加载文本文件失败: {str(e)}")
            return ""

    def list_files(self, pattern):
        """列出匹配指定模式的文件"""
        try:
            import glob
            files = glob.glob(os.path.join(self.cache_dir, pattern))
            return [os.path.basename(f) for f in files]
        except Exception as e:
            print(f"[错误] 列出文件失败: {str(e)}")
            return []

# 创建一个全局实例
secure_storage = SecureStorage()





