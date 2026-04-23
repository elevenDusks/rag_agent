from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser
from typing import Optional

from .infra import load_vector_store, build_bm25_retriever, get_hybrid_retriever
from .rerank import Rerank
from ..models.model_registry import llm
from ..rag.prompt import RAGPrompt
from ..core.config import settings
from ..core.logger import logger


class RAGPipeline:
    def __init__(self):
        pass

    async def retrieve(self, question: str, session_id: Optional[str] = None):
        logger.info("开始创建RAGPipeline")
        rag_prompt = RAGPrompt()

        # 获取重排序器
        rerank = Rerank()

        # 获取jd向量检索器 -> vector_retriever_jd
        logger.info("开始构建jd混合检索器")
        vector_retriever_jd, vector_store_jd = await load_vector_store(settings.CHROMA_NAME_JD)
        logger.info(f"0. vector_store_jd:{vector_store_jd}")
        logger.info("1. 加载:load_vector_store")
        # 获取jdbm25检索器 -> bm25_retriever_jd
        bm25_retriever_jd = await build_bm25_retriever(vector_store_jd)
        logger.info("2. 构建:build_bm25_retriever")
        # 获取jd混合检索器 -> hybrid_retriever_jd
        hybrid_retriever_jd = await get_hybrid_retriever(vector_retriever_jd, bm25_retriever_jd)
        logger.info("jd混合检索器构建成功")
        retrievered_jd = await hybrid_retriever_jd.ainvoke(question)

        # jd重排序后的前length_docs_jd个文档 -> ranked_jd_docs
        length_docs_jd = 1
        ranked_jd_docs = await rerank.rerank_documents(question, retrievered_jd, length_docs_jd)
        print(f"重排序后的文档数量：{len(ranked_jd_docs)}")
        logger.info("jd重排序成功")

        legal_keywords = ["法律", "合法", "维权", "投诉", "欺诈", "违规", "消费者", "保障"]
        # 如果用户问题不涉及法律 执行jd_pipeline流程
        chain = None
        if not any(keyword in question for keyword in legal_keywords):
            # 创建jd提示词
            logger.info("开始创建jd提示词")
            # 获取jd提示词模板 -> template_jd
            template_jd = rag_prompt.get_jd_template()
            logger.info("jd提示词模板创建成功")

            # 创建输出解析器
            parser = StrOutputParser()

            # 创建chain
            chain = template_jd | llm | parser
            logger.info("chain创建成功")
            str_jd_help = await self.get_str_from_documents(ranked_jd_docs)
            return await chain.ainvoke({"jd_help":str_jd_help,"question":question})


        else:
            # 获取law向量检索器 -> hybrid_retriever_laws
            logger.info("开始构建laws混合检索器")
            vector_retriever_laws, vector_store_laws = await load_vector_store(settings.CHROMA_NAME_LAWS)
            # 获取lawsbm25检索器 -> bm25_retriever_laws
            bm25_retriever_laws = await build_bm25_retriever(vector_store_laws)
            # 获取laws混合检索器 -> hybrid_retriever_laws
            hybrid_retriever_laws = await get_hybrid_retriever(vector_retriever_laws, bm25_retriever_laws)
            logger.info("laws混合检索器构建成功")
            retrievered_laws = await hybrid_retriever_laws.invoke(question)
            logger.info("开始重排序法律文档")
            # laws重排序后的前length_docs_laws个文档 -> ranked_laws_docs
            length_docs_laws = 1
            ranked_laws_docs = await rerank.rerank_documents(question, retrievered_laws, length_docs_laws)
            logger.info("法律文档重排序成功")

            logger.info("开始创建 jdandlaws 提示词模板")
            template_jdandlaws = await rag_prompt.get_rag_jdandlaws_template()

            # 创建输出解析器
            parser = StrOutputParser()

            chain = template_jdandlaws | llm | parser
            logger.info("chain创建成功")
            str_jd_help = await self.get_str_from_documents(ranked_jd_docs)
            str_laws = await self.get_str_from_documents(ranked_laws_docs)
            return chain.invoke({"jd_help":str_jd_help,
                                 "laws":str_laws,
                                 "question":question})


    async def get_str_from_documents(self, documents):
        str = "\n\n".join([doc.page_content for doc in documents])
        return str

