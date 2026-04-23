"""日志模块

该模块配置应用的日志系统，包括设置日志级别、格式和处理程序。
"""
import logging
from ..core.config import settings

# 配置日志系统
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),  # 从配置中获取日志级别
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # 日志格式
    handlers=[
        logging.StreamHandler(),  # 控制台输出
        logging.FileHandler('app.log')  # 文件输出
    ]
)

# 创建主日志记录器
logger = logging.getLogger('my-rag-agent')

def get_logger(name: str):
    """获取指定名称的日志记录器
    
    Args:
        name: 日志记录器的名称
        
    Returns:
        logging.Logger: 配置好的日志记录器实例
    """
    return logging.getLogger(f'my-rag-agent.{name}')
