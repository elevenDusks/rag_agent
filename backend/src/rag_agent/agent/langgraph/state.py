"""LangGraph Agent State 定义

定义 Agent 的状态结构，用于在 LangGraph 工作流中传递和管理数据。
"""
from typing import Annotated, Sequence, TypedDict, Optional, List, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import add_messages


class AgentState(TypedDict, total=False):
    """LangGraph Agent 状态定义
    
    这个状态在整个工作流中传递，包含所有需要的信息。
    """
    # 对话消息历史（带类型注解，支持 add_messages 约简）
    messages: Annotated[Sequence[BaseMessage], add_messages]
    
    # 当前会话 ID
    session_id: str
    
    # 用户输入（原始问题）
    question: str
    
    # 中间推理步骤
    intermediate_steps: List[str]
    
    # 工具调用结果 {"tool_name": result}
    tool_results: Dict[str, Any]
    
    # 最终答案（工作流结束时填充）
    final_answer: Optional[str]
    
    # 检索到的上下文（用于 RAG）
    retrieved_context: Optional[str]
    
    # 当前执行的工具名称
    current_tool: Optional[str]
    
    # 迭代计数
    iteration: int
    
    # 最大迭代次数
    max_iterations: int
    
    # 是否应该结束
    should_end: bool
    
    # 错误信息
    error: Optional[str]


def create_initial_state(
    question: str,
    session_id: str,
    max_iterations: int = 10,
    system_prompt: Optional[str] = None
) -> AgentState:
    """创建初始状态
    
    Args:
        question: 用户问题
        session_id: 会话 ID
        max_iterations: 最大迭代次数
        system_prompt: 系统提示词
        
    Returns:
        AgentState: 初始状态
    """
    messages: List[BaseMessage] = []
    
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    
    messages.append(HumanMessage(content=question))
    
    return AgentState(
        messages=messages,
        session_id=session_id,
        question=question,
        intermediate_steps=[],
        tool_results={},
        final_answer=None,
        retrieved_context=None,
        current_tool=None,
        iteration=0,
        max_iterations=max_iterations,
        should_end=False,
        error=None
    )
