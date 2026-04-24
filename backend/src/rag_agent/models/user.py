"""用户认证数据模型"""
from sqlalchemy import String, Boolean, Integer, DateTime
from sqlalchemy.orm import mapped_column, Mapped
from datetime import datetime

from ..db.base import Base


class User(Base):
    """用户表模型

    Attributes:
        id: 用户ID
        username: 用户名（唯一）
        email: 邮箱（唯一）
        hashed_password: 哈希密码
        full_name: 姓名
        is_active: 是否激活
        is_superuser: 是否超级用户
        oauth_provider: OAuth 提供商（如 google, github）
        oauth_id: OAuth 第三方 ID
        create_time: 创建时间
        updatate_time: 更新时间
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)

    # OAuth 字段
    oauth_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    oauth_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # 时间戳字段
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updatate_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
