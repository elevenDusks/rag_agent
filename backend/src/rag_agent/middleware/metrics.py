"""指标采集中间件

该模块提供了 RAG 查询指标的异步采集和批量写入功能。
"""
import asyncio
import json
from datetime import datetime, date
from typing import Optional, List
from dataclasses import dataclass

from sqlalchemy import select, func, and_, Integer
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.mysql_client import AsyncSessionLocal
from ..models.metrics import RAGQueryLog, DailyMetrics, UserFeedback
from ..core.logger import logger


@dataclass
class QueryMetrics:
    """查询指标数据类"""
    session_id: str
    user_id: Optional[int]
    query: str
    collection_name: Optional[str]

    # 检索指标
    retrieval_time_ms: int = 0
    chunks_retrieved: int = 0
    avg_relevance_score: float = 0.0

    # 生成指标
    generation_time_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    response_length: int = 0

    # 端到端指标
    total_latency_ms: int = 0
    ttft_ms: int = 0
    is_success: bool = True
    error_message: Optional[str] = None

    # 响应内容
    response: Optional[str] = None
    references_json: Optional[str] = None


class MetricsCollector:
    """指标采集器

    异步采集 RAG 查询指标，并批量写入数据库。
    """
    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._queue: asyncio.Queue[QueryMetrics] = asyncio.Queue(maxsize=1000)
        self._batch_size = 50
        self._flush_interval = 5.0  # 秒
        self._worker_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """启动采集器后台任务"""
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._worker())
        logger.info("指标采集器已启动")

    async def stop(self):
        """停止采集器并刷新剩余数据"""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        # 刷新剩余数据
        await self._flush()
        logger.info("指标采集器已停止")

    async def record(self, metrics: QueryMetrics):
        """记录查询指标

        Args:
            metrics: 查询指标数据
        """
        try:
            self._queue.put_nowait(metrics)
        except asyncio.QueueFull:
            logger.warning("指标队列已满，跳过记录")

    async def _worker(self):
        """后台工作协程"""
        last_flush = datetime.utcnow()
        buffer: List[QueryMetrics] = []

        while self._running:
            try:
                # 等待队列数据或超时
                try:
                    metrics = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=1.0
                    )
                    buffer.append(metrics)
                except asyncio.TimeoutError:
                    pass

                # 检查是否需要刷新
                now = datetime.utcnow()
                should_flush = (
                    len(buffer) >= self._batch_size or
                    (len(buffer) > 0 and (now - last_flush).total_seconds() >= self._flush_interval)
                )

                if should_flush:
                    await self._write_batch(buffer)
                    buffer = []
                    last_flush = now

            except Exception as e:
                logger.error(f"指标采集 worker 异常: {e}")

    async def _write_batch(self, metrics_list: List[QueryMetrics]):
        """批量写入数据库"""
        if not metrics_list:
            return

        try:
            async with AsyncSessionLocal() as session:
                # 批量创建日志记录
                logs = [
                    RAGQueryLog(
                        session_id=m.session_id,
                        user_id=m.user_id,
                        query=m.query,
                        collection_name=m.collection_name,
                        retrieval_time_ms=m.retrieval_time_ms,
                        chunks_retrieved=m.chunks_retrieved,
                        avg_relevance_score=m.avg_relevance_score,
                        generation_time_ms=m.generation_time_ms,
                        input_tokens=m.input_tokens,
                        output_tokens=m.output_tokens,
                        response_length=m.response_length,
                        total_latency_ms=m.total_latency_ms,
                        ttft_ms=m.ttft_ms,
                        is_success=m.is_success,
                        error_message=m.error_message,
                        response=m.response,
                        references_json=m.references_json,
                    )
                    for m in metrics_list
                ]
                session.add_all(logs)
                await session.commit()
                logger.debug(f"批量写入 {len(logs)} 条指标记录")
        except Exception as e:
            logger.error(f"批量写入指标失败: {e}")

    async def _flush(self):
        """刷新缓冲区数据"""
        if self._queue.empty():
            return

        metrics_list = []
        while not self._queue.empty():
            try:
                metrics_list.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break

        if metrics_list:
            await self._write_batch(metrics_list)


