from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime


class Base(DeclarativeBase):
    create_time: Mapped[datetime] = mapped_column(
        DateTime, insert_default=func.now(), onupdate=None, default=None
    )
    updatate_time: Mapped[datetime] = mapped_column(
        DateTime, insert_default=func.now(), onupdate=func.now()
    )
