"""配置模块

该模块定义了应用的配置设置，包括 OpenAI API 配置、ChromaDB 配置、API 配置、RAG 配置和日志配置。
"""
from typing import ClassVar, Optional, List
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR: ClassVar[Path] = Path(__file__).resolve().parent.parent.parent.parent.parent  #
# print(BASE_DIR)
ENV_PATH = str(BASE_DIR / ".env")  # .env 文件绝对路径
# print(f"1. ENV_PATH: {ENV_PATH}")

class Settings(BaseSettings):
    """配置设置类
    
    定义应用的所有配置参数，支持从环境变量和 .env 文件中读取配置。
    """
    # EmbeddingModel模型
    EMBEDDING_MODEL: str = "EMBEDDING_MODEL" # 嵌入模型

    # OpenAI API 配置
    OPENAI_API_KEY: str = "OPENAI_API_KEY"  # OpenAI API 密钥
    OPENAI_BASE_URL: str = "OPENAI_BASE_URL" #OpenAI BASE URL
    OPENAI_MODEL: str = "OPENAI_MODEL"  # 使用的 OpenAI 模型
    
    # ChromaDB 配置
    CHROMA_NAME_JD: str = "CHROMA_NAME_JD"  # 京东帮助文档集合名称
    CHROMA_NAME_LAWS: str = "CHROMA_NAME_LAWS"  # 法律集合名称
    CHROMA_NAME_EXAMPLES: str = "CHROMA_NAME_EXAMPLES"  # 实例集合名称

    # ChromaDB 存储路径
    CHROMA_DB_PATH: str = str(BASE_DIR / "CHROMA_DB_PATH") # 向量数据库存储路径

    # CrossEncoder模型
    CROSS_ENCODER_NAME: str = "CROSS_ENCODER_NAME"
    # CrossEncoder模型存储路径
    CROSS_ENCODER_MODEL_PATH:str = "CROSS_ENCODER_MODEL_PATH"

    # 文档存储路径
    DOCUMENT_PATH_JD: str = str(BASE_DIR / "DOCUMENT_PATH_JD") # 京东帮助文档存储路径
    DOCUMENT_PATH_LAW: str = str(BASE_DIR / "DOCUMENT_PATH_LAW") # 法律文档存储路径
    DOCUMENT_PATH_EXAMPLES: str = str(BASE_DIR / "DOCUMENT_PATH_EXAMPLES") # 实例文档存储路径

    # Redis配置
    REDIS_HOST:str = "REDIS_HOST"
    REDIS_PORT:int = "REDIS_PORT"
    REDIS_PASSWORD:str = "REDIS_PASSWORD"
    REDIS_DB:int= "REDIS_DB"

    # Memory配置
    # Redis Key前缀
    CHAT_MEMORY_PREFIX:str = "CHAT_MEMORY_PREFIX"
    # 最大保留5轮对话
    CHAT_MEMORY_MAX_ROUNDS:int = "CHAT_MEMORY_MAX_ROUNDS"
    # 24小时过期
    CHAT_MEMORY_EXPIRE_SECONDS:int = "CHAT_MEMORY_EXPIRE_SECONDS"

    # MYSQL配置
    MYSQL_URL:str = "MYSQL_URL"
    MYSQL_POOL_SIZE:int = "MYSQL_POOL_SIZE"
    MYSQL_MAX_OVERFLOW:int = "MYSQL_MAX_OVERFLOW"

    # JWT配置
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # OAuth2配置
    GOOGLE_CLIENT_ID: Optional[str] = "GOOGLE_CLIENT_ID"
    GOOGLE_CLIENT_SECRET: Optional[str] = "GOOGLE_CLIENT_SECRET"
    GITHUB_CLIENT_ID: Optional[str] = "GITHUB_CLIENT_ID"
    GITHUB_CLIENT_SECRET: Optional[str] = "GITHUB_CLIENT_SECRET"

    # 密码哈希配置
    PASSWORD_CONTEXT_SCHEMES: List[str] = ["argon2"]


    # 日志配置
    LOG_LEVEL: str = "LOG_LEVEL"  # 日志级别

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,  # 环境变量文件路径
        case_sensitive=True,  # 环境变量大小写敏感
    )


# 创建配置实例
settings = Settings()

# print(f'1.OPENAI_API_KEY：{settings.OPENAI_API_KEY}')
# print(f'2.OPENAI_BASE_URL：{settings.OPENAI_BASE_URL}')
# print(f'3.OPENAI_MODEL：{settings.OPENAI_MODEL}')
#
# print(f'4.DOCUMENT_NAME_JD：{settings.CHROMA_NAME_JD}')
# print(f'5.DOCUMENT_NAME_LAWS：{settings.CHROMA_NAME_LAWS}')
# print(f'6.DOCUMENT_NAME_EXAMPLES：{settings.CHROMA_NAME_EXAMPLES}')
#
# print(f'7.CHROMA_DB_PATH：{settings.CHROMA_DB_PATH}')
#
# print(f'8.DOCUMENT_PATH_JD：{settings.DOCUMENT_PATH_JD}')
# print(f'9.CHROMA_NAME_LAWS：{settings.CHROMA_NAME_LAWS}')
# print(f'10.CHROMA_NAME_EXAMPLES：{settings.CHROMA_NAME_EXAMPLES}')
#
# print(f'11.LOG_LEVEL：{settings.LOG_LEVEL}')
# print(f'12.EMBEDDING_MODEL：{settings.EMBEDDING_MODEL}')






