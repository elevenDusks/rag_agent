"""聊天API接口模块

该模块提供了聊天相关的API接口，用于处理用户的聊天请求。
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from ..services.chat_service import ChatService
from ..models.schemas import ChatResponse, ChatRequest

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ClearMemoryRequest(BaseModel):
    session_id: str


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, chat_service: ChatService = Depends()):
    """处理聊天请求（非流式）

    Args:
        request: 聊天请求数据
        chat_service: 聊天服务实例（通过依赖注入获取）

    Returns:
        ChatResponse: 聊天响应数据

    Raises:
        HTTPException: 处理过程中出现的任何异常
    """
    try:
        response = await chat_service.generate_response(
            request.message,
            request.session_id,
            request.context
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(request: ChatRequest, chat_service: ChatService = Depends()):
    """处理聊天请求（流式SSE）

    Args:
        request: 聊天请求数据
        chat_service: 聊天服务实例

    Returns:
        StreamingResponse: SSE 流式响应
    """
    return await chat_service.generate_response_stream(
        request.message,
        request.session_id,
        request.context
    )


@router.post("/clear-memory")
async def clear_memory(request: ClearMemoryRequest, chat_service: ChatService = Depends()):
    """清除会话记忆

    Args:
        request: 包含 session_id 的请求
        chat_service: 聊天服务实例（通过依赖注入获取）

    Returns:
        dict: 操作结果
    """
    try:
        success = await chat_service.clear_session_memory(request.session_id)
        if success:
            return {"success": True, "message": "会话记忆已清除"}
        else:
            return {"success": False, "message": "清除会话记忆失败"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
