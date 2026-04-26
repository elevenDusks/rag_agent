"""知识库检索工具

提供对知识库的 RAG 检索功能。
"""
from typing import Any, Dict
from ..tools.base import Tool, ToolResult
from ...rag.rag_pipeline import RAGPipeline
from ...core.logger import logger


class KnowledgeSearchTool(Tool):
    """知识库检索工具"""
    
    def __init__(self):
        self._pipeline = RAGPipeline()
    
    @property
    def name(self) -> str:
        return "knowledge_search"
    
    @property
    def description(self) -> str:
        return (
            "搜索知识库获取相关信息。当用户询问关于京东流程、政策、操作步骤等问题时使用。 "
            "返回最相关的知识库内容片段。"
        )
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询，用于从知识库中检索相关信息"
                }
            },
            "required": ["query"]
        }
    
    async def execute(self, query: str, **kwargs) -> ToolResult:
        """执行知识库检索"""
        try:
            logger.info(f"KnowledgeSearchTool 执行检索: {query}")
            
            # 调用 RAG Pipeline
            result = await self._pipeline.retrieve(question=query)
            
            logger.info(f"KnowledgeSearchTool 检索完成，结果长度: {len(result)}")
            return ToolResult(success=True, output=result)
            
        except NotImplementedError:
            return ToolResult(
                success=True,
                output="当前查询类型暂不支持知识库检索。"
            )
        except Exception as e:
            logger.error(f"KnowledgeSearchTool 执行失败: {str(e)}")
            return ToolResult(
                success=False,
                output="",
                error=f"知识库检索失败: {str(e)}"
            )
    
    async def execute_stream(self, query: str, **kwargs):
        """流式执行知识库检索"""
        try:
            async for chunk in self._pipeline.retrieve_stream(question=query):
                yield chunk
        except Exception as e:
            logger.error(f"KnowledgeSearchTool 流式执行失败: {str(e)}")
            yield f"知识库检索失败: {str(e)}"


# 工具实例（延迟初始化）
_knowledge_search_tool: KnowledgeSearchTool | None = None


def get_knowledge_search_tool() -> KnowledgeSearchTool:
    """获取知识库检索工具实例"""
    global _knowledge_search_tool
    if _knowledge_search_tool is None:
        _knowledge_search_tool = KnowledgeSearchTool()
    return _knowledge_search_tool
