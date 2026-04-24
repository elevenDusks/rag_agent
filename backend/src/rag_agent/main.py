"""应用主入口模块

该模块是应用的主入口，负责初始化 FastAPI 应用、配置 CORS、包含路由以及定义根路径和健康检查端点。
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import chat, auth

# 创建 FastAPI 应用实例
app = FastAPI(
    title="My RAG Agent API",  # API 标题
    description="A RAG (Retrieval-Augmented Generation) agent API",  # API 描述
    version="1.0.0"  # API 版本
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
    """应用入口点
    
    当直接运行该文件时，启动 uvicorn 服务器。
    """
    import uvicorn
    uvicorn.run(
        "src.rag_agent.main:app",  # 应用路径
        host="0.0.0.0",  # 主机地址
        port=8000,  # 端口
        reload=True  # 开发模式下自动重载
    )
