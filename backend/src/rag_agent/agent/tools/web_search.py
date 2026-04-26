"""网络搜索工具

使用 DuckDuckGo 进行网络搜索。
"""
from typing import Any, Dict
from ..tools.base import Tool, ToolResult
from ...core.logger import logger

try:
    from ddgs import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    try:
        from duckduckgo_search import DDGS
        DDGS_AVAILABLE = True
    except ImportError:
        DDGS_AVAILABLE = False
        logger.warning("ddgs 或 duckduckgo-search 未安装，网络搜索功能不可用。请运行: pip install ddgs")


class WebSearchTool(Tool):
    """网络搜索工具（使用 DuckDuckGo）"""
    
    def __init__(self, max_results: int = 5):
        self._max_results = max_results
    
    @property
    def name(self) -> str:
        return "web_search"
    
    @property
    def description(self) -> str:
        return (
            "搜索互联网获取最新信息。当用户询问实时新闻、天气预报、最新数据、"
            "或需要超出知识库范围的通用知识时使用。"
        )
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词"
                },
                "max_results": {
                    "type": "integer",
                    "description": "最大返回结果数，默认为 5",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    
    async def execute(self, query: str, max_results: int | None = None, **kwargs) -> ToolResult:
        """执行网络搜索"""
        if not DDGS_AVAILABLE:
            return ToolResult(
                success=False,
                output="",
                error="网络搜索功能未启用，请安装 ddgs: pip install ddgs"
            )
        
        try:
            logger.info(f"WebSearchTool 搜索: {query}")
            
            results = []
            limit = max_results or self._max_results
            
            with DDGS() as ddgs:
                for result in ddgs.text(query, max_results=limit):
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("href", ""),
                        "snippet": result.get("body", "")[:200]
                    })
            
            logger.info(f"WebSearchTool 找到 {len(results)} 条结果")
            return ToolResult(success=True, output=results)
            
        except Exception as e:
            logger.error(f"WebSearchTool 搜索失败: {str(e)}")
            return ToolResult(
                success=False,
                output=[],
                error=f"搜索失败: {str(e)}"
            )


# 工具实例
_web_search_tool: WebSearchTool | None = None


def get_web_search_tool(max_results: int = 5) -> WebSearchTool:
    """获取网络搜索工具实例"""
    global _web_search_tool
    if _web_search_tool is None:
        _web_search_tool = WebSearchTool(max_results)
    return _web_search_tool
