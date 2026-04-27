"""指标 API 接口模块

该模块提供了 RAG 量化指标相关的 API 接口，包括指标统计、用户反馈和质量报告。
"""
from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_, Integer
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.mysql_client import get_db
from ..models.metrics import RAGQueryLog, UserFeedback, DailyMetrics
from ..core.logger import logger
from ..services.quality_evaluator import quality_evaluator, QualityScore

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


# ==================== Pydantic 响应模型 ====================

class MetricsSummary(BaseModel):
    """指标汇总"""
    total_queries: int
    success_count: int
    success_rate: float
    avg_retrieval_time_ms: float
    avg_generation_time_ms: float
    avg_total_latency_ms: float
    avg_input_tokens: float
    avg_output_tokens: float
    avg_relevance_score: float
    avg_rating: Optional[float] = None
    thumbs_up_rate: float


class DailyMetricItem(BaseModel):
    """每日指标"""
    date: date
    collection_name: Optional[str]
    total_queries: int
    success_rate: float
    avg_total_latency_ms: float
    avg_relevance_score: float
    avg_rating: Optional[float] = None
    thumbs_up_rate: float


class QualityReport(BaseModel):
    """质量报告"""
    total_queries: int
    avg_quality_score: Optional[float]
    avg_relevance_score: float
    avg_rating: Optional[float]
    thumbs_up_rate: float
    problem_queries: int  # 低质量查询数量


class FeedbackCreate(BaseModel):
    """反馈创建请求"""
    query_log_id: int
    rating: Optional[int] = Field(None, ge=1, le=5)
    thumbs_up: bool = False
    thumbs_down: bool = False
    feedback_text: Optional[str] = None


class FeedbackResponse(BaseModel):
    """反馈响应"""
    id: int
    query_log_id: int
    rating: Optional[int]
    thumbs_up: bool
    thumbs_down: bool
    created_at: datetime

    class Config:
        from_attributes = True


class FeedbackStats(BaseModel):
    """反馈统计"""
    total_feedbacks: int
    avg_rating: Optional[float]
    thumbs_up_count: int
    thumbs_down_count: int
    thumbs_up_rate: float
    rating_distribution: dict = Field(default_factory=dict)


class QueryLogResponse(BaseModel):
    """查询日志响应"""
    id: int
    session_id: str
    query: str
    collection_name: Optional[str]
    retrieval_time_ms: int
    chunks_retrieved: int
    avg_relevance_score: float
    generation_time_ms: int
    input_tokens: int
    output_tokens: int
    total_latency_ms: int
    is_success: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== API 端点 ====================

