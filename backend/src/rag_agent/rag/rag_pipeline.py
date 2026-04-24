from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser
from typing import Optional, List
import asyncio

from .infra import load_vector_store, build_bm25_retriever, get_hybrid_retriever
from .rerank import Rerank
from ..models.model_registry import llm
from ..rag.prompt import RAGPrompt
from ..core.config import settings
from ..core.logger import logger


class RAGPipeline:
    """RAG Pipeline 单例，缓存检索器和重排序器"""
    
    _instance: Optional['RAGPipeline'] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if RAGPipeline._initialized:
            return
        RAGPipeline._initialized = True
        logger.info("初始化 RAGPipeline 单例")
        self._jd_hybrid_retriever = None
        self._jd_vector_store = None
        self._reranker = None
        self._init_lock = asyncio.Lock()
        self._ready = asyncio.Event()

    async def _ensure_initialized(self):
        """确保检索器已初始化"""
        if self._jd_hybrid_retriever is not None:
            return
        
        async with self._init_lock:
            if self._jd_hybrid_retriever is None:
                logger.info("开始初始化 JD 检索器...")
                
                # 加载向量库
                vector_retriever, vector_store = await load_vector_store(settings.CHROMA_NAME_JD)
                self._jd_vector_store = vector_store
                
                # 构建 BM25
                bm25 = await build_bm25_retriever(vector_store)
                
                # 构建混合检索器
                self._jd_hybrid_retriever = await get_hybrid_retriever(vector_retriever, bm25)
                
                # 初始化重排序器
                self._reranker = Rerank()
                
                logger.info("JD 检索器初始化完成")
                self._ready.set()

    async def retrieve(self, question: str, session_id: Optional[str] = None, history: Optional[List[dict]] = None):
        # 确保初始化
        await self._ensure_initialized()
        
        logger.info("开始RAG检索")
        rag_prompt = RAGPrompt()

        # 使用缓存的检索器
        retrievered_jd = await self._jd_hybrid_retriever.ainvoke(question)
        logger.info(f"检索到 {len(retrievered_jd)} 个文档")

        # 重排序 - 降到 2 个
        length_docs_jd = 2
        ranked_jd_docs = await self._reranker.rerank_documents(question, retrievered_jd, length_docs_jd)
        print(f"重排序后的文档数量：{len(ranked_jd_docs)}")
        logger.info("jd重排序成功")

        str_jd_help = await self.get_str_from_documents(ranked_jd_docs)

        legal_keywords = ["法律", "合法", "维权", "投诉", "欺诈", "违规", "消费者", "保障"]
        
        if not any(keyword in question for keyword in legal_keywords):
            # JD 流程
            template_jd = rag_prompt.get_jd_template(history)
            parser = StrOutputParser()
            chain = template_jd | llm | parser
            return await chain.ainvoke({"jd_help": str_jd_help, "question": question})
        else:
            # 法律流程暂不优化
            raise NotImplementedError("法律流程待优化")

    async def get_str_from_documents(self, documents):
        return "\n\n".join([doc.page_content for doc in documents])
