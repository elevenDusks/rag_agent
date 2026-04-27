"""LangGraph 节点定义

定义 Agent 工作流中的各个节点：
- route_node: 路由节点，决定下一步行动
- rag_retrieve_node: RAG 检索节点
- web_search_node: 网络搜索节点
- datetime_node: 日期时间查询节点
- calculator_node: 计算器节点
- generate_answer_node: 生成答案节点
"""
from typing import Literal

from .state import AgentState
from .tools import (
    datetime_query,
    calculator,
    knowledge_search,
    web_search,
)
from ..prompts.react_prompt import ReActPrompt
from ...models.model_registry import llm
from ...core.logger import logger


# ============================================================
# 节点 1: LLM 推理节点（路由决策）
# ============================================================
def llm_reason_node(state: AgentState) -> AgentState:
    """LLM 推理节点
    
    调用 LLM 进行推理，决定是否需要调用工具以及调用哪个工具。
    如果不需要工具，直接生成最终答案。
    
    Returns:
        更新后的状态
    """
    messages = state["messages"]
    iteration = state.get("iteration", 0) + 1
    
    logger.info(f"LLM 推理节点执行，第 {iteration} 轮")
    
    # 调用 LLM
    response = llm.invoke(messages)
    
    # 将 LLM 响应添加到消息历史
    new_messages = list(messages) + [response]
    
    # 提取响应内容
    response_content = response.content if hasattr(response, 'content') else str(response)
    
    # 更新状态
    return {
        "messages": new_messages,
        "iteration": iteration,
    }


# ============================================================
# 节点 2: 工具执行节点
# ============================================================
def tool_execution_node(state: AgentState) -> AgentState:
    """工具执行节点
    
    解析 LLM 的响应，执行相应的工具。
    支持的工具：
    - datetime_query: 日期时间查询
    - calculator: 计算器
    - knowledge_search: 知识库检索
    - web_search: 网络搜索
    """
    messages = state["messages"]
    tool_results = dict(state.get("tool_results", {}))
    intermediate_steps = list(state.get("intermediate_steps", []))
    
    # 获取最后一条 AI 消息
    last_message = messages[-1] if messages else None
    
    if not last_message or not hasattr(last_message, 'content'):
        return {
            "tool_results": tool_results,
            "intermediate_steps": intermediate_steps,
            "should_end": True,
            "error": "无法获取 LLM 响应"
        }
    
    response_text = last_message.content
    
    # 解析工具调用
    tool_name, tool_args = _parse_tool_call(response_text)
    
    if not tool_name:
        # 没有工具调用，检查是否有最终答案
        final_answer = _extract_final_answer(response_text)
        if final_answer:
            return {
                "final_answer": final_answer,
                "should_end": True,
            }
        else:
            # 无法解析，返回原始响应作为答案
            return {
                "final_answer": response_text,
                "should_end": True,
            }
    
    # 记录推理步骤
    thought = _extract_thought(response_text)
    if thought:
        intermediate_steps.append(f"Thought: {thought}")
    intermediate_steps.append(f"Action: {tool_name}({tool_args})")
    
    # 执行工具
    logger.info(f"执行工具: {tool_name}, 参数: {tool_args}")
    
    tool_result = _execute_tool_by_name(tool_name, tool_args)
    
    # 记录工具结果
    tool_results[tool_name] = tool_result
    
    # 将工具结果作为 Observation 添加到消息
    observation_msg = f"Observation: {tool_result}"
    intermediate_steps.append(f"Observation: {tool_result[:200]}")
    
    new_messages = list(messages) + [
        {"type": "tool", "content": observation_msg}
    ]
    
    return {
        "messages": new_messages,
        "tool_results": tool_results,
        "intermediate_steps": intermediate_steps,
        "current_tool": tool_name,
        "should_end": False,
    }


