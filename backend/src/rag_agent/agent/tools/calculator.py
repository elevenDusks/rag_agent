"""计算器工具

提供数学计算功能。
"""
import math
import re
from typing import Any, Dict, Union
from ..tools.base import Tool, ToolResult
from ...core.logger import logger


class CalculatorTool(Tool):
    """计算器工具，支持基本数学运算"""
    
    @property
    def name(self) -> str:
        return "calculator"
    
    @property
    def description(self) -> str:
        return (
            "进行数学计算。当用户需要计算数字、百分比、统计数据时使用。 "
            "支持加(+)、减(-)、乘(*)、除(/)、幂(**)、开方(sqrt)等运算。"
        )
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "数学表达式，如 '2 + 3'、'100 * 0.15'、'sqrt(16)'、'10 ** 2'"
                }
            },
            "required": ["expression"]
        }
    
    async def execute(self, expression: str, **kwargs) -> ToolResult:
        """执行数学计算"""
        try:
            logger.info(f"CalculatorTool 计算表达式: {expression}")
            
            # 安全评估数学表达式
            result = self._safe_eval(expression)
            
            logger.info(f"CalculatorTool 计算结果: {result}")
            return ToolResult(success=True, output=str(result))
            
        except Exception as e:
            logger.error(f"CalculatorTool 计算失败: {str(e)}")
            return ToolResult(
                success=False,
                output="",
                error=f"计算失败: {str(e)}"
            )
    
    def _safe_eval(self, expression: str) -> Union[int, float]:
        """安全评估数学表达式"""
        # 清理表达式
        expression = expression.strip()
        
        # 定义安全函数
        safe_dict = {
            "sqrt": math.sqrt,
            "abs": abs,
            "round": round,
            "pow": pow,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "log": math.log,
            "log10": math.log10,
            "pi": math.pi,
            "e": math.e,
        }
        
        # 移除危险字符
        safe_expr = re.sub(r'[^0-9+\-*/.() sqrtabicdefghjklmnopqrstuvwxyz_]', '', expression, flags=re.IGNORECASE)
        
        # 使用 eval 计算
        result = eval(safe_expr, {"__builtins__": {}}, safe_dict)
        
        # 如果结果是浮点数，保留合理精度
        if isinstance(result, float):
            if result == int(result):
                return int(result)
            result = round(result, 10)
        
        return result


# 工具实例
_calculator_tool: CalculatorTool | None = None


def get_calculator_tool() -> CalculatorTool:
    """获取计算器工具实例"""
    global _calculator_tool
    if _calculator_tool is None:
        _calculator_tool = CalculatorTool()
    return _calculator_tool
