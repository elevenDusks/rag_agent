"""日期时间工具

获取当前日期和时间信息。
"""
from datetime import datetime
from typing import Any, Dict
from ..tools.base import Tool, ToolResult
from ...core.logger import logger


class DateTimeTool(Tool):
    """日期时间工具"""
    
    @property
    def name(self) -> str:
        return "datetime_query"
    
    @property
    def description(self) -> str:
        return (
            "获取当前日期和时间信息。当用户询问当前日期、时间、星期几等时间相关问题时使用。"
        )
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "format": {
                    "type": "string",
                    "description": "日期时间格式，默认为 '%Y年%m月%d日 %H:%M:%S'。常用格式：'%Y-%m-%d'、'%Y/%m/%d'、'%H:%M:%S'",
                    "default": "%Y年%m月%d日 %H:%M:%S"
                }
            },
            "required": []
        }
    
    async def execute(self, format: str = "%Y年%m月%d日 %H:%M:%S", **kwargs) -> ToolResult:
        """获取当前日期时间"""
        try:
            logger.info(f"DateTimeTool 获取日期时间，格式: {format}")
            
            now = datetime.now()
            formatted = now.strftime(format)
            
            # 构建详细信息
            details = {
                "datetime": formatted,
                "date": now.strftime("%Y年%m月%d日"),
                "time": now.strftime("%H:%M:%S"),
                "weekday": ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][now.weekday()],
                "timestamp": now.timestamp()
            }
            
            logger.info(f"DateTimeTool 当前时间: {formatted}")
            return ToolResult(success=True, output=details)
            
        except Exception as e:
            logger.error(f"DateTimeTool 执行失败: {str(e)}")
            return ToolResult(
                success=False,
                output="",
                error=f"获取日期时间失败: {str(e)}"
            )


# 工具实例
_datetime_tool: DateTimeTool | None = None


def get_datetime_tool() -> DateTimeTool:
    """获取日期时间工具实例"""
    global _datetime_tool
    if _datetime_tool is None:
        _datetime_tool = DateTimeTool()
    return _datetime_tool
