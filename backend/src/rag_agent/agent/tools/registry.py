"""工具注册表

管理所有可用工具，提供工具查找、列表和 Schema 生成功能。
"""
from typing import Dict, List, Optional, Any
from .base import Tool, ToolResult, ToolCollection
from ...core.logger import logger


class ToolRegistry:
    """全局工具注册表（单例模式）"""
    
    _instance: Optional['ToolRegistry'] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if ToolRegistry._initialized:
            return
        ToolRegistry._initialized = True
        self._tools: Dict[str, Tool] = {}
        self._collections: Dict[str, ToolCollection] = {}
        logger.info("初始化 ToolRegistry")
    
    def register(self, tool: Tool, collection: Optional[str] = None) -> None:
        """注册工具
        
        Args:
            tool: 工具实例
            collection: 可选的集合名称，用于分组管理
        """
        if tool.name in self._tools:
            logger.warning(f"工具 {tool.name} 已存在，将被覆盖")
        self._tools[tool.name] = tool
        logger.info(f"注册工具: {tool.name}")
        
        if collection:
            if collection not in self._collections:
                self._collections[collection] = ToolCollection()
            self._collections[collection].add(tool)
    
    def register_collection(self, tools: List[Tool], collection: str) -> None:
        """批量注册工具到指定集合
        
        Args:
            tools: 工具列表
            collection: 集合名称
        """
        for tool in tools:
            self.register(tool, collection)
    
    def get(self, name: str) -> Optional[Tool]:
        """获取工具实例"""
        return self._tools.get(name)
    
    def list_all(self) -> List[Tool]:
        """列出所有已注册的工具"""
        return list(self._tools.values())
    
    def list_by_collection(self, collection: str) -> List[Tool]:
        """按集合列出工具"""
        if collection in self._collections:
            return self._collections[collection].list()
        return []
    
    def get_schemas(self, collection: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取工具 Schema 列表，用于 LLM Function Calling
        
        Args:
            collection: 可选的工具集合名称
            
        Returns:
            工具 Schema 列表
        """
        if collection and collection in self._collections:
            return self._collections[collection].get_schemas()
        return [tool.get_schema() for tool in self._tools.values()]
    
    def get_system_message(self, collection: Optional[str] = None) -> str:
        """生成系统提示词中的工具描述部分
        
        Args:
            collection: 可选的工具集合名称
            
        Returns:
            格式化的工具描述文本
        """
        tools = self.list_by_collection(collection) if collection else self.list_all()
        
        if not tools:
            return "无可用工具。"
        
        descriptions = []
        for tool in tools:
            params = tool.parameters
            param_str = ""
            if params.get("properties"):
                param_lines = []
                for param_name, param_info in params["properties"].items():
                    required = param_name in params.get("required", [])
                    param_lines.append(
                        f"  - {param_name}: {param_info.get('description', '无描述')} "
                        f"({'必填' if required else '可选'})"
                    )
                if param_lines:
                    param_str = "\n" + "\n".join(param_lines)
            
            descriptions.append(
                f"## {tool.name}\n"
                f"{tool.description}{param_str}"
            )
        
        return "\n\n".join(descriptions)
    
    def __len__(self) -> int:
        return len(self._tools)
    
    def __contains__(self, name: str) -> bool:
        return name in self._tools


# 全局注册表实例
registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """获取全局工具注册表"""
    return registry
