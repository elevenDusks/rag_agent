"""LangGraph 统一 Agent

整合 Memory、RAG Chain、Tools 的统一 Agent 实现。
基于 LangGraph 实现，具有：
- 可视化的状态流转
- 灵活的节点扩展
- 内置的记忆管理
- 统一的工具调用
"""
from typing import List, Dict, Optional, Any, AsyncGenerator, Literal, Callable
from dataclasses import dataclass, field
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

from ..core.logger import logger
from ..models.model_registry import llm
from .state import UnifiedState, AgentState, create_agent_state
from .memory import LangChainMemoryManager
from .rag_chain import RAGChainBuilder
from ..agent.langgraph.tools import (
    get_all_tools,
    get_tool_by_name,
    TOOL_DESCRIPTIONS,
)


# ============================================================
# Agent 配置
# ============================================================
@dataclass
class AgentConfig:
    """Agent 配置"""

    # 系统提示词
    system_prompt: str = """你是一个智能助手，可以帮助用户回答问题。

## 可用能力
1. 知识库检索：当用户询问关于京东流程、政策、操作步骤等问题时
2. 网络搜索：获取最新信息
3. 日期时间查询：获取当前时间
4. 计算器：执行数学计算

## 输出格式
当你需要使用工具时，请使用以下格式：
Thought: 分析问题
Action: tool_name({"param": "value"})
Observation: [工具执行结果]
Final Answer: 你的最终回答"""

    # 最大迭代次数
    max_iterations: int = 10

    # 是否使用 RAG
    use_rag: bool = True

    # 是否使用工具
    use_tools: bool = True

    # RAG Top-K
    rag_top_k: int = 4

    # 重排序 Top-K
    rerank_top_k: int = 2


