"""聊天服务模块

该模块提供了与用户进行对话的核心功能，使用RAG（检索增强生成）技术生成回复。
"""
from typing import List, Optional, AsyncGenerator
from fastapi.responses import StreamingResponse
import json

from ..models.schemas import ChatResponse
from ..core.logger import get_logger
from ..rag.rag_pipeline import RAGPipeline
from ..memroy.memory import ChatMemory
from ..core.logger import logger

class ChatService:
    """聊天服务类

    负责处理用户的聊天请求，通过RAG pipeline生成智能回复。
    """
    def __init__(self):
        """初始化聊天服务

        创建RAG pipeline实例，用于后续的回复生成。
        """
        self.rag_pipeline = RAGPipeline()

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

        Raises:
            Exception: 生成回复过程中出现的任何异常
        """
        try:
            session_id = session_id or "default"
            logger.info(f"为question生成response: {question}, session_id: {session_id}")

            # 获取对话历史
            history = await ChatMemory.get_history(session_id)
            logger.info(f"获取到历史对话 {len(history)} 条")

            # 使用RAG pipeline生成回复，传入历史对话
            response = await self.rag_pipeline.retrieve(
                question=question,
                session_id=session_id,
                history=history
            )

            # 保存用户消息和AI回复到记忆
            await ChatMemory.add_message(session_id, "user", question)
            await ChatMemory.add_message(session_id, "assistant", response)

            # 构建并返回响应对象
            return ChatResponse(
                message=response,
                session_id=session_id
            )
        except Exception as e:
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
        logger.info(f"[流式] 为question生成response: {question}, session_id: {session_id}")

        # 获取对话历史
        history = await ChatMemory.get_history(session_id)
        
        # 保存用户消息
        await ChatMemory.add_message(session_id, "user", question)

        async def event_generator():
            full_response = ""
            try:
                async for chunk in self.rag_pipeline.retrieve_stream(
                    question=question,
                    session_id=session_id,
                    history=history
                ):
                    if chunk:
                        # 确保 chunk 是字符串
                        text = str(chunk) if not isinstance(chunk, str) else chunk
                        full_response += text
                        # SSE 格式
                        yield f"data: {json.dumps({'token': text, 'type': 'token'})}\n\n"
                
                # 保存助手回复
                await ChatMemory.add_message(session_id, "assistant", full_response)
                
                # 发送完成信号
                yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"
                
            except Exception as e:
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
