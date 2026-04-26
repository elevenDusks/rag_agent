"""Agent API 接口模块

提供 Agent 相关的 API 接口，包括对话、工具管理等。
"""
import time
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import json

from ..models.schemas import (
    AgentRequest, AgentResponse, AgentResponse,
    ToolListResponse, ToolSchema,
    ToolExecuteRequest, ToolExecuteResponse
)
from ..agent.core.agent import AgentConfig, AgentType
from ..agent.core.react_agent import ReActAgent
from ..agent.tools import ToolRegistry
from ..agent.tools.knowledge_search import get_knowledge_search_tool
from ..agent.tools.calculator import get_calculator_tool
from ..agent.tools.datetime_tool import get_datetime_tool
from ..agent.tools.web_search import get_web_search_tool, DDGS_AVAILABLE
from ..core.logger import logger

router = APIRouter(prefix="/api/agent", tags=["agent"])

# 全局工具注册表（延迟初始化）
_tool_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    """获取工具注册表（单例）"""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
        _register_default_tools(_tool_registry)
    return _tool_registry


def _register_default_tools(registry: ToolRegistry):
    """注册默认工具"""
    # 知识库搜索
    registry.register(get_knowledge_search_tool(), collection="default")
    
    # 计算器
    registry.register(get_calculator_tool(), collection="default")
    
    # 日期时间
    registry.register(get_datetime_tool(), collection="default")
    
    # 网络搜索
    if DDGS_AVAILABLE:
        registry.register(get_web_search_tool(), collection="default")
    
    logger.info(f"已注册 {len(registry)} 个默认工具")


def get_agent(agent_type: str = "react") -> ReActAgent:
    """创建 Agent 实例"""
    registry = get_tool_registry()
    
    config = AgentConfig(
        agent_type=AgentType(agent_type),
        max_iterations=10,
        tools=registry.list_all()
    )
    
    return ReActAgent(config)


@router.post("/chat", response_model=AgentResponse)
async def agent_chat(request: AgentRequest):
    """Agent 聊天接口
    
    Args:
        request: Agent 请求数据
        
    Returns:
        AgentResponse: Agent 响应
    """
    try:
        logger.info(f"Agent chat 请求: {request.message[:50]}..., 类型: {request.agent_type}")
        
        # 获取 Agent
        agent = get_agent(agent_type=request.agent_type)
        
        # 准备历史记录
        history = []
        if request.context:
            for i, ctx in enumerate(request.context):
                if i % 2 == 0:
                    history.append({"role": "user", "content": ctx})
                else:
                    history.append({"role": "assistant", "content": ctx})
        
        # 执行 Agent
        start_time = time.time()
        result = await agent.run(
            request.message,
            history=history,
            session_id=request.session_id
        )
        elapsed_ms = (time.time() - start_time) * 1000
        
        logger.info(f"Agent chat 完成，耗时: {elapsed_ms:.2f}ms, 迭代: {result.iterations}")
        
        # 构建响应
        return AgentResponse(
            answer=result.answer,
            tool_calls=result.tool_calls,
            iterations=result.iterations,
            agent_type=result.agent_type,
            session_id=request.session_id,
            intermediate_steps=result.intermediate_steps
        )
        
    except Exception as e:
        logger.error(f"Agent chat 失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def agent_chat_stream(request: AgentRequest):
    """Agent 聊天流式接口
    
    Args:
        request: Agent 请求数据
        
    Returns:
        StreamingResponse: SSE 流式响应
    """
    async def generate():
        try:
            agent = get_agent(agent_type=request.agent_type)
            
            # 发送工具调用开始
            yield f"event: tool_calls\ndata: []\n\n"
            
            # 流式生成
            tool_calls = []
            async for chunk in agent.run_stream(request.message):
                if chunk:
                    # 发送文本块
                    yield f"event: content\ndata: {json.dumps({'content': chunk})}\n\n"
            
            # 发送完成
            yield f"event: done\ndata: {json.dumps({'done': True})}\n\n"
            
        except Exception as e:
            logger.error(f"Agent stream 失败: {str(e)}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/tools", response_model=ToolListResponse)
async def list_tools():
    """获取可用工具列表
    
    Returns:
        ToolListResponse: 工具列表
    """
    registry = get_tool_registry()
    tools = registry.list_all()
    
    tool_schemas = [
        ToolSchema(
            name=tool.name,
            description=tool.description,
            parameters=tool.parameters
        )
        for tool in tools
    ]
    
    return ToolListResponse(tools=tool_schemas, total=len(tool_schemas))


@router.post("/execute", response_model=ToolExecuteResponse)
async def execute_tool(request: ToolExecuteRequest):
    """直接执行指定工具
    
    Args:
        request: 工具执行请求
        
    Returns:
        ToolExecuteResponse: 执行结果
    """
    start_time = time.time()
    
    try:
        registry = get_tool_registry()
        tool = registry.get(request.tool_name)
        
        if not tool:
            raise HTTPException(
                status_code=404,
                detail=f"工具不存在: {request.tool_name}"
            )
        
        result = await tool.execute(**request.parameters)
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        return ToolExecuteResponse(
            tool_name=request.tool_name,
            success=result.success,
            output=result.output,
            error=result.error,
            execution_time_ms=elapsed_ms
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"工具执行失败: {str(e)}")
        elapsed_ms = (time.time() - start_time) * 1000
        return ToolExecuteResponse(
            tool_name=request.tool_name,
            success=False,
            output=None,
            error=str(e),
            execution_time_ms=elapsed_ms
        )


@router.get("/health")
async def agent_health():
    """Agent 健康检查
    
    Returns:
        dict: 健康状态
    """
    registry = get_tool_registry()
    
    return {
        "status": "healthy",
        "tools_count": len(registry),
        "available_tools": [tool.name for tool in registry.list_all()],
        "duckduckgo_available": DDGS_AVAILABLE
    }
