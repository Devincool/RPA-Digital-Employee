from abc import ABC, abstractmethod

class IMAdapterBase(ABC):
    """IM软件适配器基类"""
    
    @property
    @abstractmethod
    def MainWindow_touxiang_group(self):
        pass
    
    @property
    @abstractmethod
    def MainWindow_chat_windowx(self):
        pass
    
    @property
    @abstractmethod
    def Search_Good_Flow_search_button(self):
        pass
    
    @property
    @abstractmethod 
    def Search_Good_Flow_input_control(self):
        pass
    
    @property
    @abstractmethod
    def Search_Good_Flow_sendgood_button(self):
        pass
    
    @property
    @abstractmethod
    def Check_Order_Flow_order_table_control(self):
        pass
    
    @property
    @abstractmethod
    def Check_Order_Flow_order_id(self):
        pass
    
    @property
    @abstractmethod
    def MessageList_Control_msg_label(self):
        pass
    
    @property
    @abstractmethod
    def MessageList_Control_msg_list(self):
        pass
    
    @property
    @abstractmethod
    def DialogWindow_screen_shot_control_x(self):
        pass
    
    @property
    @abstractmethod
    def DialogWindow_user_id_in_chat_control(self):
        pass
    
    @property
    @abstractmethod
    def DialogWindow_last_message_group_control(self):
        pass
    
    @property
    @abstractmethod
    def DialogWindow_last_message(self):
        """获取最后一条消息"""
        pass

    @abstractmethod
    def get_message_by_index(self, index):
        """根据索引获取消息
        
        Args:
            index: 消息索引，从2开始
        """
        pass

    @abstractmethod
    def get_message_group_by_index(self, index):
        """根据索引获取消息组控件
        
        Args:
            index: 消息索引，从2开始
        """
        pass

    @property
    @abstractmethod
    def DialogWindow_input_control(self):
        pass
    
    @property
    @abstractmethod
    def ManageWindow_service_name(self):
        pass
    
    @property
    @abstractmethod
    def ManageWindow_good_name(self):
        pass
    
    @property
    @abstractmethod
    def ManageWindow_good_table_control(self):
        pass
    
    @property
    @abstractmethod
    def ManageWindow_order_table_control(self):
        pass
    
    @property
    @abstractmethod
    def ManageWindow_modify_price_button(self):
        pass
    
    @property
    @abstractmethod
    def Price_Editwindow_price_edit_control(self):
        pass
    
    @property
    @abstractmethod
    def Price_Editwindow_confirm_button(self):
        pass

class IMAdapterFactory:
    """IM适配器工厂类"""
    
    _adapters = {}
    
    @classmethod
    def get_adapter(cls, version):
        """获取指定版本的适配器实例
        
        Args:
            version: 版本号字符串，如 "1.21.18"
            
        Returns:
            IMAdapterBase: 适配器实例
            
        Raises:
            ValueError: 当指定版本不存在时抛出
        """
        adapter_class = cls._adapters.get(version)
        if not adapter_class:
            raise ValueError(f"Unsupported IM version: {version}")
        return adapter_class()
    
    @classmethod
    def register_adapter(cls, version, adapter_class):
        """注册新的适配器
        
        Args:
            version: 版本号字符串
            adapter_class: 适配器类
        """
        cls._adapters[version] = adapter_class 