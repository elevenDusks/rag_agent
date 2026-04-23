"""聊天API接口模块

该模块提供了聊天相关的API接口，用于处理用户的聊天请求。
"""
from fastapi import APIRouter, Depends, HTTPException
from ..services.chat_service import ChatService
from ..models.schemas import ChatResponse, ChatRequest

router = APIRouter(prefix="/api/chat", tags=["chat"])



@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, chat_service: ChatService = Depends()):
    """处理聊天请求

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