class MetricsAggregator:
    """每日指标聚合器

    将原始日志聚合为每日统计指标。
    """

    @staticmethod
    async def aggregate_daily(date_to_aggregate: Optional[date] = None):
        """聚合指定日期的指标

        Args:
            date_to_aggregate: 要聚合的日期，默认为昨天
        """
        if date_to_aggregate is None:
            date_to_aggregate = datetime.utcnow().date()

        start_datetime = datetime.combine(date_to_aggregate, datetime.min.time())
        end_datetime = datetime.combine(date_to_aggregate, datetime.max.time())

        async with AsyncSessionLocal() as session:
            try:
                # 按 collection_name 分组聚合
                query = select(
                    RAGQueryLog.collection_name,
                    func.count(RAGQueryLog.id).label("total_queries"),
                    func.sum(func.cast(RAGQueryLog.is_success, int)).label("success_count"),
                    func.avg(RAGQueryLog.retrieval_time_ms).label("avg_retrieval_time_ms"),
                    func.avg(RAGQueryLog.generation_time_ms).label("avg_generation_time_ms"),
                    func.avg(RAGQueryLog.total_latency_ms).label("avg_total_latency_ms"),
                    func.avg(RAGQueryLog.ttft_ms).label("avg_ttft_ms"),
                    func.avg(RAGQueryLog.input_tokens).label("avg_input_tokens"),
                    func.avg(RAGQueryLog.output_tokens).label("avg_output_tokens"),
                    func.sum(RAGQueryLog.input_tokens).label("total_input_tokens"),
                    func.sum(RAGQueryLog.output_tokens).label("total_output_tokens"),
                    func.avg(RAGQueryLog.avg_relevance_score).label("avg_relevance_score"),
                    func.avg(RAGQueryLog.chunks_retrieved).label("avg_chunks_retrieved"),
                ).where(
                    and_(
                        RAGQueryLog.created_at >= start_datetime,
                        RAGQueryLog.created_at <= end_datetime,
                    )
                ).group_by(RAGQueryLog.collection_name)

                result = await session.execute(query)
                rows = result.all()

                for row in rows:
                    total = row.total_queries or 1
                    success_count = int(row.success_count or 0)
                    success_rate = success_count / total if total > 0 else 0.0

                    # 查询该日期和集合的用户反馈
                    feedback_query = select(
                        func.avg(UserFeedback.rating).label("avg_rating"),
                        func.sum(func.cast(UserFeedback.thumbs_up, int)).label("thumbs_up_count"),
                        func.sum(func.cast(UserFeedback.thumbs_down, int)).label("thumbs_down_count"),
                    ).join(
                        RAGQueryLog, UserFeedback.query_log_id == RAGQueryLog.id
                    ).where(
                        and_(
                            UserFeedback.created_at >= start_datetime,
                            UserFeedback.created_at <= end_datetime,
                            RAGQueryLog.collection_name == row.collection_name,
                        )
                    )
                    feedback_result = await session.execute(feedback_query)
                    feedback_row = feedback_result.one()

                    thumbs_up = int(feedback_row.thumbs_up_count or 0)
                    thumbs_down = int(feedback_row.thumbs_down_count or 0)
                    total_feedback = thumbs_up + thumbs_down
                    thumbs_up_rate = thumbs_up / total_feedback if total_feedback > 0 else 0.0

                    # 检查是否存在记录
                    existing = await session.execute(
                        select(DailyMetrics).where(
                            and_(
                                DailyMetrics.date == date_to_aggregate,
                                DailyMetrics.collection_name == row.collection_name,
                            )
                        )
                    )
                    existing_metric = existing.scalar_one_or_none()

                    if existing_metric:
                        # 更新现有记录
                        existing_metric.total_queries = row.total_queries or 0
                        existing_metric.success_count = success_count
                        existing_metric.success_rate = round(success_rate, 4)
                        existing_metric.avg_retrieval_time_ms = round(float(row.avg_retrieval_time_ms or 0), 2)
                        existing_metric.avg_generation_time_ms = round(float(row.avg_generation_time_ms or 0), 2)
                        existing_metric.avg_total_latency_ms = round(float(row.avg_total_latency_ms or 0), 2)
                        existing_metric.avg_ttft_ms = round(float(row.avg_ttft_ms or 0), 2)
                        existing_metric.avg_input_tokens = round(float(row.avg_input_tokens or 0), 2)
                        existing_metric.avg_output_tokens = round(float(row.avg_output_tokens or 0), 2)
                        existing_metric.total_input_tokens = int(row.total_input_tokens or 0)
                        existing_metric.total_output_tokens = int(row.total_output_tokens or 0)
                        existing_metric.avg_relevance_score = round(float(row.avg_relevance_score or 0), 4)
                        existing_metric.avg_chunks_retrieved = round(float(row.avg_chunks_retrieved or 0), 2)
                        existing_metric.avg_rating = round(float(feedback_row.avg_rating), 2) if feedback_row.avg_rating else None
                        existing_metric.thumbs_up_count = thumbs_up
                        existing_metric.thumbs_down_count = thumbs_down
                        existing_metric.thumbs_up_rate = round(thumbs_up_rate, 4)
                    else:
                        # 创建新记录
                        daily_metric = DailyMetrics(
                            date=date_to_aggregate,
                            collection_name=row.collection_name,
                            total_queries=row.total_queries or 0,
                            success_count=success_count,
                            success_rate=round(success_rate, 4),
                            avg_retrieval_time_ms=round(float(row.avg_retrieval_time_ms or 0), 2),
                            avg_generation_time_ms=round(float(row.avg_generation_time_ms or 0), 2),
                            avg_total_latency_ms=round(float(row.avg_total_latency_ms or 0), 2),
                            avg_ttft_ms=round(float(row.avg_ttft_ms or 0), 2),
                            avg_input_tokens=round(float(row.avg_input_tokens or 0), 2),
                            avg_output_tokens=round(float(row.avg_output_tokens or 0), 2),
                            total_input_tokens=int(row.total_input_tokens or 0),
                            total_output_tokens=int(row.total_output_tokens or 0),
                            avg_relevance_score=round(float(row.avg_relevance_score or 0), 4),
                            avg_chunks_retrieved=round(float(row.avg_chunks_retrieved or 0), 2),
                            avg_rating=round(float(feedback_row.avg_rating), 2) if feedback_row.avg_rating else None,
                            thumbs_up_count=thumbs_up,
                            thumbs_down_count=thumbs_down,
                            thumbs_up_rate=round(thumbs_up_rate, 4),
                        )
                        session.add(daily_metric)

                await session.commit()
                logger.info(f"成功聚合 {date_to_aggregate} 的指标数据")

            except Exception as e:
                await session.rollback()
                logger.error(f"聚合每日指标失败: {e}")
                raise


# 全局单例
metrics_collector = MetricsCollector()