@router.get("/summary", response_model=MetricsSummary)
async def get_metrics_summary(
    days: int = Query(7, ge=1, le=90, description="统计天数"),
    collection: Optional[str] = Query(None, description="知识库集合名称过滤")
) -> MetricsSummary:
    """获取指标汇总

    返回指定时间范围内的关键指标汇总。
    """
    async with get_db() as session:
        try:
            # 计算起始日期
            start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            start_date = start_date - timedelta(days=days)

            # 基础查询条件
            conditions = [RAGQueryLog.created_at >= start_date]
            if collection:
                conditions.append(RAGQueryLog.collection_name == collection)

            # 查询原始日志聚合
            query = select(
                func.count(RAGQueryLog.id).label("total_queries"),
                func.sum(func.cast(RAGQueryLog.is_success, Integer)).label("success_count"),
                func.avg(RAGQueryLog.retrieval_time_ms).label("avg_retrieval_time_ms"),
                func.avg(RAGQueryLog.generation_time_ms).label("avg_generation_time_ms"),
                func.avg(RAGQueryLog.total_latency_ms).label("avg_total_latency_ms"),
                func.avg(RAGQueryLog.input_tokens).label("avg_input_tokens"),
                func.avg(RAGQueryLog.output_tokens).label("avg_output_tokens"),
                func.avg(RAGQueryLog.avg_relevance_score).label("avg_relevance_score"),
            ).where(and_(*conditions))

            result = await session.execute(query)
            row = result.one()

            # 查询反馈统计
            feedback_query = select(
                func.count(UserFeedback.id).label("total_feedbacks"),
                func.avg(UserFeedback.rating).label("avg_rating"),
                func.sum(func.cast(UserFeedback.thumbs_up, Integer)).label("thumbs_up_count"),
                func.sum(func.cast(UserFeedback.thumbs_down, Integer)).label("thumbs_down_count"),
            ).join(
                RAGQueryLog, UserFeedback.query_log_id == RAGQueryLog.id
            ).where(and_(*conditions))

            feedback_result = await session.execute(feedback_query)
            feedback_row = feedback_result.one()

            # 计算成功率
            total = row.total_queries or 1
            success_count = int(row.success_count or 0)
            success_rate = success_count / total if total > 0 else 0.0

            # 计算点赞率
            thumbs_up = int(feedback_row.thumbs_up_count or 0)
            thumbs_down = int(feedback_row.thumbs_down_count or 0)
            total_feedback = thumbs_up + thumbs_down
            thumbs_up_rate = thumbs_up / total_feedback if total_feedback > 0 else 0.0

            return MetricsSummary(
                total_queries=row.total_queries or 0,
                success_count=success_count,
                success_rate=round(success_rate, 4),
                avg_retrieval_time_ms=round(float(row.avg_retrieval_time_ms or 0), 2),
                avg_generation_time_ms=round(float(row.avg_generation_time_ms or 0), 2),
                avg_total_latency_ms=round(float(row.avg_total_latency_ms or 0), 2),
                avg_input_tokens=round(float(row.avg_input_tokens or 0), 2),
                avg_output_tokens=round(float(row.avg_output_tokens or 0), 2),
                avg_relevance_score=round(float(row.avg_relevance_score or 0), 4),
                avg_rating=round(float(feedback_row.avg_rating), 2) if feedback_row.avg_rating else None,
                thumbs_up_rate=round(thumbs_up_rate, 4),
            )
        except Exception as e:
            logger.error(f"获取指标汇总失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily", response_model=List[DailyMetricItem])
async def get_daily_metrics(
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    collection: Optional[str] = Query(None, description="知识库集合名称过滤")
) -> List[DailyMetricItem]:
    """获取每日指标趋势

    返回指定日期范围内的每日指标数据。
    """
    async with get_db() as session:
        try:
            conditions = [
                DailyMetrics.date >= start_date,
                DailyMetrics.date <= end_date
            ]
            if collection:
                conditions.append(DailyMetrics.collection_name == collection)

            query = select(DailyMetrics).where(and_(*conditions)).order_by(DailyMetrics.date)

            result = await session.execute(query)
            metrics = result.scalars().all()

            return [
                DailyMetricItem(
                    date=m.date,
                    collection_name=m.collection_name,
                    total_queries=m.total_queries,
                    success_rate=round(m.success_rate, 4),
                    avg_total_latency_ms=round(m.avg_total_latency_ms, 2),
                    avg_relevance_score=round(m.avg_relevance_score, 4),
                    avg_rating=round(m.avg_rating, 2) if m.avg_rating else None,
                    thumbs_up_rate=round(m.thumbs_up_rate, 4),
                )
                for m in metrics
            ]
        except Exception as e:
            logger.error(f"获取每日指标失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/quality", response_model=QualityReport)
