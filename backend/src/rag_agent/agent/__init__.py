"""Agent 模块

提供 Agent 核心功能，包括：
- ReAct Agent：基于 ReAct 范式的推理 Agent
- LangGraph Agent：基于 LangGraph 的 ReAct Agent（推荐）
"""
from .core.agent import BaseAgent, AgentResponse, AgentConfig, AgentType, ToolCall
from .core.react_agent import ReActAgent

# LangGraph Agent
from .langgraph import LangGraphAgent, AgentState, build_agent_workflow

__all__ = [
    # 核心
    "BaseAgent",
    "AgentResponse",
    "AgentConfig",
    "AgentType",
    "ToolCall",
    # ReAct Agent
    "ReActAgent",
    # LangGraph Agent
    "LangGraphAgent",
    "AgentState",
    "build_agent_workflow",
]