# ============================================================
# LangGraph Agent 实现
# ============================================================
class UnifiedAgent:
    """统一 Agent

    基于 LangGraph 的完整 Agent 实现，整合：
    - 记忆管理（LangChain Memory）
    - RAG 检索（LangChain LCEL）
    - 工具调用（LangChain Tools）

    工作流：
    ┌─────────────────────────────────────────────────────────────┐
    │                        START                                 │
    └─────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                    route_decision                            │
    │         (根据问题决定：RAG / Tool / Direct Answer)            │
    └─────────────────────────┬───────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            │                 │                 │
            ▼                 ▼                 ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │    rag       │  │    tools     │  │   direct     │
    │   retrieve   │  │   execution  │  │   answer     │
    └──────┬───────┘  └──────┬───────┘  └──────────────┘
           │                 │                 │
           └─────────────────┼─────────────────┘
                             │
                             ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                     generate_answer                          │
    │                   (基于上下文生成答案)                        │
    └─────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
                              END
    """

    def __init__(self, config: AgentConfig = None):
        """初始化 Agent

        Args:
            config: Agent 配置
        """
        self.config = config or AgentConfig()
        self.memory_manager: Optional[LangChainMemoryManager] = None
        self.rag_chain_builder = RAGChainBuilder()
        
        # 初始化工具
        self.tools = get_all_tools()
        self.tool_map = {tool.name: tool for tool in self.tools}
        
        # 预编译工作流
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """构建工作流"""
        workflow = StateGraph(UnifiedState)

        # 添加节点
        workflow.add_node("route_decision", self._route_node)
        workflow.add_node("rag_retrieve", self._rag_retrieve_node)
        workflow.add_node("tool_execution", self._tool_execution_node)
        workflow.add_node("direct_answer", self._direct_answer_node)
        workflow.add_node("generate_answer", self._generate_answer_node)

        # 设置入口点
        workflow.set_entry_point("route_decision")

        # 添加边
        workflow.add_conditional_edges(
            "route_decision",
            self._route_decision,
            {
                "rag": "rag_retrieve",
                "tools": "tool_execution",
                "direct": "direct_answer",
            }
        )

        # rag_retrieve -> generate_answer
        workflow.add_edge("rag_retrieve", "generate_answer")

        # tool_execution -> 循环检查
        workflow.add_conditional_edges(
            "tool_execution",
            self._should_continue_after_tool,
            {
                "continue": "route_decision",
                "end": "generate_answer",
            }
        )

        # direct_answer -> generate_answer
        workflow.add_edge("direct_answer", "generate_answer")

        # generate_answer -> END
        workflow.add_edge("generate_answer", END)

        return workflow.compile()

    def _route_decision(self, state: UnifiedState) -> Literal["rag", "tools", "direct"]:
        """路由决策

        根据问题类型决定下一步：
        - rag: 需要 RAG 检索
        - tools: 需要执行工具
        - direct: 直接回答
        """
        messages = state.get("messages", [])
        if not messages:
            return "direct"

        last_message = messages[-1]
        if hasattr(last_message, 'content'):
            content = last_message.content.lower()

            # 关键词检测
            if any(kw in content for kw in ["京东", "退换货", "物流", "优惠", "会员", "支付"]):
                return "rag"
            if any(kw in content for kw in ["今天", "现在", "时间", "日期", "天气"]):
                return "tools"
            if any(kw in content for kw in ["计算", "等于", "+", "-", "*", "/"]):
                return "tools"

        # 默认使用 RAG
        return "rag"

    async def _route_node(self, state: UnifiedState) -> UnifiedState:
        """路由节点"""
        logger.info(f"路由决策: {state.get('route')}")
        return {"route": state.get("route")}

    async def _rag_retrieve_node(self, state: UnifiedState) -> UnifiedState:
        """RAG 检索节点"""
        from ..rag.infra import load_vector_store
        from ..rag.rerank import Rerank

        try:
            question = state.get("input", "")
            logger.info(f"RAG 检索: {question[:50]}...")

            # 加载向量存储
            vector_retriever, vector_store = await load_vector_store("jd_help")

            # 检索
            docs = vector_retriever.ainvoke(question)
            
            # 重排序
            reranker = Rerank()
            ranked_docs = await reranker.rerank_documents(question, docs, self.config.rag_top_k)

            # 构建上下文
            context = "\n\n".join([doc.page_content for doc in ranked_docs])

            logger.info(f"RAG 检索完成，找到 {len(ranked_docs)} 个文档")
            return {
                "retrieved_docs": ranked_docs,
                "context": context,
            }
        except Exception as e:
            logger.error(f"RAG 检索失败: {e}")
            return {
                "retrieved_docs": [],
                "context": "",
                "error": str(e),
            }

    async def _tool_execution_node(self, state: UnifiedState) -> UnifiedState:
        """工具执行节点"""
        messages = state.get("messages", [])
        tool_results = dict(state.get("tool_results", {}))
        intermediate_steps = list(state.get("intermediate_steps", []))

        if not messages:
            return {"should_end": True}

        # 获取最后一条消息
        last_message = messages[-1]
        if not hasattr(last_message, 'content'):
            return {"should_end": True}

        content = last_message.content

        # 解析工具调用
        import re
        import json

        patterns = [
            r'Action:\s*(\w+)\s*\(\s*(\{[^}]*\})\s*\)',
            r'Action:\s*(\w+)\s*\(\s*\)',
            r'Action:\s*(\w+)\s*\(\s*([^)]+)\s*\)',
        ]

        tool_name = None
        tool_args = {}

        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                tool_name = match.group(1)
                if len(match.groups()) > 1:
                    args_str = match.group(2).strip()
                    if args_str:
                        try:
                            if args_str.startswith('{'):
                                tool_args = json.loads(args_str)
                            elif '=' in args_str:
                                parts = args_str.split('=')
                                if len(parts) == 2:
                                    tool_args = {parts[0].strip(): parts[1].strip().strip('"\'')}
                        except:
                            pass
                break

        if not tool_name:
            return {"should_end": True}

        # 执行工具
        tool = self.tool_map.get(tool_name)
        if not tool:
            result = f"未知工具: {tool_name}"
        else:
            try:
                result = tool.invoke(tool_args)
                result = str(result)
            except Exception as e:
                result = f"工具执行失败: {str(e)}"

        tool_results[tool_name] = result
        intermediate_steps.append(f"Tool: {tool_name} -> {result[:100]}")

        # 添加工具消息
        tool_message = ToolMessage(
            content=f"Observation: {result}",
            tool_call_id=tool_name,
        )

        return {
            "messages": [tool_message],
            "tool_results": tool_results,
            "intermediate_steps": intermediate_steps,
            "should_end": False,
        }

    async def _direct_answer_node(self, state: UnifiedState) -> UnifiedState:
        """直接回答节点（不需要检索/工具）"""
        # 添加标记，不使用额外上下文
        return {"context": ""}

    async def _generate_answer_node(self, state: UnifiedState) -> UnifiedState:
        """生成答案节点"""
        from ..rag.prompt import RAGPrompt

        try:
            question = state.get("input", "")
            context = state.get("context", "")
            messages = state.get("messages", [])

            # 构建历史
            history_str = ""
            for msg in messages[:-1]:  # 排除最后一条（可能是待回答的问题）
                if hasattr(msg, 'content'):
                    role = "用户" if isinstance(msg, HumanMessage) else "助手"
                    history_str += f"{role}：{msg.content}\n"

            # 使用 RAG 提示词
            rag_prompt = RAGPrompt()
            prompt = rag_prompt.get_jd_template(history=[
                {"role": "user", "content": m} for m in history_str.split("\n") if m
            ])

            # 调用 LLM
            chain = prompt | llm
            response = await chain.ainvoke({
                "question": question,
                "jd_help": context,
            })

            answer = response.content if hasattr(response, 'content') else str(response)

            logger.info(f"生成答案完成，长度: {len(answer)}")
            return {"answer": answer}

        except Exception as e:
            logger.error(f"生成答案失败: {e}")
            return {
                "answer": f"生成答案时出错: {str(e)}",
                "error": str(e),
            }

    def _should_continue_after_tool(self, state: UnifiedState) -> Literal["continue", "end"]:
        """工具执行后判断是否继续"""
        # 检查迭代次数
        iteration = state.get("iteration", 0)
        max_iterations = state.get("max_iterations", self.config.max_iterations)

        if iteration >= max_iterations:
            return "end"

        # 检查是否有最终答案
        messages = state.get("messages", [])
        if messages:
            last_msg = messages[-1]
            if hasattr(last_msg, 'content'):
                if "Final Answer:" in last_msg.content:
                    return "end"

        # 默认继续
        return "end"  # 简化：工具执行一次后就结束

    # ============================================================
    # 对话接口
    # ============================================================

    async def run(
        self,
        question: str,
        session_id: str = "default",
    ) -> Dict[str, Any]:
        """运行 Agent

        Args:
            question: 用户问题
            session_id: 会话 ID

        Returns:
            包含 answer, tool_results 等的字典
        """
        # 创建记忆管理器
        if self.memory_manager is None or self.memory_manager.session_id != session_id:
            self.memory_manager = LangChainMemoryManager(session_id=session_id)

        # 添加用户消息
        self.memory_manager.add_user_message(question)

        # 获取历史
        history_messages = self.memory_manager.get_messages()
        history = [
            {"role": "user" if isinstance(m, HumanMessage) else "assistant", "content": m.content}
            for m in history_messages if hasattr(m, 'content')
        ]

        # 创建初始状态
        initial_state = create_agent_state(
            input=question,
            session_id=session_id,
            max_iterations=self.config.max_iterations,
            system_prompt=self.config.system_prompt,
            use_tools=self.config.use_tools,
            use_rag=self.config.use_rag,
        )
        initial_state["messages"] = [
            SystemMessage(content=self.config.system_prompt),
            HumanMessage(content=question),
        ]
        initial_state["history"] = history

        # 执行工作流
        try:
            final_state = await self.workflow.ainvoke(initial_state)

            answer = final_state.get("answer", "无法生成答案")

            # 添加助手消息
            self.memory_manager.add_ai_message(answer)

            return {
                "answer": answer,
                "tool_results": final_state.get("tool_results", {}),
                "intermediate_steps": final_state.get("intermediate_steps", []),
                "iteration": final_state.get("iteration", 0),
                "context": final_state.get("context", ""),
            }

        except Exception as e:
            logger.error(f"Agent 执行失败: {e}")
            return {
                "answer": f"执行出错: {str(e)}",
                "tool_results": {},
                "intermediate_steps": [],
                "iteration": 0,
                "error": str(e),
            }

    async def run_stream(
        self,
        question: str,
        session_id: str = "default",
    ) -> AsyncGenerator[str, None]:
        """流式运行 Agent"""
        result = await self.run(question, session_id)
        yield result.get("answer", "")

    def clear_memory(self, session_id: str = None) -> None:
        """清除记忆"""
        if self.memory_manager:
            self.memory_manager.clear()


# ============================================================
# 工厂函数
# ============================================================
def create_unified_agent(
    max_iterations: int = 10,
    use_rag: bool = True,
    use_tools: bool = True,
    system_prompt: str = None,
) -> UnifiedAgent:
    """创建统一 Agent

    Args:
        max_iterations: 最大迭代次数
        use_rag: 是否使用 RAG
        use_tools: 是否使用工具
        system_prompt: 自定义系统提示词

    Returns:
        UnifiedAgent 实例
    """
    config = AgentConfig(
        max_iterations=max_iterations,
        use_rag=use_rag,
        use_tools=use_tools,
        system_prompt=system_prompt,
    )
    return UnifiedAgent(config)
