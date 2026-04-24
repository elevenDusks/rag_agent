from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select
from contextlib import asynccontextmanager

from ..core.config import settings
from ..models.user import User  # noqa: F401 - 需要导入以注册模型
from ..db.base import Base
from ..core.logger import logger
from ..core.security import get_password_hash

# 创建数据库引擎
async_engine = create_async_engine(
    settings.MYSQL_URL,
    pool_size = settings.MYSQL_POOL_SIZE,
    max_overflow=10,
    pool_recycle=3600
)

# 创建数据库表
async def create_tables():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行（原来的 startup）
    await create_tables()
    logger.info("数据库表初始化完成")

    # 创建默认管理员账号
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.username == "admin")
        result = await session.execute(stmt)
        existing_admin = result.scalar_one_or_none()
        if not existing_admin:
            admin = User(
                username="admin",
                email="admin@example.com",
                hashed_password=get_password_hash("admin123"),
                full_name="Administrator",
                is_superuser=True,
                is_active=True,
            )
            session.add(admin)
            await session.commit()
            logger.info("默认管理员账号已创建: admin / admin123")
        else:
            logger.info("管理员账号已存在")

    yield  # 程序运行中

    # 关闭时执行（原来的 shutdown）
    await async_engine.dispose()
    logger.info("数据库连接已关闭")

# 创建会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
    class_=AsyncSession
)


# 依赖函数：获取数据库会话
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

