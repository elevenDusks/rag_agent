"""文件读取工具

读取本地文件内容。
"""
from pathlib import Path
from typing import Any, Dict
from ..tools.base import Tool, ToolResult
from ...core.logger import logger


class FileReaderTool(Tool):
    """文件读取工具"""
    
    def __init__(self, allowed_dirs: list[str] | None = None):
        """
        Args:
            allowed_dirs: 允许访问的目录列表，None 表示允许所有目录（不推荐）
        """
        self._allowed_dirs = [Path(d).resolve() for d in (allowed_dirs or [])]
    
    @property
    def name(self) -> str:
        return "file_reader"
    
    @property
    def description(self) -> str:
        return (
            "读取本地文件内容。当用户需要查看代码、文档、配置文件等内容时使用。"
        )
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "要读取的文件路径"
                },
                "max_lines": {
                    "type": "integer",
                    "description": "最多读取的行数，默认为 100",
                    "default": 100
                }
            },
            "required": ["file_path"]
        }
    
    async def execute(self, file_path: str, max_lines: int = 100, **kwargs) -> ToolResult:
        """读取文件内容"""
        try:
            logger.info(f"FileReaderTool 读取文件: {file_path}")
            
            path = Path(file_path).resolve()
            
            # 安全检查
            if not self._is_safe_path(path):
                logger.warning(f"FileReaderTool 访问受限: {file_path}")
                return ToolResult(
                    success=False,
                    output="",
                    error="文件路径不在允许范围内"
                )
            
            # 检查文件是否存在
            if not path.exists():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"文件不存在: {file_path}"
                )
            
            # 检查是否为文件
            if not path.is_file():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"路径不是文件: {file_path}"
                )
            
            # 读取文件
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()[:max_lines]
                content = ''.join(lines)
            
            has_more = len(f.readlines()) > max_lines if False else False  # 简化
            
            result = {
                "path": str(path),
                "content": content,
                "truncated": len(content.split('\n')) >= max_lines,
                "max_lines": max_lines
            }
            
            logger.info(f"FileReaderTool 读取成功: {len(content)} 字符")
            return ToolResult(success=True, output=result)
            
        except UnicodeDecodeError:
            return ToolResult(
                success=False,
                output="",
                error="文件编码不支持，请确保文件为 UTF-8 编码"
            )
        except Exception as e:
            logger.error(f"FileReaderTool 读取失败: {str(e)}")
            return ToolResult(
                success=False,
                output="",
                error=f"读取文件失败: {str(e)}"
            )
    
    def _is_safe_path(self, path: Path) -> bool:
        """检查路径是否安全"""
        if not self._allowed_dirs:
            return True  # 无限制
        
        for allowed_dir in self._allowed_dirs:
            try:
                path.relative_to(allowed_dir)
                return True
            except ValueError:
                continue
        return False


# 工具实例
_file_reader_tool: FileReaderTool | None = None


def get_file_reader_tool(allowed_dirs: list[str] | None = None) -> FileReaderTool:
    """获取文件读取工具实例"""
    global _file_reader_tool
    if _file_reader_tool is None:
        _file_reader_tool = FileReaderTool(allowed_dirs)
    return _file_reader_tool
