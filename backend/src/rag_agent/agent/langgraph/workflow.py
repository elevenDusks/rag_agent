"""LangGraph Agent 工作流定义

构建完整的 ReAct Agent 工作流图。
"""
from langgraph.graph import StateGraph, END
from typing import Literal

from .state import AgentState, create_initial_state
from .nodes import (
    llm_reason_node,
    tool_execution_node,
    should_continue,
    generate_answer_node,
)
from .tools import TOOL_DESCRIPTIONS
from ..prompts.react_prompt import ReActPrompt


def _should_continue_router(state: AgentState) -> Literal["tool_execution", "generate_answer"]:
    """路由函数：根据状态决定下一步
    
    Returns:
        "tool_execution" - 需要执行工具
        "generate_answer" - 生成最终答案
    """
    messages = state.get("messages", [])
    if not messages:
        return "generate_answer"
    
    last_msg = messages[-1]
    
    # 检查是否有工具调用
    if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
        return "tool_execution"
    
    # 检查文本格式
    if hasattr(last_msg, 'content'):
        content = last_msg.content
        # 如果包含 Action 且不包含 Final Answer，继续执行工具
        if "Action:" in content and "Final Answer:" not in content:
            return "tool_execution"
        # 如果包含 Final Answer，直接生成答案
        if "Final Answer:" in content:
            return "generate_answer"
    
    # 默认生成答案
    return "generate_answer"


def build_agent_workflow(
    system_prompt: str = None,
    max_iterations: int = 10
) -> StateGraph:
    """构建 Agent 工作流图
    
    工作流结构：
    
        ┌─────────────────────────────────────────────────────┐
        │                      START                          │
        └─────────────────────────┬───────────────────────────┘
                                  │
                                  ▼
        ┌─────────────────────────────────────────────────────┐
        │                   llm_reason                         │
        │            (调用 LLM 进行推理)                        │
        └─────────────────────────┬───────────────────────────┘
                                  │
                                  ▼
        ┌─────────────────────────────────────────────────────┐
        │                   路由判断                           │
        │         检查是否需要调用工具                          │
        └─────────────────────────┬───────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
                    ▼                           ▼
        ┌───────────────────────┐   ┌─────────────────────────┐
        │    tool_execution     │   │    generate_answer      │
        │    (执行工具)           │   │    (生成最终答案)         │
        └───────────┬───────────┘   └─────────────────────────┘
                    │                           │
                    ▼                           │
        ┌───────────────────────────────────────┤
        │                                       │
        │           是否继续循环？                 │
        │                                       │
        └───────────────────┬───────────────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
                ▼                       ▼
            [继续]                   [结束]
            llm_reason             END
                │
    
    Args:
        system_prompt: 自定义系统提示词
        max_iterations: 最大迭代次数
        
    Returns:
        StateGraph: 构建好的工作流图
    """
    # 构建系统提示词
    if system_prompt is None:
        system_prompt = ReActPrompt.get_system_prompt()
    
    # 创建工作流图
    workflow = StateGraph(AgentState)
    
    # 添加节点
    workflow.add_node("llm_reason", llm_reason_node)
    workflow.add_node("tool_execution", tool_execution_node)
    workflow.add_node("generate_answer", generate_answer_node)
    
    # 设置入口点
    workflow.set_entry_point("llm_reason")
    
    # 添加边
    # llm_reason -> 路由判断
    workflow.add_conditional_edges(
        "llm_reason",
        _should_continue_router,
        {
            "tool_execution": "tool_execution",
            "generate_answer": "generate_answer"
        }
    )
    
    # tool_execution -> 继续判断
    workflow.add_conditional_edges(
        "tool_execution",
        should_continue,
        {
            "continue": "llm_reason",  # 继续下一轮推理
            "end": "generate_answer"    # 结束
        }
    )
    
    # generate_answer -> END
    workflow.add_edge("generate_answer", END)
    
    # 编译工作流
    return workflow.compile()


