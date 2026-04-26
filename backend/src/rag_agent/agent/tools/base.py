
"""工具基类定义

所有 Agent 工具必须继承自 Tool 基类，实现 name, description, execute 方法。
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """工具执行结果"""
    success: bool = Field(description="执行是否成功")
    output: Any = Field(description="工具输出内容")
    error: Optional[str] = Field(default=None, description="错误信息（如果失败）")
    
    class Config:
        arbitrary_types_allowed = True


class Tool(ABC):
    """Agent 工具抽象基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称，用于 LLM 识别和调用"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述，用于 LLM 理解工具用途"""
        pass
    
    @property
    def parameters(self) -> Dict[str, Any]:
        """工具参数 Schema（JSON Schema 格式），用于 LLM 理解参数"""
        return {
            "type": "object",
            "properties": {},
            "required": []
        }
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """执行工具逻辑
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            ToolResult: 执行结果
        """
        pass
    
    def get_schema(self) -> Dict[str, Any]:
        """获取完整的工具 Schema，用于 LLM Function Calling"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


class AsyncTool(Tool):
    """异步工具基类（与 Tool 相同，主要用于语义区分）"""
    pass


class ToolCollection:
    """工具集合，用于批量管理多个工具"""
    
    def __init__(self, tools: Optional[List[Tool]] = None):
        self._tools: Dict[str, Tool] = {}
        if tools:
            for tool in tools:
                self.add(tool)
    
    def add(self, tool: Tool) -> None:
        """添加工具"""
        self._tools[tool.name] = tool
    
    def get(self, name: str) -> Optional[Tool]:
        """获取工具"""
        return self._tools.get(name)
    
    def list(self) -> List[Tool]:
        """列出所有工具"""
        return list(self._tools.values())
    
    def get_schemas(self) -> List[Dict[str, Any]]:
        """获取所有工具的 Schema 列表"""
        return [tool.get_schema() for tool in self._tools.values()]
    
    def __len__(self) -> int:
        return len(self._tools)
    
    def __contains__(self, name: str) -> bool:
        return name in self._tools
