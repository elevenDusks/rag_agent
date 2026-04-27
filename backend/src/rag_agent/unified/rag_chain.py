"""LangChain LCEL RAG Chain

使用 LangChain Expression Language (LCEL) 构建 RAG Chain。
支持：
- 混合检索（向量 + BM25）
- 重排序
- 流式输出
- 多模版支持
"""
from typing import List, Dict, Optional, Any, AsyncGenerator, Union, Callable
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import (
    RunnablePassthrough,
    RunnableBranch,
    RunnableLambda,
)
from langchain_core.documents import Document
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from ..core.logger import logger
from ..core.config import settings
from ..models.model_registry import llm, embedding_model
from ..rag.prompt import RAGPrompt


# ============================================================
# LCEL RAG Chain 构建器
# ============================================================
class RAGChainBuilder:
    """RAG Chain 构建器

    使用 LCEL 构建灵活的 RAG Chain。

    架构：
    ┌─────────────────────────────────────────────────────────┐
    │                    RAG Chain                            │
    │  ┌──────────┐   ┌──────────┐   ┌──────────┐         │
    │  │ retrieve │ → │ rerank   │ → │ generate │         │
    │  └──────────┘   └──────────┘   └──────────┘         │
    └─────────────────────────────────────────────────────────┘
    """

    def __init__(
        self,
        retriever: Any = None,
        reranker: Any = None,
        llm_model: Any = None,
    ):
        self.retriever = retriever
        self.reranker = reranker
        self.llm = llm_model or llm
        self._chain = None
        self._stream_chain = None

    def build(
        self,
        prompt_template: str = None,
        output_key: str = "answer",
        with_history: bool = True,
    ) -> Any:
        """构建 RAG Chain

        Args:
            prompt_template: 提示词模板
            output_key: 输出键名
            with_history: 是否包含历史对话

        Returns:
            LCEL Chain
        """
        # 获取提示词模板
        if prompt_template is None:
            rag_prompt = RAGPrompt()
            prompt = rag_prompt.get_jd_template()
        else:
            prompt = ChatPromptTemplate.from_template(prompt_template)

        # 构建 Chain
        chain = (
            RunnableLambda(self._format_inputs)
            | {
                "context": RunnableLambda(self._retrieve_and_rerank),
                "question": RunnableLambda(self._get_question),
                "history": RunnableLambda(self._get_history),
            }
            | prompt
            | self.llm
            | StrOutputParser()
        )

        self._chain = chain
        return chain

    def build_with_retriever(
        self,
        retriever: Callable,
        prompt: Any,
    ) -> Any:
        """使用自定义检索器构建 Chain

        Args:
            retriever: 检索器函数
            prompt: 提示词模板

        Returns:
            LCEL Chain
        """
        chain = (
            {
                "context": retriever,
                "question": RunnablePassthrough(),
            }
            | prompt
            | self.llm
            | StrOutputParser()
        )
        return chain

    def build_conditional(
        self,
        legal_prompt: Any,
        normal_prompt: Any,
        condition_fn: Callable[[str], bool] = None,
    ) -> Any:
        """构建条件分支 Chain

        根据问题类型选择不同的提示词模板。
        """
        if condition_fn is None:
            condition_fn = self._is_legal_question

        chain = RunnableBranch(
            (
                condition_fn,
                self.build_with_retriever(
                    self._get_retriever(),
                    legal_prompt
                )
            ),
            self.build_with_retriever(
                self._get_retriever(),
                normal_prompt
            )
        )
        return chain

    def _get_retriever(self) -> Any:
        """获取检索器"""
        if self.retriever:
            return self.retriever
        # 返回默认检索器
        from ..rag.infra import load_vector_store
        # 延迟加载
        return RunnableLambda(self._async_retrieve)

    async def _async_retrieve(self, query: str) -> str:
        """异步检索"""
        if not hasattr(self, '_vector_store') or self._vector_store is None:
            _, vector_store = await load_vector_store(settings.CHROMA_NAME_JD)
            self._vector_store = vector_store
        docs = self._vector_store.similarity_search(query, k=2)
        return "\n\n".join([doc.page_content for doc in docs])

    async def _retrieve_and_rerank(self, inputs: Dict) -> str:
        """检索并重排序"""
        question = inputs.get("question", "") if isinstance(inputs, dict) else str(inputs)
        
        if self.retriever:
            docs = await self._ainvoke_retriever(question)
        else:
            docs = []

        if self.reranker and docs:
            docs = await self.reranker.rerank_documents(question, docs, k=2)

        return "\n\n".join([doc.page_content for doc in docs])

    async def _ainvoke_retriever(self, query: str) -> List[Document]:
        """异步调用检索器"""
        if callable(self.retriever):
            result = self.retriever(query)
            if hasattr(result, '__await__'):
                return await result
            return result
        return []

    def _format_inputs(self, question: str) -> Dict[str, Any]:
        """格式化输入"""
        return {"question": question}

    def _get_question(self, inputs: Dict) -> str:
        """获取问题"""
        return inputs.get("question", "")

    def _get_history(self, inputs: Dict) -> str:
        """获取历史"""
        history = inputs.get("history", [])
        if isinstance(history, list):
            lines = []
            for msg in history:
                role = "用户" if msg.get("role") == "user" else "助手"
                lines.append(f"{role}：{msg.get('content', '')}")
            return "\n".join(lines)
        return str(history) if history else ""

    def _is_legal_question(self, question: str) -> bool:
        """判断是否为法律问题"""
        legal_keywords = ["法律", "合法", "维权", "投诉", "欺诈", "违规", "消费者", "保障"]
        return any(keyword in question for keyword in legal_keywords)

    async def ainvoke(self, question: str, **kwargs) -> str:
        """异步调用 Chain"""
        if self._chain is None:
            self.build()
        return await self._chain.ainvoke(question, **kwargs)

    async def astream(self, question: str, **kwargs) -> AsyncGenerator[str, None]:
        """流式调用 Chain"""
        if self._chain is None:
            self.build()
        async for chunk in self._chain.astream(question, **kwargs):
            yield chunk