class LangGraphAgent:
    """基于 LangGraph 的 ReAct Agent
    
    使用 LangGraph 实现的 ReAct Agent，具有更好的状态管理和
    可视化调试能力。
    
    Example:
        agent = LangGraphAgent()
        result = await agent.run("今天几号？")
        print(result.answer)
    """
    
    def __init__(
        self,
        system_prompt: str = None,
        max_iterations: int = 10,
    ):
        """初始化 Agent
        
        Args:
            system_prompt: 自定义系统提示词
            max_iterations: 最大迭代次数
        """
        self.max_iterations = max_iterations
        
        # 构建系统提示词
        if system_prompt is None:
            system_prompt = ReActPrompt.get_system_prompt()
        
        self.system_prompt = system_prompt
        
        # 预编译工作流
        self.workflow = build_agent_workflow(
            system_prompt=self.system_prompt,
            max_iterations=self.max_iterations
        )
    
    async def run(
        self,
        question: str,
        session_id: str = "default",
        history: list = None
    ) -> "AgentRunResult":
        """执行 Agent
        
        Args:
            question: 用户问题
            session_id: 会话 ID
            history: 对话历史
            
        Returns:
            AgentRunResult: 包含答案和执行信息的对象
        """
        from ..agent import AgentResponse
        from ...memroy.memory import ChatMemory
        
        # 获取对话历史作为上下文
        chat_history = history or []
        
        # 构建消息列表
        messages = []
        
        # 添加系统提示词
        from langchain_core.messages import SystemMessage, HumanMessage
        messages.append(SystemMessage(content=self.system_prompt))
        
        # 添加历史对话
        for msg in chat_history:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                from langchain_core.messages import AIMessage
                messages.append(AIMessage(content=content))
        
        # 添加当前问题
        messages.append(HumanMessage(content=question))
        
        # 创建初始状态
        initial_state = AgentState(
            messages=messages,
            session_id=session_id,
            question=question,
            intermediate_steps=[],
            tool_results={},
            final_answer=None,
            retrieved_context=None,
            current_tool=None,
            iteration=0,
            max_iterations=self.max_iterations,
            should_end=False,
            error=None
        )
        
        # 执行工作流
        try:
            final_state = await self.workflow.ainvoke(initial_state)
            
            # 提取结果
            final_answer = final_state.get("final_answer", "抱歉，无法生成回答。")
            intermediate_steps = final_state.get("intermediate_steps", [])
            tool_results = final_state.get("tool_results", {})
            iterations = final_state.get("iteration", 0)
            
            # 构建工具调用记录
            tool_calls = []
            for tool_name, result in tool_results.items():
                tool_calls.append({
                    "tool": tool_name,
                    "output": result,
                    "success": True
                })
            
            return AgentRunResult(
                answer=final_answer,
                tool_calls=tool_calls,
                iterations=iterations,
                intermediate_steps=intermediate_steps,
                session_id=session_id
            )
            
        except Exception as e:
            from ...core.logger import logger
            logger.error(f"LangGraphAgent 执行失败: {str(e)}")
            
            return AgentRunResult(
                answer=f"执行出错: {str(e)}",
                tool_calls=[],
                iterations=0,
                intermediate_steps=[],
                session_id=session_id,
                error=str(e)
            )
    
    async def run_stream(
        self,
        question: str,
        session_id: str = "default",
        history: list = None
    ):
        """流式执行 Agent
        
        Args:
            question: 用户问题
            session_id: 会话 ID
            history: 对话历史
            
        Yields:
            str: 响应的 token 片段
        """
        result = await self.run(question, session_id, history)
        yield result.answer


class AgentRunResult:
    """Agent 执行结果"""
    
    def __init__(
        self,
        answer: str,
        tool_calls: list = None,
        iterations: int = 0,
        intermediate_steps: list = None,
        session_id: str = "default",
        error: str = None
    ):
        self.answer = answer
        self.tool_calls = tool_calls or []
        self.iterations = iterations
        self.intermediate_steps = intermediate_steps or []
        self.session_id = session_id
        self.error = error
    
    def to_agent_response(self) -> "AgentResponse":
        """转换为 AgentResponse 格式"""
        from ..agent import AgentResponse, AgentType
        
        return AgentResponse(
            answer=self.answer,
            tool_calls=self.tool_calls,
            iterations=self.iterations,
            agent_type=AgentType.REACT.value,
            intermediate_steps=self.intermediate_steps
        )


# 导出便捷函数
def create_agent(
    system_prompt: str = None,
    max_iterations: int = 10
) -> LangGraphAgent:
    """创建 LangGraph Agent 实例
    
    Args:
        system_prompt: 自定义系统提示词
        max_iterations: 最大迭代次数
        
    Returns:
        LangGraphAgent 实例
    """
    return LangGraphAgent(
        system_prompt=system_prompt,
        max_iterations=max_iterations
    )