async def get_quality_report(
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    collection: Optional[str] = Query(None, description="知识库集合名称过滤")
) -> QualityReport:
    """获取质量报告

    基于用户反馈和 LLM 评估生成质量报告。
    """
    async with get_db() as session:
        try:
            conditions = [
                RAGQueryLog.created_at >= datetime.combine(start_date, datetime.min.time()),
                RAGQueryLog.created_at <= datetime.combine(end_date, datetime.max.time()),
            ]
            if collection:
                conditions.append(RAGQueryLog.collection_name == collection)

            # 查询基础统计
            query = select(
                func.count(RAGQueryLog.id).label("total_queries"),
                func.avg(RAGQueryLog.avg_relevance_score).label("avg_relevance_score"),
            ).where(and_(*conditions))

            result = await session.execute(query)
            row = result.one()

            # 查询反馈统计
            feedback_query = select(
                func.count(UserFeedback.id).label("total_feedbacks"),
                func.avg(UserFeedback.rating).label("avg_rating"),
                func.sum(func.cast(UserFeedback.thumbs_up, Integer)).label("thumbs_up_count"),
                func.sum(func.cast(UserFeedback.thumbs_down, Integer)).label("thumbs_down_count"),
            ).join(
                RAGQueryLog, UserFeedback.query_log_id == RAGQueryLog.id
            ).where(and_(*conditions))

            feedback_result = await session.execute(feedback_query)
            feedback_row = feedback_result.one()

            # 计算点赞率
            thumbs_up = int(feedback_row.thumbs_up_count or 0)
            thumbs_down = int(feedback_row.thumbs_down_count or 0)
            total_feedback = thumbs_up + thumbs_down
            thumbs_up_rate = thumbs_up / total_feedback if total_feedback > 0 else 0.0

            # 估算问题查询 (低评分或点踩)
            problem_queries = thumbs_down + (int(feedback_row.total_feedbacks or 0) - thumbs_up - thumbs_down) // 2

            return QualityReport(
                total_queries=row.total_queries or 0,
                avg_quality_score=None,  # LLM 评估待实现
                avg_relevance_score=round(float(row.avg_relevance_score or 0), 4),
                avg_rating=round(float(feedback_row.avg_rating), 2) if feedback_row.avg_rating else None,
                thumbs_up_rate=round(thumbs_up_rate, 4),
                problem_queries=problem_queries,
            )
        except Exception as e:
            logger.error(f"获取质量报告失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    feedback: FeedbackCreate,
    db: AsyncSession = Depends(get_db)
) -> FeedbackResponse:
    """提交用户反馈

    用户可以对 RAG 回答进行评分和评价。
    """
    try:
        # 验证 query_log_id 存在
        result = await db.execute(
            select(RAGQueryLog).where(RAGQueryLog.id == feedback.query_log_id)
        )
        query_log = result.scalar_one_or_none()
        if not query_log:
            raise HTTPException(status_code=404, detail="查询记录不存在")

        # 创建反馈记录
        db_feedback = UserFeedback(
            query_log_id=feedback.query_log_id,
            rating=feedback.rating,
            thumbs_up=feedback.thumbs_up,
            thumbs_down=feedback.thumbs_down,
            feedback_text=feedback.feedback_text,
        )
        db.add(db_feedback)
        await db.commit()
        await db.refresh(db_feedback)

        return FeedbackResponse.model_validate(db_feedback)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"提交反馈失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback/stats", response_model=FeedbackStats)
async def get_feedback_stats(
    days: int = Query(30, ge=1, le=365, description="统计天数")
) -> FeedbackStats:
    """获取反馈统计

    返回指定时间范围内的用户反馈统计。
    """
    async with get_db() as session:
        try:
            start_date = datetime.utcnow() - timedelta(days=days)

            query = select(
                func.count(UserFeedback.id).label("total_feedbacks"),
                func.avg(UserFeedback.rating).label("avg_rating"),
                func.sum(func.cast(UserFeedback.thumbs_up, Integer)).label("thumbs_up_count"),
                func.sum(func.cast(UserFeedback.thumbs_down, Integer)).label("thumbs_down_count"),
            ).where(UserFeedback.created_at >= start_date)

            result = await session.execute(query)
            row = result.one()

            # 评分分布
            distribution_query = select(
                UserFeedback.rating,
                func.count(UserFeedback.id).label("count")
            ).where(
                and_(
                    UserFeedback.created_at >= start_date,
                    UserFeedback.rating.isnot(None)
                )
            ).group_by(UserFeedback.rating)

            dist_result = await session.execute(distribution_query)
            distribution = {str(row.rating): row.count for row in dist_result}

            # 计算点赞率
            thumbs_up = int(row.thumbs_up_count or 0)
            thumbs_down = int(row.thumbs_down_count or 0)
            total_feedback = thumbs_up + thumbs_down
            thumbs_up_rate = thumbs_up / total_feedback if total_feedback > 0 else 0.0

            return FeedbackStats(
                total_feedbacks=row.total_feedbacks or 0,
                avg_rating=round(float(row.avg_rating), 2) if row.avg_rating else None,
                thumbs_up_count=thumbs_up,
                thumbs_down_count=thumbs_down,
                thumbs_up_rate=round(thumbs_up_rate, 4),
                rating_distribution=distribution,
            )
        except Exception as e:
            logger.error(f"获取反馈统计失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/queries", response_model=List[QueryLogResponse])
