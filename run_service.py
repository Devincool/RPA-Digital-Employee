import sys
import os
import signal
from pathlib import Path

# 添加项目根目录到Python路径
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from core.CustomerService import CustomerService

def signal_handler(signum, frame):
    """处理退出信号"""
    print("\n检测到退出信号，正在停止服务...")
    if hasattr(signal_handler, 'customer_service'):
        signal_handler.customer_service.stop()
    sys.exit(0)

def main():
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 创建并启动客服服务
    customer_service = CustomerService()
    signal_handler.customer_service = customer_service  # 保存实例引用以便信号处理
    
    try:
        if customer_service.launch_im_app():
            print("IM应用启动成功，开始检查消息")
            customer_service.check_new_messages()
        else:
            print("IM应用启动失败")
            sys.exit(1)
    except Exception as e:
        print(f"运行服务时发生异常: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main() 