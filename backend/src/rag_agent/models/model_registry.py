"""模型模块

该模块定义了应用中使用的聊天模型、嵌入模型、排序模型等。
"""
from langchain_openai import ChatOpenAI

from ..core.logger import logger
from ..core.config import settings
from langchain_openai import OpenAIEmbeddings
from sentence_transformers import CrossEncoder
from pathlib import Path

# 项目根目录地址
BASE_URL = Path(__file__).parents[4]

# 嵌入模型名称
EMBEDDING_MODEL = settings.EMBEDDING_MODEL
# 排序模型地址
EMBEDDING_MODEL_PATH = str(BASE_URL/settings.CROSS_ENCODER_MODEL_PATH)

# 创建llm模型实例
_llm_instance = None
def get_llm():
    global _llm_instance
    if _llm_instance is None:
        # 可添加日志、参数校验等逻辑
        logger.info(f"初始化llm模型：{settings.OPENAI_MODEL}")
        _llm_instance = ChatOpenAI(
            model= settings.OPENAI_MODEL,
            base_url=settings.OPENAI_BASE_URL,
            api_key=settings.OPENAI_API_KEY
        )
    return _llm_instance
llm = get_llm()

class Embedding_model:
    """
    嵌入模型
    """
    def __init__(self):
        self.model = OpenAIEmbeddings(model=EMBEDDING_MODEL)

embedding_model = Embedding_model()

# 创建CrossEncoder模型实例
_cross_encoder_instance = None
def get_cross_encoder():
    global _cross_encoder_instance
    if _cross_encoder_instance is None:
        # 可添加日志、参数校验等逻辑
        logger.info(f"初始化CrossEncoder模型：{settings.CROSS_ENCODER_NAME}")
        _cross_encoder_instance = CrossEncoder(
            settings.CROSS_ENCODER_NAME,
            cache_folder=EMBEDDING_MODEL_PATH,
        )
    return _cross_encoder_instance
crossEncoder_model = get_cross_encoder()
