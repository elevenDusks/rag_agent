"""聊天服务模块

使用 LangChain/LangGraph 架构的聊天服务。
支持两种模式：
1. Unified 模式（默认）：使用统一的 LangGraph Agent
2. RAG Pipeline 模式：直接使用 RAG 检索生成
"""
import time
import json
from typing import List, Optional, AsyncGenerator, Dict, Any
from fastapi.responses import StreamingResponse

from ..models.schemas import ChatResponse
from ..core.logger import logger
from ..memroy.memory import ChatMemory
from ..middleware.metrics import metrics_collector, QueryMetrics
from ..core.config import settings

# 统一 LangGraph Agent
from ..unified import UnifiedAgent, AgentConfig, LangChainMemoryManager


class ChatService:
    """聊天服务类

    负责处理用户的聊天请求，使用 LangChain/LangGraph 架构。

    架构：
    ┌─────────────────────────────────────────────────────────────┐
    │                      ChatService                             │
    │  ┌─────────────────────────────────────────────────────┐   │
    │  │              UnifiedAgent (LangGraph)               │   │
    │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐        │   │
    │  │  │  route   │→│ retrieve │→│ generate │        │   │
    │  │  └──────────┘  └──────────┘  └──────────┘        │   │
    │  └─────────────────────────────────────────────────────┘   │
    │                              ↓                            │
    │  ┌─────────────────────────────────────────────────────┐   │
    │  │          LangChainMemoryManager                      │   │
    │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐        │   │
    │  │  │ Buffer   │  │ Vector   │  │ Summary  │        │   │
    │  │  │ Memory   │  │ Memory   │  │ Memory   │        │   │
    │  │  └──────────┘  └──────────┘  └──────────┘        │   │
    │  └─────────────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────┘
    """

    def __init__(self, use_unified: bool = True):
        """初始化聊天服务

        Args:
            use_unified: 是否使用 Unified Agent 模式，默认为 True
        """
        self.use_unified = use_unified

        # Unified Agent 模式
        if self.use_unified:
            config = AgentConfig(
                max_iterations=10,
                use_rag=True,
                use_tools=True,
            )
            self.agent = UnifiedAgent(config=config)
            logger.info("ChatService 初始化完成，使用 Unified LangGraph Agent 模式")
        else:
            # RAG Pipeline 模式（保留兼容）
            from ..rag.rag_pipeline import RAGPipeline
            self.rag_pipeline = RAGPipeline()
            self.agent = None
            logger.info("ChatService 初始化完成，使用 RAG Pipeline 模式")

    async def generate_response(
        self,
        question: str,
        session_id: Optional[str] = None,
        context: Optional[List[str]] = None
    ) -> ChatResponse:
        """生成用户消息的回复

        Args:
            question: 用户发送的消息
            session_id: 会话ID，用于保持上下文一致性
            context: 可选的上下文信息列表

        Returns:
            ChatResponse: 包含回复消息和会话ID的响应对象
        """
        session_id = session_id or "default"
        total_start = time.perf_counter()
        generation_start = total_start

        try:
            logger.info(f"为question生成response: {question}, session_id: {session_id}")

            # 保存用户消息（保持兼容性）
            await ChatMemory.add_message(session_id, "user", question)

            # 根据模式选择生成方式
            if self.use_unified and self.agent:
                # Unified Agent 模式
                result = await self.agent.run(
                    question=question,
                    session_id=session_id,
                )
                response = result.get("answer", "")

                # 保存助手回复
                await ChatMemory.add_message(session_id, "assistant", response)
            else:
                # RAG Pipeline 模式
                history = await ChatMemory.get_history(session_id)
                response = await self.rag_pipeline.retrieve(
                    question=question,
                    session_id=session_id,
                    history=history
                )
                await ChatMemory.add_message(session_id, "assistant", response)

            generation_end = time.perf_counter()
            generation_time_ms = int((generation_end - generation_start) * 1000)
            total_end = time.perf_counter()
            total_time_ms = int((total_end - total_start) * 1000)

            # 记录指标
            metrics = QueryMetrics(
                session_id=session_id,
                user_id=None,
                query=question,
                collection_name=settings.CHROMA_NAME_JD,
                generation_time_ms=generation_time_ms,
                total_latency_ms=total_time_ms,
                is_success=True,
                response=response[:1000] if response else None,
            )
            await metrics_collector.record(metrics)

            return ChatResponse(
                message=response,
                session_id=session_id
            )

        except Exception as e:
            total_end = time.perf_counter()
            total_time_ms = int((total_end - total_start) * 1000)

            # 记录失败指标
            metrics = QueryMetrics(
                session_id=session_id,
                user_id=None,
                query=question,
                collection_name=settings.CHROMA_NAME_JD,
                total_latency_ms=total_time_ms,
                is_success=False,
                error_message=str(e)[:500],
            )
            await metrics_collector.record(metrics)

            logger.error(f"Error generating response: {e}")
            raise

    async def clear_session_memory(self, session_id: str) -> bool:
        """清除会话记忆

        Args:
            session_id: 会话ID

        Returns:
            bool: 是否成功清除
        """
        try:
            # 清除 Unified Agent 记忆
            if self.use_unified and self.agent:
                self.agent.clear_memory(session_id)

            # 清除 ChatMemory
            await ChatMemory.clear_memory(session_id)
            return True
        except Exception as e:
            logger.error(f"清除会话记忆失败: {e}")
            return False

    async def generate_response_stream(
        self,
        question: str,
        session_id: Optional[str] = None,
        context: Optional[List[str]] = None
    ) -> StreamingResponse:
        """流式生成回复（SSE）

        Args:
            question: 用户消息
            session_id: 会话ID
            context: 可选的上下文信息

        Returns:
            StreamingResponse: SSE 流式响应
        """
        session_id = session_id or "default"
        total_start = time.perf_counter()
        first_token_time = None

        logger.info(f"[流式] 为question生成response: {question}, session_id: {session_id}")

        # 保存用户消息
        await ChatMemory.add_message(session_id, "user", question)

        async def event_generator():
            full_response = ""
            generation_start = time.perf_counter()

            try:
                if self.use_unified and self.agent:
                    # Unified Agent 流式模式
                    async for chunk in self.agent.run_stream(
                        question=question,
                        session_id=session_id,
                    ):
                        nonlocal first_token_time
                        if first_token_time is None:
                            first_token_time = time.perf_counter()

                        if chunk:
                            text = str(chunk) if not isinstance(chunk, str) else chunk
                            full_response += text
                            yield f"data: {json.dumps({'token': text, 'type': 'token'})}\n\n"
                else:
                    # RAG Pipeline 流式模式
                    history = await ChatMemory.get_history(session_id)
                    async for chunk in self.rag_pipeline.retrieve_stream(
                        question=question,
                        session_id=session_id,
                        history=history
                    ):
                        nonlocal first_token_time
                        if first_token_time is None:
                            first_token_time = time.perf_counter()

                        if chunk:
                            text = str(chunk) if not isinstance(chunk, str) else chunk
                            full_response += text
                            yield f"data: {json.dumps({'token': text, 'type': 'token'})}\n\n"

                # 保存助手回复
                await ChatMemory.add_message(session_id, "assistant", full_response)
                generation_end = time.perf_counter()
                generation_time_ms = int((generation_end - generation_start) * 1000)
                ttft_ms = int((first_token_time - generation_start) * 1000) if first_token_time else 0
                total_end = time.perf_counter()
                total_time_ms = int((total_end - total_start) * 1000)

                # 记录指标
                metrics = QueryMetrics(
                    session_id=session_id,
                    user_id=None,
                    query=question,
                    collection_name=settings.CHROMA_NAME_JD,
                    generation_time_ms=generation_time_ms,
                    total_latency_ms=total_time_ms,
                    ttft_ms=ttft_ms,
                    is_success=True,
                    response=full_response[:1000] if full_response else None,
                )
                await metrics_collector.record(metrics)

                # 发送完成信号
                yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"

            except Exception as e:
                total_end = time.perf_counter()
                total_time_ms = int((total_end - total_start) * 1000)

                # 记录失败指标
                metrics = QueryMetrics(
                    session_id=session_id,
                    user_id=None,
                    query=question,
                    collection_name=settings.CHROMA_NAME_JD,
                    total_latency_ms=total_time_ms,
                    is_success=False,
                    error_message=str(e)[:500],
                )
                await metrics_collector.record(metrics)

                logger.error(f"[流式] 生成响应失败: {e}")
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )


