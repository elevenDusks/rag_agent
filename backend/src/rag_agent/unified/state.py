"""LangGraph 统一 State 定义

为 LangGraph 工作流定义统一的状态结构。
"""
from typing import Annotated, Sequence, TypedDict, Optional, List, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.graph import add_messages

from .memory import LangChainMemoryManager


# ============================================================
# 核心状态定义
# ============================================================
class UnifiedState(TypedDict, total=False):
    """统一状态定义

    所有 LangGraph 工作流共享的状态结构。
    """

    # ==================== 对话相关 ====================
    # 对话消息历史（带类型注解，支持 add_messages 约简）
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # 用户输入
    input: str

    # 最终答案
    answer: Optional[str]

    # ==================== 会话相关 ====================
    # 会话 ID
    session_id: str

    # 对话历史（简化格式，用于提示词）
    history: List[Dict[str, str]]

    # ==================== 检索相关 ====================
    # 检索到的文档
    retrieved_docs: List[Any]

    # 重排序后的文档
    reranked_docs: List[Any]

    # 检索到的上下文
    context: Optional[str]

    # ==================== 工具相关 ====================
    # 工具调用结果
    tool_results: Dict[str, Any]

    # 当前执行的工具
    current_tool: Optional[str]

    # ==================== 推理相关 ====================
    # 中间推理步骤
    intermediate_steps: List[str]

    # 迭代计数
    iteration: int

    # 最大迭代次数
    max_iterations: int

    # ==================== 状态控制 ====================
    # 是否应该结束
    should_end: bool

    # 错误信息
    error: Optional[str]

    # 路由决策
    route: Optional[str]


# ============================================================
# Agent 专用状态（扩展 UnifiedState）
# ============================================================
class AgentState(UnifiedState):
    """Agent 专用状态"""

    # Agent 类型
    agent_type: str

    # 是否使用 RAG
    use_rag: bool

    # 是否使用工具
    use_tools: bool

    # 可用工具列表
    available_tools: List[str]


# ============================================================
# RAG 专用状态
# ============================================================
class RAGState(TypedDict, total=False):
    """RAG 专用状态"""

    # 问题
    question: str

    # 检索结果
    documents: List[Any]

    # 重排序结果
    ranked_documents: List[Any]

    # 最终上下文
    context: str

    # LLM 响应
    response: str

    # 会话 ID
    session_id: str


# ============================================================
# 状态创建辅助函数
# ============================================================
def create_agent_state(
    input: str,
    session_id: str,
    max_iterations: int = 10,
    system_prompt: str = None,
    use_tools: bool = True,
    use_rag: bool = True,
) -> Dict[str, Any]:
    """创建 Agent 初始状态

    Args:
        input: 用户输入
        session_id: 会话 ID
        max_iterations: 最大迭代次数
        system_prompt: 系统提示词
        use_tools: 是否使用工具
        use_rag: 是否使用 RAG

    Returns:
        AgentState 初始状态
    """
    messages: List[BaseMessage] = []

    # 添加系统提示词
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))

    # 添加用户输入
    messages.append(HumanMessage(content=input))

    return AgentState(
        # 对话相关
        messages=messages,
        input=input,
        answer=None,

        # 会话相关
        session_id=session_id,
        history=[],

        # 检索相关
        retrieved_docs=[],
        reranked_docs=[],
        context=None,

        # 工具相关
        tool_results={},
        current_tool=None,

        # 推理相关
        intermediate_steps=[],
        iteration=0,
        max_iterations=max_iterations,

        # 状态控制
        should_end=False,
        error=None,
        route=None,

        # Agent 专用
        agent_type="react",
        use_rag=use_rag,
        use_tools=use_tools,
        available_tools=["knowledge_search", "web_search", "datetime_query", "calculator"],
    )


def create_rag_state(
    question: str,
    session_id: str,
) -> Dict[str, Any]:
    """创建 RAG 初始状态

    Args:
        question: 用户问题
        session_id: 会话 ID

    Returns:
        RAGState 初始状态
    """
    return RAGState(
        question=question,
        session_id=session_id,
        documents=[],
        ranked_documents=[],
        context="",
        response="",
    )


# ============================================================
# 状态约简函数
# ============================================================
def reduce_messages(left: Sequence[BaseMessage], right: Sequence[BaseMessage]) -> Sequence[BaseMessage]:
    """合并消息列表

    用于 add_messages 约简。
    """
    return list(left) + list(right)


def reduce_dict(left: Dict, right: Dict) -> Dict:
    """合并字典

    用于工具结果等字段的约简。
    """
    result = dict(left)
    result.update(right)
    return result
