"""RAG 量化指标数据模型

该模块定义了 RAG 查询日志、用户反馈和每日聚合指标的数据库模型。
"""
from datetime import datetime, date
from sqlalchemy import String, Integer, BigInteger, Float, Boolean, Text, Date, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base


class RAGQueryLog(Base):
    """RAG 查询日志表

    记录每次 RAG 查询的详细指标数据，包括检索指标、生成指标和端到端指标。
    """
    __tablename__ = "rag_query_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    collection_name: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # 检索指标
    retrieval_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    chunks_retrieved: Mapped[int] = mapped_column(Integer, default=0)
    avg_relevance_score: Mapped[float] = mapped_column(Float, default=0.0)

    # 生成指标
    generation_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    response_length: Mapped[int] = mapped_column(Integer, default=0)

    # 端到端指标
    total_latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    ttft_ms: Mapped[int] = mapped_column(Integer, default=0)  # Time to First Token
    is_success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 响应内容 (可选，用于调试)
    response: Mapped[str | None] = mapped_column(Text, nullable=True)
    references_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 序列化的引用

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_created_at", "created_at"),
        Index("idx_collection_name", "collection_name"),
    )

    def __repr__(self) -> str:
        return f"<RAGQueryLog(id={self.id}, query='{self.query[:50]}...', success={self.is_success})>"


class UserFeedback(Base):
    """用户反馈表

    记录用户对 RAG 回答的反馈，包括评分和文字评价。
    """
    __tablename__ = "user_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query_log_id: Mapped[int] = mapped_column(Integer, ForeignKey("rag_query_logs.id"), nullable=False)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5 分
    thumbs_up: Mapped[bool] = mapped_column(Boolean, default=False)
    thumbs_down: Mapped[bool] = mapped_column(Boolean, default=False)
    feedback_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_query_log_id", "query_log_id"),
    )

    def __repr__(self) -> str:
        return f"<UserFeedback(id={self.id}, rating={self.rating}, thumbs_up={self.thumbs_up})>"


class DailyMetrics(Base):
    """每日统计指标表

    预聚合的每日指标数据，用于快速查询和趋势分析。
    """
    __tablename__ = "daily_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    collection_name: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # 聚合指标
    total_queries: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    success_rate: Mapped[float] = mapped_column(Float, default=0.0)

    # 性能指标
    avg_retrieval_time_ms: Mapped[float] = mapped_column(Float, default=0.0)
    avg_generation_time_ms: Mapped[float] = mapped_column(Float, default=0.0)
    avg_total_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    avg_ttft_ms: Mapped[float] = mapped_column(Float, default=0.0)

    # Token 指标
    avg_input_tokens: Mapped[float] = mapped_column(Float, default=0.0)
    avg_output_tokens: Mapped[float] = mapped_column(Float, default=0.0)
    total_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_output_tokens: Mapped[int] = mapped_column(Integer, default=0)

    # 检索指标
    avg_relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    avg_chunks_retrieved: Mapped[float] = mapped_column(Float, default=0.0)

    # 用户反馈聚合
    avg_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    thumbs_up_count: Mapped[int] = mapped_column(Integer, default=0)
    thumbs_down_count: Mapped[int] = mapped_column(Integer, default=0)
    thumbs_up_rate: Mapped[float] = mapped_column(Float, default=0.0)

    # LLM 质量评估
    avg_quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("date", "collection_name", name="uix_date_collection"),
    )

    def __repr__(self) -> str:
        return f"<DailyMetrics(date={self.date}, collection={self.collection_name}, queries={self.total_queries})>"