# ============================================================
# LangChain/LangGraph 架构图
# ============================================================
"""
完整架构：

┌─────────────────────────────────────────────────────────────────────────┐
│                           LangChain/LangGraph                            │
│                              完整架构图                                    │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                            ChatService                                    │
│                              │                                           │
│           ┌──────────────────┴──────────────────┐                         │
│           │                                     │                        │
│           ▼                                     ▼                        │
│  ┌─────────────────────┐          ┌─────────────────────┐             │
│  │   UnifiedAgent      │          │   RAGPipeline       │             │
│  │   (LangGraph)       │          │   (兼容模式)         │             │
│  └──────────┬──────────┘          └─────────────────────┘             │
│             │                                                              │
│  ┌──────────┴──────────────────────────────────────────┐                │
│  │                   LangGraph Workflow                  │                │
│  │                                                         │                │
│  │  ┌───────────┐    ┌───────────┐    ┌───────────┐      │                │
│  │  │   route  │───▶│ retrieve  │───▶│ generate  │      │                │
│  │  └───────────┘    └───────────┘    └───────────┘      │                │
│  │        │                                                   │                │
│  │        ▼                                                   │                │
│  │  ┌───────────┐                                             │                │
│  │  │   tools  │                                             │                │
│  │  └───────────┘                                             │                │
│  └────────────────────────────────────────────────────────────┘                │
│             │                                                              │
│             ▼                                                              │
│  ┌────────────────────────────────────────────────────────────┐             │
│  │                   LangChain Memory                          │             │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │             │
│  │  │   Buffer    │  │   Vector    │  │   Summary   │         │             │
│  │  │   Memory    │  │   Memory    │  │   Memory    │         │             │
│  │  │  (Redis)    │  │  (Chroma)   │  │   (LLM)     │         │             │
│  │  └─────────────┘  └─────────────┘  └─────────────┘         │             │
│  └────────────────────────────────────────────────────────────┘             │
│             │                                                              │
│             ▼                                                              │
│  ┌────────────────────────────────────────────────────────────┐             │
│  │                   LangChain LCEL Chains                      │             │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐               │             │
│  │  │  Retriever │→│ Reranker  │→│ Generator │               │             │
│  │  └───────────┘  └───────────┘  └───────────┘               │             │
│  └────────────────────────────────────────────────────────────┘             │
└─────────────────────────────────────────────────────────────────────────────┘
"""
