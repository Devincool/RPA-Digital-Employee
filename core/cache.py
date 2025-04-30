"""对话缓存相关功能"""
import os
import json
import time
from collections import deque
from collections import defaultdict
from datetime import datetime, timedelta
from core.secure import SecureStorage
from core.config import Config
import threading

class DialogCache:
    """多轮对话缓存类,支持按用户id缓存对话内容并持久化存储"""
    
    _instance = None
    _instance_lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._instance_lock:
                if not cls._instance:
                    cls._instance = super(DialogCache, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, parent=None, cache_dir="cache"):
        if not hasattr(self, '_initialized'):
            self.parent = parent  # 保存父对象引用
            
            # 使用配置文件中的缓存目录，如果没有则使用默认值
            self.cache_dir = os.path.join(os.environ.get('LOCALAPPDATA'), 'Programs', 'yimai', "dialog_cache")
            self.secure_storage = SecureStorage(self.cache_dir)
            self.meta_file = "dialog_meta.json"  # 元数据文件
            self.stats_file = "user_stats.json"  # 统计数据文件
            self.mem_cache = {}  # 内存缓存
            self.last_access = {}  # 最后访问时间
            self.pending_archive = {}  # 待归档的对话
            # 从配置文件获取缓存过期时间（小时），默认1小时
            self.cache_expire_hours = getattr(Config, 'CACHE_EXPIRE_HOURS', 5)
            # 从配置文件获取内存缓存最大条数，默认30条
            self.max_cache_size = getattr(Config, 'MAX_CACHE_SIZE', 30)
            
            self.meta_data = self._load_meta()  # 加载管理数据
            self.daily_stats = self._load_daily_stats()
            
            # 添加实时统计数据
            self.current_stats = {
                "total_messages": 0,
                "unique_users": set(),
                "start_time": datetime.now()
            }
            
            self._initialized = True

    def _load_meta(self):
        """加载管理文件"""
        try:
            return self.secure_storage.load_json(self.meta_file) or {}
        except Exception as e:
            print(f"[对话缓存] 加载管理文件失败: {e}")
            return {}

    def _save_meta(self):
        """保存管理文件"""
        try:
            self.secure_storage.save_json(self.meta_file, self.meta_data)
        except Exception as e:
            print(f"[对话缓存] 保存管理文件失败: {e}")

    def _get_user_cache_dir(self, user_id):
        """获取用户缓存目录"""
        return os.path.join(self.cache_dir, str(user_id))

    def _archive_dialogs(self, user_id):
        """归档用户对话记录到加密文件"""
        if not self.pending_archive.get(user_id):
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dialog_file = f"dialog_{user_id}_{timestamp}.json"
            
            dialog_data = {
                "user_id": user_id,
                "timestamp": time.time(),
                "dialogs": self.pending_archive[user_id]
            }
            
            self.secure_storage.save_json(dialog_file, dialog_data)
            self.pending_archive[user_id] = []
                
        except Exception as e:
            print(f"[对话缓存] 归档对话失败: {str(e)}")

    def _clean_expired_cache(self):
        """清理过期的内存缓存"""
        now = datetime.now()
        expired = []
        
        # 第一步：找出过期的缓存
        for user_id, last_time in self.last_access.items():
            if now - datetime.fromtimestamp(last_time) > timedelta(hours=self.cache_expire_hours):
                expired.append(user_id)
                
        # 第二步：归档并删除过期缓存
        for user_id in expired:
            try:
                # 确保用户目录存在
                user_dir = self._get_user_cache_dir(user_id)
                if not os.path.exists(user_dir):
                    os.makedirs(user_dir)
                    
                # 归档对话
                if user_id in self.pending_archive and self.pending_archive[user_id]:
                    self._archive_dialogs(user_id)
                    
                # 删除缓存
                if user_id in self.mem_cache:
                    del self.mem_cache[user_id]
                if user_id in self.last_access:
                    del self.last_access[user_id]
                    
            except Exception as e:
                print(f"清理缓存失败: {str(e)}")

    def add_dialog(self, user_id, role, content):
        """添加对话记录并更新统计数据"""
        dialog = {
            "role": role,
            "content": content,
            "timestamp": time.time()
        }

        if role == "system" and content.startswith("<人工介入>"):
            # 人工介入，重组对话
            # 归档当前对话
            self.archive_current_dialog(user_id)
            
            # 清空该用户的对话缓存
            self.mem_cache[user_id].clear()
            
            # 提取人工介入的内容
            human_content = content[content.find("<人工介入>")+6:content.find("</人工介入>")]
            
            # 获取最近6条历史记录
            user_dir = self._get_user_cache_dir(user_id)
            history = []
            if os.path.exists(user_dir):
                files = sorted(os.listdir(user_dir), reverse=True)
                if files:
                    latest_file = os.path.join(user_dir, files[0])
                    with open(latest_file, "r", encoding="utf-8") as f:
                        dialog_data = json.load(f)
                        history = dialog_data[-6:] if len(dialog_data) > 6 else dialog_data
            
            # 重组对话缓存
            # 添加人工介入内容作为第一条
            if history and history[0]["role"] == "system":
                history[0]["content"] = history[0]["content"] + "." + human_content 
            else:
                self.mem_cache[user_id].append({
                    "role": "system",
                    "content": human_content,
                    "timestamp": time.time()
                })
            
            # 添加历史记录
            for msg in history:
                self.mem_cache[user_id].append(msg)
            
            return

        # 更新内存缓存
        if user_id not in self.mem_cache:
            self.mem_cache[user_id] = deque(maxlen=self.max_cache_size)
        
        # 检查是否需要归档
        if len(self.mem_cache[user_id]) >= self.max_cache_size - 1:  # 留出一个位置给新消息
            # 主动归档，保留最新的 max_cache_size//2 条消息
            self.archive_current_dialog(user_id, keep_latest=self.max_cache_size//2)
        
        self.mem_cache[user_id].append(dialog)
        self.last_access[user_id] = time.time()

        # 添加到待归档队列
        if user_id not in self.pending_archive:
            self.pending_archive[user_id] = []
        self.pending_archive[user_id].append(dialog)

        # 更新元数据
        if user_id not in self.meta_data:
            self.meta_data[user_id] = {}
        self.meta_data[user_id]["last_chat_time"] = time.time()
        self._save_meta()

        # 更新用户统计
        self.update_user_stats(user_id, role=role)

        self._clean_expired_cache()

    def get_history(self, user_id, limit=None):
        """获取用户历史对话记录"""
        # 使用配置的历史记录限制数量
        limit = limit or getattr(Config, 'MAX_HISTORY_LIMIT', 10)
        
        # 如果用户在内存缓存中，直接返回
        if user_id in self.mem_cache:
            self.last_access[user_id] = time.time()
            return list(self.mem_cache[user_id])

        # 如果不在内存缓存中，尝试从加密文件加载
        try:
            # 查找最新的对话文件
            pattern = f"dialog_{user_id}_*.json"
            files = self.secure_storage.list_files(pattern)
            if not files:
                return []
            
            # 获取最新的文件
            latest_file = sorted(files)[-1]
            dialog_data = self.secure_storage.load_json(latest_file)
            if dialog_data and "dialogs" in dialog_data:
                return dialog_data["dialogs"][-limit:]
            return []
            
        except Exception as e:
            print(f"[对话缓存] 加载对话历史失败: {e}")
            return []
    
    def get_last_message(self, user_id):
        """获取用户最后一条消息
        """
        return self.mem_cache[user_id][-1]["content"]

    def get_user_info(self, user_id):
        """获取用户信息
        
        Args:
            user_id: 用户id
            
        Returns:
            dict: 用户信息字典
        """
        return self.meta_data.get(str(user_id), {})

    def update_user_info(self, user_id, info):
        """更新用户信息
        
        Args:
            user_id: 用户id
            info: 要更新的信息字典
        """
        if user_id not in self.meta_data:
            self.meta_data[user_id] = {}
        self.meta_data[user_id].update(info)
        self._save_meta()

    def is_client_in_memcache(self, user_id):
        """判断用户是否有咨询过，可用于避免频繁点击商品tab选项卡
        """
        return user_id in self.mem_cache

    def _load_daily_stats(self):
        """加载每日用户统计数据"""
        try:
            return self.secure_storage.load_json(self.stats_file) or {}
        except Exception as e:
            print(f"[对话缓存] 加载统计数据失败: {e}")
            return {}

    def _save_daily_stats(self):
        """保存每日用户统计数据"""
        try:
            self.secure_storage.save_json(self.stats_file, self.daily_stats)
        except Exception as e:
            print(f"[对话缓存] 保存统计数据失败: {e}")

    def update_user_stats(self, user_id, role="user"):
        """更新用户访问统计"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            
            # 初始化今日数据
            if today not in self.daily_stats:
                self.daily_stats[today] = {
                    "total_users": 0,
                    "unique_users": [],
                    "active_hours": {},
                    "user_list": []
                }
            
            # 更新统计数据
            current_hour = datetime.now().strftime("%H")
            stats = self.daily_stats[today]
            
            # 如果是新用户
            if user_id not in stats["unique_users"]:
                stats["total_users"] += 1
                stats["unique_users"].append(user_id)
                stats["user_list"].append({
                    "user_id": user_id,
                    "first_visit": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
            
            # 只统计用户发送的消息
            if role == "user":
                # 更新活跃时段统计（记录消息数）
                stats["active_hours"][current_hour] = stats["active_hours"].get(current_hour, 0) + 1
                
                # 更新实时统计
                self.current_stats["total_messages"] += 1
                self.current_stats["unique_users"].add(user_id)
                
                # 通过父对象发送信号
                if self.parent and hasattr(self.parent, 'stats_updated'):
                    self.parent.stats_updated.emit({
                        "total_messages": self.current_stats["total_messages"],
                        "unique_users": len(self.current_stats["unique_users"]),
                        "start_time": self.current_stats["start_time"]
                    })
            
            # 保存统计数据
            self._save_daily_stats()
        except Exception as e:
            print(f"更新用户统计失败: {str(e)}")

    def get_current_stats(self):
        """获取当前统计数据"""
        return {
            "total_messages": self.current_stats["total_messages"],
            "unique_users": len(self.current_stats["unique_users"]),
            "start_time": self.current_stats["start_time"]
        }

    def get_daily_stats(self, date=None):
        """获取指定日期的用户统计数据
        
        Args:
            date: 日期字符串，格式为YYYY-MM-DD，默认为今天
            
        Returns:
            dict: 包含以下统计数据的字典：
                - total_users: 总用户数
                - unique_users: 独立用户数
                - active_hours: 各时段活跃度
                - user_list: 用户访问列表
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
            
        if date in self.daily_stats:
            stats = self.daily_stats[date]
            return {
                "date": date,
                "total_users": stats["total_users"],
                "unique_users": len(stats["unique_users"]),
                "active_hours": stats["active_hours"],
                "user_list": stats["user_list"]
            }
        return None

    def get_stats_summary(self, days=7):
        """获取最近几天的统计数据汇总
        
        Args:
            days: 要统计的天数，默认7天
            
        Returns:
            dict: 包含以下统计数据的字典：
                - total_period_users: 周期内总用户数
                - avg_daily_users: 日均用户数
                - peak_hour: 最活跃时段
                - daily_stats: 每日统计数据列表
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days-1)
        
        summary = {
            "period": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            "total_period_users": 0,
            "avg_daily_users": 0,
            "peak_hour": "00",
            "daily_stats": []
        }
        
        total_hours = defaultdict(int)
        valid_days = 0
        
        # 统计每一天
        current = start_date
        while current <= end_date:
            date = current.strftime("%Y-%m-%d")
            if date in self.daily_stats:
                stats = self.daily_stats[date]
                daily_data = {
                    "date": date,
                    "total_users": stats["total_users"],
                    "unique_users": len(stats["unique_users"])
                }
                summary["daily_stats"].append(daily_data)
                summary["total_period_users"] += stats["total_users"]
                
                # 累计各时段数据
                for hour, count in stats["active_hours"].items():
                    total_hours[hour] += count
                    
                valid_days += 1
            
            current += timedelta(days=1)
        
        # 计算平均值和峰值
        if valid_days > 0:
            summary["avg_daily_users"] = round(summary["total_period_users"] / valid_days, 2)
            
        if total_hours:
            summary["peak_hour"] = max(total_hours.items(), key=lambda x: x[1])[0]
            
        return summary

    def archive_current_dialog(self, user_id, keep_latest=5):
        """主动归档当前对话并只保留最新的n条记录
        
        Args:
            user_id: 用户ID
            keep_latest: 要在内存中保留的最新消息数量，默认5条
            
        Returns:
            bool: 归档成功返回True，失败返回False
        """
        try:
            if user_id not in self.mem_cache:
                print(f"用户 {user_id} 没有对话记录")
                return False
                
            # 获取当前所有对话
            current_dialogs = list(self.mem_cache[user_id])
            
            if len(current_dialogs) <= keep_latest:
                print(f"当前对话数量({len(current_dialogs)})不超过保留数量({keep_latest})，无需归档")
                return True
                
            # 分离要归档的对话和要保留的对话
            to_archive = current_dialogs[:-keep_latest]  # 除了最新的keep_latest条都归档
            to_keep = current_dialogs[-keep_latest:]     # 保留最新的keep_latest条
            
            # 添加要归档的对话到pending_archive
            if user_id not in self.pending_archive:
                self.pending_archive[user_id] = []
            self.pending_archive[user_id].extend(to_archive)
            
            # 执行归档
            self._archive_dialogs(user_id)
            
            # 更新内存缓存，只保留最新的keep_latest条记录
            self.mem_cache[user_id] = deque(to_keep, maxlen=self.max_cache_size)
            
            print(f"已归档 {len(to_archive)} 条对话，保留最新的 {len(to_keep)} 条记录")
            return True
            
        except Exception as e:
            print(f"归档对话失败: {str(e)}")
            return False