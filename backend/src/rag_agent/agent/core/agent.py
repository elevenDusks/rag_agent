"""Agent 核心抽象

定义 Agent 基类和通用接口。
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, AsyncGenerator
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
from enum import Enum

from ..tools.base import Tool, ToolResult
from ...core.logger import logger


class AgentType(str, Enum):
    """Agent 类型枚举"""
    REACT = "react"
    PLAN_EXECUTE = "plan_execute"
    CONVERSATIONAL = "conversational"


@dataclass
class ToolCall:
    """工具调用记录"""
    tool_name: str
    tool_input: Dict[str, Any]
    tool_output: Any
    success: bool = True
    error: Optional[str] = None


@dataclass
class AgentConfig:
    """Agent 配置"""
    agent_type: AgentType = AgentType.REACT
    max_iterations: int = 10
    max_tokens: int = 2000
    temperature: float = 0.7
    tools: List[Tool] = field(default_factory=list)
    system_prompt: Optional[str] = None
    verbose: bool = False


class AgentResponse(BaseModel):
    """Agent 响应"""
    answer: str = Field(description="最终回答")
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list, description="工具调用记录")
    iterations: int = Field(description="执行的迭代次数")
    agent_type: str = Field(description="Agent 类型")
    intermediate_steps: List[str] = Field(default_factory=list, description="中间推理步骤")


class BaseAgent(ABC):
    """Agent 抽象基类"""
    
    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self._tools_map: Dict[str, Tool] = {t.name: t for t in self.config.tools}
        self._tool_calls: List[ToolCall] = []
        logger.info(f"初始化 {self.__class__.__name__}，工具数量: {len(self._tools_map)}")
    
    @property
    def tools(self) -> List[Tool]:
        """获取工具列表"""
        return self.config.tools
    
    @property
    def tool_names(self) -> List[str]:
        """获取工具名称列表"""
        return list(self._tools_map.keys())
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """获取指定工具"""
        return self._tools_map.get(name)
    
    async def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """执行指定工具"""
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                output="",
                error=f"工具不存在: {tool_name}"
            )
        
        try:
            logger.info(f"执行工具: {tool_name}, 参数: {kwargs}")
            result = await tool.execute(**kwargs)
            
            self._tool_calls.append(ToolCall(
                tool_name=tool_name,
                tool_input=kwargs,
                tool_output=result.output,
                success=result.success,
                error=result.error
            ))
            
            if not result.success:
                logger.warning(f"工具 {tool_name} 执行失败: {result.error}")
            
            return result
            
        except Exception as e:
            logger.error(f"工具 {tool_name} 执行异常: {str(e)}")
            error_result = ToolResult(success=False, output="", error=str(e))
            
            self._tool_calls.append(ToolCall(
                tool_name=tool_name,
                tool_input=kwargs,
                tool_output="",
                success=False,
                error=str(e)
            ))
            
            return error_result
    
    def clear_tool_calls(self) -> None:
        """清除工具调用记录"""
        self._tool_calls.clear()
    
    def get_tool_call_records(self) -> List[Dict[str, Any]]:
        """获取工具调用记录"""
        return [
            {
                "tool": tc.tool_name,
                "input": tc.tool_input,
                "output": tc.tool_output,
                "success": tc.success,
                "error": tc.error
            }
            for tc in self._tool_calls
        ]
    
    @abstractmethod
    async def run(self, user_input: str, **kwargs) -> AgentResponse:
        """执行 Agent 逻辑
        
        Args:
            user_input: 用户输入
            **kwargs: 其他参数（如 history, session_id 等）
            
        Returns:
            AgentResponse: Agent 响应
        """
        pass
    
    @abstractmethod
    async def run_stream(self, user_input: str, **kwargs) -> AsyncGenerator[str, None]:
        """流式执行 Agent
        
        Args:
            user_input: 用户输入
            **kwargs: 其他参数
            
        Yields:
            str: 响应片段
        """
        yield ""
