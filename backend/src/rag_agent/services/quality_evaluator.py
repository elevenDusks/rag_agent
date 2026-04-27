"""LLM 质量评估模块

该模块使用 LLM-as-Judge 方式评估 RAG 回答的质量。
"""
from typing import Optional, List
from dataclasses import dataclass

from ..core.logger import logger
from ..models.model_registry import llm
from ..models.metrics import RAGQueryLog


@dataclass
class QualityScore:
    """质量评分结果"""
    query: str
    response: str
    relevance: float  # 0-1，与问题相关性
    helpfulness: float  # 0-1，有用性
    accuracy: float  # 0-1，准确性
    overall: float  # 综合评分
    reasoning: str  # 评分理由


QUALITY_PROMPT = """你是一个专业的 RAG 系统质量评估员。请评估以下问答对的质量。

问题: {question}

回答: {response}

请从以下几个方面评估回答质量：

1. 相关性 (relevance): 回答是否针对问题？
2. 有用性 (helpfulness): 回答对用户是否有帮助？
3. 准确性 (accuracy): 回答内容是否正确？

请以 JSON 格式返回评估结果：
{{
    "relevance": 0.0-1.0 的分数,
    "helpfulness": 0.0-1.0 的分数,
    "accuracy": 0.0-1.0 的分数,
    "reasoning": "评分理由（1-2句话）"
}}

只返回 JSON，不要包含其他内容。
"""


class QualityEvaluator:
    """LLM 质量评估器

    使用 LLM-as-Judge 方式评估 RAG 回答质量。
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self._initialized = False

    async def evaluate(
        self,
        question: str,
        response: str,
        references: Optional[List[str]] = None
    ) -> QualityScore:
        """评估单个问答对的质量

        Args:
            question: 用户问题
            response: RAG 回答
            references: 参考文档列表

        Returns:
            QualityScore: 质量评分结果
        """
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import ChatPromptTemplate

        prompt = ChatPromptTemplate.from_template(QUALITY_PROMPT)
        chain = prompt | llm | StrOutputParser()

        try:
            result = await chain.ainvoke({
                "question": question,
                "response": response
            })

            # 解析 JSON 结果
            import json
            # 尝试提取 JSON
            json_str = result.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]
            
            data = json.loads(json_str.strip())

            relevance = float(data.get("relevance", 0.5))
            helpfulness = float(data.get("helpfulness", 0.5))
            accuracy = float(data.get("accuracy", 0.5))
            overall = (relevance + helpfulness + accuracy) / 3
            reasoning = data.get("reasoning", "")

            return QualityScore(
                query=question,
                response=response,
                relevance=relevance,
                helpfulness=helpfulness,
                accuracy=accuracy,
                overall=overall,
                reasoning=reasoning,
            )
        except Exception as e:
            logger.error(f"LLM 质量评估失败: {e}")
            # 返回默认评分
            return QualityScore(
                query=question,
                response=response,
                relevance=0.5,
                helpfulness=0.5,
                accuracy=0.5,
                overall=0.5,
                reasoning=f"评估失败: {str(e)[:100]}",
            )

    async def evaluate_batch(
        self,
        queries: List[RAGQueryLog],
        sample_size: int = 10
    ) -> List[QualityScore]:
        """批量评估查询日志的质量

        Args:
            queries: 查询日志列表
            sample_size: 采样大小，避免评估过多

        Returns:
            List[QualityScore]: 质量评分列表
        """
        import random
        
        # 采样
        if len(queries) > sample_size:
            sampled = random.sample(queries, sample_size)
        else:
            sampled = queries

        results = []
        for log in sampled:
            if log.response:
                score = await self.evaluate(log.query, log.response)
                results.append(score)

        return results


# 全局单例
quality_evaluator = QualityEvaluator()
