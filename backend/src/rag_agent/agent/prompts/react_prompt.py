"""Agent 提示词模板

提供各种 Agent 模式所需的提示词模板。
"""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class ToolDescription:
    """工具描述"""
    name: str
    description: str
    parameters: Dict[str, Any]


class ReActPrompt:
    """ReAct 模式提示词"""
    
    @staticmethod
    def get_system_prompt(tools: Optional[List[ToolDescription]] = None) -> str:
        """获取 ReAct 系统提示词"""
        tools_section = ""
        if tools:
            tools_lines = []
            for tool in tools:
                params = tool.parameters.get("properties", {})
                param_desc = ""
                if params:
                    param_lines = []
                    for name, info in params.items():
                        ptype = info.get("type", "string")
                        desc = info.get("description", "无描述")
                        required = name in tool.parameters.get("required", [])
                        param_lines.append(
                            f"    - {name} ({ptype}): {desc} {'[必填]' if required else '[可选]'}"
                        )
                    param_desc = "\n参数:\n" + "\n".join(param_lines)
                
                tools_lines.append(f"### {tool.name}\n{tool.description}{param_desc}")
            tools_section = "\n\n".join(tools_lines)
        else:
            tools_section = "无可用工具。"
        
        return f"""你是一个严格的助手，必须严格按照指定格式输出。

## 可用工具

{tools_section}

## 重要：你必须严格遵循以下输出格式

当需要获取实时信息（如日期、时间、天气、搜索等）时，必须使用工具！

输出格式（每一行都要有，不要省略任何一行）：

Thought: 分析问题，判断是否需要使用工具。如果日期/时间相关，必须使用 datetime_query 工具。
Action: tool_name({{"param_name": "param_value"}})  【只在需要工具时输出】
Observation: 【收到工具结果后系统会自动填入】
Final Answer: 你的最终回答

## 关键规则

1. 如果用户问日期、时间、星期几 → 必须使用 datetime_query 工具
2. 如果需要计算 → 必须使用 calculator 工具
3. 如果需要搜索网络信息 → 必须使用 web_search 工具
4. 如果需要查询知识库 → 必须使用 knowledge_search 工具
5. 格式必须完全正确，Action 后面跟 JSON 格式的参数
6. 每次只输出一个 Thought、一个 Action（如果需要）、一个 Final Answer
7. 不要输出额外的内容，只输出格式化的内容

## 正确示例

用户: 今天几号？
Thought: 用户询问今天的日期，这是一个关于日期/时间的问题，我需要使用 datetime_query 工具来获取准确的日期信息。
Action: datetime_query({{"format": "%Y年%m月%d日"}})
Observation: [系统会自动填入工具返回结果]
Final Answer: 今天是2026年4月26日，星期日。

用户: 250 + 380 等于多少？
Thought: 用户需要进行数学计算，我应该使用 calculator 工具。
Action: calculator({{"expression": "250 + 380"}})
Final Answer: 250 + 380 = 630

## 错误示例（不要这样输出）

错误: 今天是2026年4月26日。
（没有使用工具就直接回答日期是错误的！）

正确:
Thought: 用户询问今天的日期，我需要使用 datetime_query 工具获取准确日期。
Action: datetime_query({{"format": "%Y年%m月%d日"}})
Final Answer: 今天是2026年4月26日。"""
    
    @staticmethod
    def get_few_shot_examples() -> List[Dict[str, str]]:
        """获取 few-shot 示例"""
        return [
            {
                "input": "搜索一下今天有什么新闻",
                "output": """Thought: 用户想了解今天的新闻，我应该使用网络搜索工具获取最新信息。
Action: web_search({"query": "今日新闻 2026", "max_results": 5})
Observation: 工具执行成功: [多条新闻结果]
Thought: 搜索到了新闻，可以整理给用户了。
Final Answer: 今天的主要新闻包括...（根据搜索结果整理）"""
            }
        ]


