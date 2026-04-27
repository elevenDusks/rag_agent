"""应用主入口模块

该模块是应用的主入口，负责初始化 FastAPI 应用、配置 CORS、包含路由以及定义根路径和健康检查端点。
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import chat, auth, agent, metrics
from .middleware.metrics import metrics_collector
from .db.mysql_client import create_tables, async_engine, AsyncSessionLocal
from .models.user import User
from .models.metrics import RAGQueryLog, UserFeedback, DailyMetrics  # noqa: F401 - 注册模型
from .core.security import get_password_hash
from sqlalchemy import select
from .core.logger import logger


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    # 创建数据库表
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

    # 启动指标采集器
    await metrics_collector.start()

    yield

    # 停止指标采集器
    await metrics_collector.stop()

    # 关闭数据库连接
    await async_engine.dispose()
    logger.info("数据库连接已关闭")

# 创建 FastAPI 应用实例
app = FastAPI(
    title="My RAG Agent API",  # API 标题
    description="A RAG (Retrieval-Augmented Generation) agent API",  # API 描述
    version="1.0.0",  # API 版本
    lifespan=app_lifespan  # 生命周期管理
)

# 配置 CORS（跨域资源共享）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,  # 允许携带凭证
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有 HTTP 头
)

# 包含路由
app.include_router(chat.router)  # 聊天相关路由
app.include_router(auth.router)
app.include_router(agent.router)  # Agent 相关路由
app.include_router(metrics.router)  # 指标相关路由

@app.get("/")
async def root():
    """根路径
    
    返回 API 基本信息。
    """
    return {"message": "My RAG Agent API"}

@app.get("/health")
async def health_check():
    """健康检查端点
    
    用于检查 API 是否正常运行。
    """
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.src.rag_agent.main:app",
        host="0.0.0.0",
        port=5001,
        reload=True
    )
