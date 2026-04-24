"""OAuth2 认证服务

提供用户认证、Token 生成、JWT 令牌验证等功能
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.security import verify_password, get_password_hash
from ..models.schemas import TokenData
from ..models.user import User


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT access token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[TokenData]:
    """解码 JWT token"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        if username is None:
            return None
        return TokenData(username=username, user_id=user_id)
    except JWTError:
        return None


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
    """验证用户名密码"""
    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        return None
    if user.hashed_password is None:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """根据用户名获取用户"""
    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """根据邮箱获取用户"""
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_oauth(db: AsyncSession, provider: str, oauth_id: str) -> Optional[User]:
    """根据 OAuth 提供商和 ID 获取用户"""
    stmt = select(User).where(
        User.oauth_provider == provider,
        User.oauth_id == oauth_id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    username: str,
    email: str,
    password: Optional[str] = None,
    full_name: Optional[str] = None,
    oauth_provider: Optional[str] = None,
    oauth_id: Optional[str] = None
) -> User:
    """创建新用户"""
    hashed_password = get_password_hash(password) if password else None
    user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
        oauth_provider=oauth_provider,
        oauth_id=oauth_id
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user(db: AsyncSession, user_id: int) -> Optional[User]:
    """根据 ID 获取用户"""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