class ConversationalPrompt:
    """对话式 Agent 提示词"""
    
    @staticmethod
    def get_system_prompt(
        persona: str = "智能助手",
        capabilities: Optional[List[str]] = None
    ) -> str:
        """获取对话式系统提示词"""
        caps = ""
        if capabilities:
            caps = "\n".join([f"- {cap}" for cap in capabilities])
        else:
            caps = "- 回答用户问题\n- 提供建议和帮助\n- 在需要时调用工具"
        
        return f"""你是一个{persona}。

## 核心能力
{caps}

## 回复原则
1. 简洁明了，用自然语言回答
2. 如果不确定，诚实说明
3. 在需要时主动使用工具获取信息
4. 保持友好和专业的语气"""
    
    @staticmethod
    def get_conversation_template(
        history: Optional[List[Dict[str, str]]] = None,
        context: Optional[str] = None
    ) -> str:
        """生成对话模板"""
        history_section = ""
        if history:
            lines = []
            for msg in history[-5:]:  # 只保留最近5条
                role = "用户" if msg.get("role") == "user" else "助手"
                content = msg.get("content", "")
                lines.append(f"{role}: {content}")
            history_section = "\n".join(lines)
        else:
            history_section = "（暂无历史记录）"
        
        context_section = f"\n\n## 上下文信息\n{context}" if context else ""
        
        return f"""## 对话历史
{history_section}
{context_section}

## 当前对话
用户: {{input}}
助手: """


class PlanExecutePrompt:
    """规划执行 Agent 提示词"""
    
    @staticmethod
    def get_planner_prompt(tools: Optional[List[ToolDescription]] = None) -> str:
        """获取规划器提示词"""
        tools_section = ""
        if tools:
            tools_lines = []
            for tool in tools:
                tools_lines.append(f"- {tool.name}: {tool.description}")
            tools_section = "\n".join(tools_lines)
        else:
            tools_section = "无可用工具"
        
        return f"""你是一个任务规划专家。

## 可用工具
{tools_section}

## 任务规划

对于复杂任务，你需要将其分解为多个步骤：
1. 分析用户目标
2. 制定执行计划
3. 逐步执行并调整

请用 JSON 格式返回计划：
{{
    "plan": [
        {{"step": 1, "action": "工具名", "reason": "原因"}},
        ...
    ],
    "expected_result": "最终期望结果"
}}"""
    
    @staticmethod
    def get_executor_prompt() -> str:
        """获取执行器提示词"""
        return """你是一个任务执行专家。

## 执行原则
1. 严格按照计划执行每个步骤
2. 记录每个步骤的执行结果
3. 如果某步骤失败，尝试调整或报告
4. 最终汇总所有结果给出完整回答

## 响应格式
Step 1: [执行的动作]
Result: [结果]
Step 2: [执行的动作]
Result: [结果]
...
Final Answer: [汇总回答]"""


class ToolUsePrompt:
    """工具使用相关提示词"""
    
    @staticmethod
    def get_tool_selection_prompt() -> str:
        """获取工具选择提示词"""
        return """给定用户问题和可用工具，选择最合适的工具。

问题: {question}

可用工具:
{tools}

选择策略:
1. 如果问题可以直接回答，不需要工具
2. 如果需要特定信息（如时间、计算），选择对应工具
3. 如果需要多个工具，按顺序执行

输出格式:
如果选择工具: {{"tool": "tool_name", "reason": "选择原因"}}
如果不需要工具: {{"tool": null, "reason": "原因"}}"""
    
    @staticmethod
    def get_result_synthesis_prompt() -> str:
        """获取结果综合提示词"""
        return """基于以下信息，综合给出最终回答。

用户问题: {question}

中间结果:
{results}

要求:
1. 整合所有工具返回的信息
2. 用清晰易懂的方式回答
3. 如果工具返回错误，说明情况并给出建议"""
