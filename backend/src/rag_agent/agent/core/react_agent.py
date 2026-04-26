"""ReAct Agent 实现

基于 ReAct (Reasoning + Acting) 范式的 Agent 实现。
支持 Thought → Action → Observation 循环推理。
"""
import json
import re
from typing import List, Optional, Dict, Any, AsyncGenerator
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda

from .agent import BaseAgent, AgentConfig, AgentResponse, AgentType
from ..prompts.react_prompt import ReActPrompt, ToolDescription
from ...models.model_registry import llm
from ...core.logger import logger


class ReActAgent(BaseAgent):
    """ReAct Agent 实现
    
    推理模式:
    1. Thought: 分析问题，决定下一步行动
    2. Action: 调用工具
    3. Observation: 获取工具返回结果
    4. 重复直到得到答案
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        super().__init__(config)
        self._intermediate_steps: List[str] = []
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        # 将工具转换为 ToolDescription 格式
        tool_descriptions = []
        for tool in self.tools:
            params = tool.parameters if hasattr(tool, 'parameters') else {}
            tool_desc = ToolDescription(
                name=tool.name,
                description=tool.description,
                parameters=params
            )
            tool_descriptions.append(tool_desc)
        
        # 使用 ReActPrompt 生成提示词
        return ReActPrompt.get_system_prompt(tool_descriptions)
    
    def _format_tools_description(self) -> str:
        """格式化工具描述"""
        if not self.tools:
            return "无可用工具。"
        
        descriptions = []
        for tool in self.tools:
            params = tool.parameters.get("properties", {})
            param_str = ""
            if params:
                param_lines = []
                for name, info in params.items():
                    ptype = info.get("type", "string")
                    desc = info.get("description", "无描述")
                    required = name in tool.parameters.get("required", [])
                    param_lines.append(f"  - {name} ({ptype}): {desc} {'[必填]' if required else '[可选]'}")
                param_str = "\n" + "\n".join(param_lines)
            
            descriptions.append(f"### {tool.name}\n{tool.description}{param_str}")
        
        return "\n\n".join(descriptions)
    
    def _parse_ai_message(self, message: str) -> Dict[str, Any]:
        """解析 AI 消息，提取 Thought、Action 等部分"""
        result = {
            "thought": "",
            "action": None,
            "final_answer": None
        }
        
        # 提取 Thought
        thought_match = re.search(r'Thought:\s*(.+?)(?=\n(?:Action|Final)|$)', message, re.DOTALL)
        if thought_match:
            result["thought"] = thought_match.group(1).strip()
        
        # 提取 Action - 更宽松的匹配
        # 匹配格式: Action: tool_name({"param": "value"}) 或 Action: tool_name()
        action_patterns = [
            r'Action:\s*(\w+)\s*\(\s*(\{[^}]*\})\s*\)',  # Action: name({"k": "v"})
            r'Action:\s*(\w+)\s*\(\s*\)',  # Action: name()
            r'Action:\s*(\w+)\s*\(\s*([^)]+)\s*\)',  # Action: name(value)
        ]
        
        for pattern in action_patterns:
            action_match = re.search(pattern, message, re.DOTALL)
            if action_match:
                tool_name = action_match.group(1)
                args = {}
                
                if len(action_match.groups()) > 1:
                    args_str = action_match.group(2).strip()
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
                
                result["action"] = {
                    "tool": tool_name,
                    "args": args
                }
                break
        
        # 提取 Final Answer
        final_match = re.search(r'Final Answer:\s*(.+?)$', message, re.DOTALL)
        if final_match:
            result["final_answer"] = final_match.group(1).strip()
        
        # 如果没有找到 Final Answer，但有其他内容，可能是直接回答
        if not result["final_answer"] and message.strip():
            # 检查是否只是对话式回答
            if not result["action"] and not result["thought"]:
                # 没有 thought 和 action，可能是简单回答
                result["final_answer"] = message.strip()
        
        return result
    
    async def run(self, user_input: str, **kwargs) -> AgentResponse:
        """执行 ReAct 推理循环"""
        self.clear_tool_calls()
        self._intermediate_steps.clear()
        
        history = kwargs.get("history", [])
        system_prompt = self._build_system_prompt()
        
        logger.info(f"ReActAgent 开始处理: {user_input[:50]}...")
        
        # 构建消息历史
        messages = [
            SystemMessage(content=system_prompt),
            *self._convert_history(history),
            HumanMessage(content=user_input)
        ]
        
        iterations = 0
        max_iterations = self.config.max_iterations
        
        while iterations < max_iterations:
            iterations += 1
            
            # 调用 LLM
            response = await llm.ainvoke(messages)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            logger.info(f"ReAct 第 {iterations} 轮 LLM 响应长度: {len(response_text)}")
            
            # 解析响应
            parsed = self._parse_ai_message(response_text)
            
            # 添加 AI 响应到历史
            messages.append(AIMessage(content=response_text))
            
            # 优先检查是否需要执行工具
            if parsed["action"]:
                action = parsed["action"]
                tool_name = action["tool"]
                args = action["args"]
                
                thought = parsed["thought"]
                self._intermediate_steps.append(f"Thought: {thought}")
                self._intermediate_steps.append(f"Action: {tool_name}({args})")
                
                # 执行工具
                tool_result = await self.execute_tool(tool_name, **args)
                
                observation = (
                    f"工具执行{'成功' if tool_result.success else '失败'}: {tool_result.output}"
                    if tool_result.success
                    else f"错误: {tool_result.error}"
                )
                self._intermediate_steps.append(f"Observation: {observation[:500]}")
                
                # 添加观察结果到消息
                messages.append(HumanMessage(
                    content=f"Observation: {observation}"
                ))
                # 继续下一轮推理
                continue
            
            # 没有 Action 时，检查是否有最终答案
            if parsed["final_answer"]:
                logger.info(f"ReActAgent 完成，迭代次数: {iterations}")
                return AgentResponse(
                    answer=parsed["final_answer"],
                    tool_calls=self.get_tool_call_records(),
                    iterations=iterations,
                    agent_type=AgentType.REACT.value,
                    intermediate_steps=self._intermediate_steps
                )
            
            # 没有动作也没有答案
            if parsed["thought"]:
                self._intermediate_steps.append(f"Thought: {parsed['thought']}")
                continue
            else:
                logger.warning(f"ReActAgent 无法提取有效响应，返回原始内容")
                return AgentResponse(
                    answer=response_text,
                    tool_calls=self.get_tool_call_records(),
                    iterations=iterations,
                    agent_type=AgentType.REACT.value,
                    intermediate_steps=self._intermediate_steps
                )
        
        # 达到最大迭代次数
        logger.warning(f"ReActAgent 达到最大迭代次数: {max_iterations}")
        return AgentResponse(
            answer="抱歉，问题较为复杂，已达到最大推理步骤。请尝试简化问题或分步提问。",
            tool_calls=self.get_tool_call_records(),
            iterations=iterations,
            agent_type=AgentType.REACT.value,
            intermediate_steps=self._intermediate_steps
        )
    
    async def run_stream(self, user_input: str, **kwargs) -> AsyncGenerator[str, None]:
        """流式执行 ReAct Agent"""
        # 对于复杂推理，流式输出较为复杂，这里简化处理
        response = await self.run(user_input, **kwargs)
        yield response.answer
    
    def _convert_history(self, history: List[Dict]) -> List:
        """转换历史记录为 LangChain 消息格式"""
        messages = []
        for msg in history:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
        
        return messages


class ReActAgentFactory:
    """ReAct Agent 工厂类"""
    
    @staticmethod
    def create(
        tools: List[Any] = None,
        max_iterations: int = 10,
        system_prompt: Optional[str] = None
    ) -> ReActAgent:
        """创建 ReAct Agent"""
        config = AgentConfig(
            agent_type=AgentType.REACT,
            max_iterations=max_iterations,
            tools=tools or [],
            system_prompt=system_prompt
        )
        return ReActAgent(config)
