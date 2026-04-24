"""模型模块

该模块定义了应用中使用的聊天模型、嵌入模型、排序模型等。
"""
from langchain_openai import ChatOpenAI
from functools import lru_cache

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
            api_key=settings.OPENAI_API_KEY,
            streaming=True  # 启用流式输出
        )
    return _llm_instance
llm = get_llm()

class Embedding_model:
    """
    嵌入模型，支持缓存
    """
    def __init__(self):
        self.model = OpenAIEmbeddings(model=EMBEDDING_MODEL)
        self._embedding_cache = {}
        self._cache_max_size = 500

    def _normalize_text(self, text: str) -> str:
        """标准化文本用于缓存key"""
        return text.lower().strip()

    def embed_query(self, text: str):
        """带缓存的嵌入查询"""
        cache_key = self._normalize_text(text)
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]
        
        result = self.model.embed_query(text)
        
        # LRU 缓存
        if len(self._embedding_cache) >= self._cache_max_size:
            # 移除最早的条目
            self._embedding_cache.pop(next(iter(self._embedding_cache)))
        self._embedding_cache[cache_key] = result
        
        return result
    
    def embed_documents(self, texts: list):
        """文档嵌入（不缓存）"""
        return self.model.embed_documents(texts)

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
