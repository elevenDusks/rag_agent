from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_chroma import Chroma
from langchain_core.documents import Document

from ..core.config import settings
from ..core.logger import logger
from ..models.model_registry import embedding_model


async def load_vector_store(collection_name):
    logger.debug(f"开始加载向量数据库：{collection_name}")
    #加载本地向量数据库
    vector_store = Chroma(
        persist_directory=settings.CHROMA_DB_PATH,
        embedding_function=embedding_model.model,
        collection_name=collection_name
    )

    #构建向量检索器
    vector_retriever = vector_store.as_retriever(search_kwargs={"k": 10})
    logger.debug(f"向量数据库加载完成：{collection_name}")
    return  vector_retriever, vector_store

async def build_bm25_retriever(vector_store):
    logger.debug("开始构建BM25检索器")
    #从向量库中拿出所有chunk
    data = vector_store.get()
    docs = [
        Document(page_content=doc)
        for doc in data["documents"]
    ]

    #构建BM25检索器
    bm25_retriever = BM25Retriever.from_documents(docs)
    bm25_retriever.k=5

    logger.debug("BM25检索器构建完成")
    return bm25_retriever

async def get_hybrid_retriever(vector_retriever, bm25_retriever):
    logger.debug("开始构建混合检索器")

    hybrid_retriever = EnsembleRetriever(
        retrievers=[vector_retriever, bm25_retriever],
        weights = [0.6, 0.4]
    )

    logger.debug("混合检索器构建完成")
    return hybrid_retriever