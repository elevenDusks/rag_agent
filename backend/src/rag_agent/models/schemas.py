"""数据模型模块

该模块定义了应用中使用的数据模型，包括聊天、搜索、用户和文档相关的模型。
"""
from pydantic import BaseModel, EmailStr
from typing import List, Optional


# ============ 用户相关模型 ============

class UserBase(BaseModel):
    """用户基础模型"""
    username: str
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """用户创建模型"""
    password: str


class UserUpdate(BaseModel):
    """用户更新模型"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None


class UserInDB(UserBase):
    """数据库中的用户模型"""
    id: int
    hashed_password: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False
    oauth_provider: Optional[str] = None
    oauth_id: Optional[str] = None

    class Config:
        from_attributes = True


class UserResponse(UserBase):
    """用户响应模型"""
    id: int
    is_active: bool
    is_superuser: bool

    class Config:
        from_attributes = True


# ============ 认证相关模型 ============

class Token(BaseModel):
    """JWT Token 响应模型"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token 中的数据"""
    username: Optional[str] = None
    user_id: Optional[int] = None


class LoginRequest(BaseModel):
    """登录请求模型"""
    username: str
    password: str


# ============ 聊天相关模型 ============


class ChatRequest(BaseModel):
    """聊天请求模型

    Attributes:
        message: 用户发送的消息
        session_id: 会话ID，用于保持上下文一致性
        context: 可选的上下文信息列表
    """
    message: str
    session_id: Optional[str] = None
    context: Optional[List[str]] = None

class ChatMessage(BaseModel):
    """聊天消息模型
    
    Attributes:
        role: 消息角色，如 "user" 或 "assistant"
        content: 消息内容
    """
    role: str
    content: str

class ChatResponse(BaseModel):
    """聊天响应模型
    
    Attributes:
        message: 生成的回答消息
        session_id: 会话ID
    """
    message: str
    session_id: str


class SearchResult(BaseModel):
    """搜索结果模型
    
    Attributes:
        id: 文档ID
        content: 文档内容
        score: 相关性得分
    """
    id: str
    content: str
    score: float

class SearchResponse(BaseModel):
    """搜索响应模型
    
    Attributes:
        results: 搜索结果列表
    """
    results: List[SearchResult]

class DocumentResponse(BaseModel):
    """文档响应模型
    
    Attributes:
        message: 操作结果消息
        document_ids: 导入的文档ID列表
    """
    message: str
    document_ids: List[str]