async def get_recent_queries(
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    collection: Optional[str] = Query(None, description="知识库集合名称过滤")
) -> List[QueryLogResponse]:
    """获取最近的查询日志

    返回最近的 RAG 查询记录。
    """
    async with get_db() as session:
        try:
            conditions = []
            if collection:
                conditions.append(RAGQueryLog.collection_name == collection)

            query = select(RAGQueryLog)
            if conditions:
                query = query.where(and_(*conditions))
            query = query.order_by(RAGQueryLog.created_at.desc()).limit(limit).offset(offset)

            result = await session.execute(query)
            queries = result.scalars().all()

            return [QueryLogResponse.model_validate(q) for q in queries]
        except Exception as e:
            logger.error(f"获取查询日志失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluate")
async def evaluate_response(
    query_log_id: int = Query(..., description="查询日志ID")
) -> QualityScore:
    """使用 LLM 评估单个回答的质量

    基于 LLM-as-Judge 方式评估回答质量。
    """
    async with get_db() as session:
        try:
            result = await session.execute(
                select(RAGQueryLog).where(RAGQueryLog.id == query_log_id)
            )
            query_log = result.scalar_one_or_none()
            
            if not query_log:
                raise HTTPException(status_code=404, detail="查询记录不存在")
            
            if not query_log.response:
                raise HTTPException(status_code=400, detail="该查询没有响应内容可供评估")
            
            score = await quality_evaluator.evaluate(
                question=query_log.query,
                response=query_log.response,
            )
            
            return score
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"LLM 评估失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluate/batch")
async def evaluate_batch(
    days: int = Query(7, ge=1, le=90, description="评估最近N天的数据"),
    sample_size: int = Query(10, ge=1, le=50, description="采样大小")
) -> dict:
    """批量评估回答质量

    对最近的查询日志进行采样评估。
    """
    async with get_db() as session:
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            result = await session.execute(
                select(RAGQueryLog)
                .where(
                    and_(
                        RAGQueryLog.created_at >= start_date,
                        RAGQueryLog.is_success == True,
                        RAGQueryLog.response.isnot(None)
                    )
                )
                .order_by(RAGQueryLog.created_at.desc())
                .limit(100)
            )
            query_logs = result.scalars().all()
            
            if not query_logs:
                return {
                    "message": "没有可评估的数据",
                    "evaluated_count": 0,
                    "scores": []
                }
            
            scores = await quality_evaluator.evaluate_batch(
                queries=query_logs,
                sample_size=sample_size
            )
            
            avg_overall = sum(s.overall for s in scores) / len(scores) if scores else 0
            avg_relevance = sum(s.relevance for s in scores) / len(scores) if scores else 0
            avg_helpfulness = sum(s.helpfulness for s in scores) / len(scores) if scores else 0
            avg_accuracy = sum(s.accuracy for s in scores) / len(scores) if scores else 0
            
            return {
                "evaluated_count": len(scores),
                "total_available": len(query_logs),
                "summary": {
                    "avg_overall": round(avg_overall, 4),
                    "avg_relevance": round(avg_relevance, 4),
                    "avg_helpfulness": round(avg_helpfulness, 4),
                    "avg_accuracy": round(avg_accuracy, 4),
                },
                "scores": [
                    {
                        "query": s.query[:100] + "..." if len(s.query) > 100 else s.query,
                        "overall": round(s.overall, 4),
                        "relevance": round(s.relevance, 4),
                        "helpfulness": round(s.helpfulness, 4),
                        "accuracy": round(s.accuracy, 4),
                        "reasoning": s.reasoning,
                    }
                    for s in scores
                ]
            }
        except Exception as e:
            logger.error(f"批量评估失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