# ============================================================
# 混合检索 Chain
# ============================================================
class HybridRetrieverChain:
    """混合检索 Chain

    结合向量检索和 BM25 检索。
    """

    def __init__(
        self,
        vector_store: Any = None,
        bm25_retriever: Any = None,
        weights: List[float] = [0.6, 0.4],
    ):
        self.vector_store = vector_store
        self.bm25_retriever = bm25_retriever
        self.weights = weights

    async def retrieve(self, query: str, k: int = 4) -> List[Document]:
        """混合检索"""
        results = []

        # 向量检索
        if self.vector_store:
            vector_docs = self.vector_store.similarity_search(query, k=k)
            results.extend(vector_docs)

        # BM25 检索
        if self.bm25_retriever:
            bm25_docs = self.bm25_retriever.invoke(query)
            results.extend(bm25_docs)

        # 去重（按内容）
        seen = set()
        unique_docs = []
        for doc in results:
            content = doc.page_content[:100]
            if content not in seen:
                seen.add(content)
                unique_docs.append(doc)

        return unique_docs[:k]

    def as_runnable(self) -> RunnableLambda:
        """转换为 Runnable"""
        return RunnableLambda(self.retrieve)


# ============================================================
# 预构建的 RAG Chain
# ============================================================
class PrebuiltRAGChains:
    """预构建的 RAG Chain

    提供常用的 RAG Chain 配置。
    """

    @staticmethod
    def create_jd_help_chain(
        retriever: Any = None,
        reranker: Any = None,
    ) -> Any:
        """创建京东帮助文档 RAG Chain"""
        builder = RAGChainBuilder(
            retriever=retriever,
            reranker=reranker,
        )
        return builder.build()

    @staticmethod
    def create_legal_chain(
        retriever: Any = None,
        reranker: Any = None,
    ) -> Any:
        """创建法律文档 RAG Chain"""
        builder = RAGChainBuilder(
            retriever=retriever,
            reranker=reranker,
        )
        rag_prompt = RAGPrompt()
        return builder.build(prompt_template=rag_prompt.get_rag_jdandlaws_template().messages[0].prompt.template)

    @staticmethod
    def create_conversational_chain(
        memory_manager: Any = None,
    ) -> Any:
        """创建对话式 RAG Chain"""

        # 获取提示词
        rag_prompt = RAGPrompt()

        # 构建 Chain
        def format_inputs(question: str) -> Dict:
            history = []
            if memory_manager:
                messages = memory_manager.get_messages()
                history = [
                    {"role": "user" if isinstance(m, HumanMessage) else "assistant", "content": m.content}
                    for m in messages[-10:] if hasattr(m, 'content')
                ]
            return {"question": question, "history": history}

        chain = (
            RunnableLambda(format_inputs)
            | {
                "jd_help": RunnableLambda(lambda x: ""),  # 需要检索填充
                "question": RunnableLambda(lambda x: x.get("question", "")),
                "history_str": RunnableLambda(lambda x: x.get("history_str", "")),
            }
            | rag_prompt.get_jd_template()
            | llm
            | StrOutputParser()
        )
        return chain
