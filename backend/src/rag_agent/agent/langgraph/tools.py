"""LangGraph Agent 工具定义

使用 LangChain 的 @tool 装饰器定义工具，与 LangGraph 原生集成。
"""
from langchain_core.tools import tool
from datetime import datetime
from typing import Optional, List, Dict, Any

from ...core.logger import logger


# ============================================================
# 工具 1: 日期时间查询
# ============================================================
@tool
def datetime_query(format: str = "%Y年%m月%d日 %H:%M:%S") -> str:
    """获取当前日期和时间信息。
    
    当用户询问当前日期、时间、星期几等时间相关问题时使用。
    
    Args:
        format: 日期时间格式，默认为 '%Y年%m月%d日 %H:%M:%S'
                常用格式：
                - '%Y年%m月%d日' -> 2026年04月27日
                - '%Y-%m-%d' -> 2026-04-27
                - '%H:%M:%S' -> 14:30:00
                - '%Y年%m月%d日 %H:%M:%S' -> 2026年04月27日 14:30:00
    
    Returns:
        包含日期时间详细信息的字典
    """
    now = datetime.now()
    
    details = {
        "datetime": now.strftime(format),
        "date": now.strftime("%Y年%m月%d日"),
        "time": now.strftime("%H:%M:%S"),
        "weekday": ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][now.weekday()],
        "timestamp": now.timestamp(),
        "iso_format": now.isoformat()
    }
    
    logger.info(f"DateTimeTool 当前时间: {details['datetime']}")
    return f"当前时间：{details['datetime']}，{details['weekday']}"


# ============================================================
# 工具 2: 计算器
# ============================================================
@tool
def calculator(expression: str) -> str:
    """执行数学计算。
    
    当用户需要进行数学运算（加减乘除、百分比、平方等）时使用。
    
    Args:
        expression: 数学表达式，例如 "250 + 380"、"100 * 0.15"、"2**3"
    
    Returns:
        计算结果的字符串描述
    """
    try:
        # 安全评估数学表达式
        allowed_chars = set("0123456789.+-*/%()** ")
        if not all(c in allowed_chars for c in expression):
            return f"错误：表达式包含非法字符"
        
        result = eval(expression)
        logger.info(f"Calculator 计算: {expression} = {result}")
        return f"{expression} = {result}"
    except ZeroDivisionError:
        return "错误：除数不能为零"
    except Exception as e:
        return f"计算错误：{str(e)}"


# ============================================================
# 工具 3: 知识库检索 (RAG)
# ============================================================
@tool
def knowledge_search(query: str) -> str:
    """搜索知识库获取相关信息。
    
    当用户询问关于京东流程、政策、操作步骤等问题时使用。
    返回最相关的知识库内容片段。
    
    Args:
        query: 搜索查询，用于从知识库中检索相关信息
    
    Returns:
        检索到的相关知识内容
    """
    from ...rag.rag_pipeline import RAGPipeline
    
    try:
        logger.info(f"KnowledgeSearchTool 执行检索: {query}")
        
        # 使用全局 RAGPipeline 实例
        pipeline = RAGPipeline()
        
        # 同步调用异步方法
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 如果已经在事件循环中，使用 create_task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, pipeline.retrieve(question=query))
                result = future.result(timeout=30)
        else:
            result = asyncio.run(pipeline.retrieve(question=query))
        
        if not result:
            return "知识库中没有找到相关信息。"
        
        logger.info(f"KnowledgeSearchTool 检索完成，结果长度: {len(result)}")
        return result
        
    except Exception as e:
        logger.error(f"KnowledgeSearchTool 执行失败: {str(e)}")
        return f"知识库检索失败: {str(e)}"


# ============================================================
# 工具 4: 网络搜索
# ============================================================
@tool
def web_search(query: str, max_results: int = 5) -> str:
    """搜索互联网获取最新信息。
    
    当用户询问实时新闻、天气预报、最新数据、或需要超出知识库范围的通用知识时使用。
    
    Args:
        query: 搜索关键词
        max_results: 最大返回结果数，默认为 5
    
    Returns:
        搜索结果列表
    """
    try:
        logger.info(f"WebSearchTool 搜索: {query}")
        
        from ddgs import DDGS
        
        results = []
        with DDGS() as ddgs:
            for i, result in enumerate(ddgs.text(query, max_results=max_results)):
                results.append({
                    "序号": i + 1,
                    "标题": result.get("title", ""),
                    "链接": result.get("href", ""),
                    "摘要": result.get("body", "")[:200]
                })
        
        if not results:
            return "没有找到相关结果。"
        
        # 格式化输出
        output = "搜索结果：\n"
        for r in results:
            output += f"\n{r['序号']}. {r['标题']}\n"
            output += f"   {r['摘要']}\n"
            output += f"   链接: {r['链接']}\n"
        
        logger.info(f"WebSearchTool 找到 {len(results)} 条结果")
        return output
        
    except ImportError:
        return "网络搜索功能未启用，请安装 ddgs: pip install ddgs"
    except Exception as e:
        logger.error(f"WebSearchTool 搜索失败: {str(e)}")
        return f"搜索失败: {str(e)}"


# ============================================================
# 工具注册表
# ============================================================
def get_all_tools() -> List:
    """获取所有可用工具
    
    Returns:
        工具列表
    """
    return [
        datetime_query,
        calculator,
        knowledge_search,
        web_search,
    ]


def get_tool_by_name(name: str):
    """根据名称获取工具
    
    Args:
        name: 工具名称
        
    Returns:
        工具实例或 None
    """
    tools = {tool.name: tool for tool in get_all_tools()}
    return tools.get(name)


# ============================================================
# 工具描述（用于提示词）
# ============================================================
TOOL_DESCRIPTIONS = """
## 可用工具

### 1. datetime_query
获取当前日期和时间信息。
- 参数:
  - format (string): 日期时间格式，默认为 '%Y年%m月%d日 %H:%M:%S'

### 2. calculator
执行数学计算。
- 参数:
  - expression (string): 数学表达式，例如 "250 + 380"

### 3. knowledge_search
搜索知识库获取相关信息。
- 参数:
  - query (string): 搜索查询

### 4. web_search
搜索互联网获取最新信息。
- 参数:
  - query (string): 搜索关键词
  - max_results (integer, optional): 最大返回结果数，默认为 5
"""