# ============================================================
# 节点 3: 检查是否结束
# ============================================================
def should_continue(state: AgentState) -> Literal["continue", "end"]:
    """判断是否继续执行
    
    检查状态，决定是继续循环还是结束。
    
    Returns:
        "continue" 继续执行
        "end" 结束执行
    """
    # 检查是否已达到最大迭代次数
    if state.get("iteration", 0) >= state.get("max_iterations", 10):
        logger.warning(f"达到最大迭代次数: {state.get('max_iterations')}")
        return "end"
    
    # 检查是否已有最终答案
    if state.get("final_answer"):
        return "end"
    
    # 检查是否有错误
    if state.get("error"):
        return "end"
    
    # 检查最后一条消息是否包含 ToolCall
    messages = state.get("messages", [])
    if messages:
        last_msg = messages[-1]
        # 检查是否有 tool_calls（Function Calling 格式）
        if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
            return "continue"
        
        # 检查文本格式中是否包含 Action
        if hasattr(last_msg, 'content'):
            content = last_msg.content
            if "Action:" in content or "Final Answer:" in content:
                # 如果有 Final Answer，提取并结束
                final = _extract_final_answer(content)
                if final:
                    return "end"
                return "continue"
    
    # 默认继续
    return "continue"


# ============================================================
# 节点 4: 生成最终答案
# ============================================================
def generate_answer_node(state: AgentState) -> AgentState:
    """生成最终答案节点
    
    当推理循环结束后，生成最终答案返回给用户。
    """
    messages = state["messages"]
    intermediate_steps = state.get("intermediate_steps", [])
    final_answer = state.get("final_answer")
    
    # 如果已经有最终答案，直接返回
    if final_answer:
        return {"final_answer": final_answer}
    
    # 从消息历史中提取最终答案
    for msg in reversed(messages):
        if hasattr(msg, 'content'):
            content = msg.content
            answer = _extract_final_answer(content)
            if answer:
                return {"final_answer": answer}
    
    # 如果没有找到最终答案，返回最后一条消息
    if messages:
        last_msg = messages[-1]
        content = last_msg.content if hasattr(last_msg, 'content') else str(last_msg)
        return {"final_answer": content}
    
    return {"final_answer": "抱歉，无法生成回答。"}


# ============================================================
# 辅助函数
# ============================================================
def _parse_tool_call(text: str) -> tuple[str | None, dict]:
    """解析工具调用
    
    从 LLM 响应中提取工具名称和参数。
    
    Args:
        text: LLM 响应文本
        
    Returns:
        (tool_name, tool_args) 元组
    """
    import re
    import json
    
    # 匹配格式: Action: tool_name({"param": "value"}) 或 Action: tool_name()
    patterns = [
        r'Action:\s*(\w+)\s*\(\s*(\{[^}]*\})\s*\)',  # Action: name({"k": "v"})
        r'Action:\s*(\w+)\s*\(\s*\)',  # Action: name()
        r'Action:\s*(\w+)\s*\(\s*([^)]+)\s*\)',  # Action: name(value)
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            tool_name = match.group(1)
            args = {}
            
            if len(match.groups()) > 1:
                args_str = match.group(2).strip()
                if args_str:
                    try:
                        if args_str.startswith('{'):
                            args = json.loads(args_str)
                        elif '=' in args_str:
                            parts = args_str.split('=')
                            if len(parts) == 2:
                                key = parts[0].strip()
                                value = parts[1].strip().strip('"\'')
                                args[key] = value
                    except (json.JSONDecodeError, ValueError):
                        args = {}
            
            return tool_name, args
    
    return None, {}


def _extract_thought(text: str) -> str:
    """提取 Thought"""
    import re
    match = re.search(r'Thought:\s*(.+?)(?=\n(?:Action|Final)|$)', text, re.DOTALL)
    return match.group(1).strip() if match else ""


def _extract_final_answer(text: str) -> str | None:
    """提取 Final Answer"""
    import re
    match = re.search(r'Final Answer:\s*(.+?)$', text, re.DOTALL)
    return match.group(1).strip() if match else None


def _execute_tool_by_name(tool_name: str, args: dict) -> str:
    """根据名称执行工具
    
    Args:
        tool_name: 工具名称
        args: 工具参数
        
    Returns:
        工具执行结果
    """
    tool_map = {
        "datetime_query": datetime_query,
        "calculator": calculator,
        "knowledge_search": knowledge_search,
        "web_search": web_search,
    }
    
    tool = tool_map.get(tool_name)
    if not tool:
        return f"错误：未知工具 {tool_name}"
    
    try:
        result = tool.invoke(args)
        return str(result) if result else "工具执行完成，无返回内容"
    except Exception as e:
        logger.error(f"工具 {tool_name} 执行失败: {str(e)}")
        return f"工具执行失败: {str(e)}"
