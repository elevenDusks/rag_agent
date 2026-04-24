"""认证 API 路由

提供用户注册、登录、OAuth2 认证等 API
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_active_user
from ..auth.oauth2 import (
    authenticate_user,
    create_access_token,
    create_user,
    get_user_by_email,
    get_user_by_oauth,
    get_user_by_username,
)
from ..db.mysql_client import get_db
from ..models.schemas import Token, UserCreate, UserResponse
from ..models.user import User


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    """用户注册"""
    if await get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    if await get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    user = await create_user(
        db,
        username=user_data.username,
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name
    )
    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """用户名密码登录"""
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id}
    )
    return Token(access_token=access_token)


@router.post("/login/oauth/{provider}", response_model=Token)
async def oauth_login(
    provider: str,
    code: str,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """OAuth2 登录/注册"""
    oauth_id = None

    if provider == "google":
        oauth_id = await _verify_google_token(code)
    elif provider == "github":
        oauth_id = await _verify_github_token(code)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: {provider}"
        )

    if oauth_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OAuth authentication failed"
        )

    user = await get_user_by_oauth(db, provider, oauth_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Please register first or link your OAuth account."
        )

    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id}
    )
    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: Annotated[User, Depends(get_current_active_user)]):
    """获取当前用户信息"""
    return current_user


async def _verify_google_token(code: str) -> str | None:
    """验证 Google OAuth token 并获取用户 ID"""
    # TODO: 实现 Google OAuth token 验证
    return None


async def _verify_github_token(code: str) -> str | None:
    """验证 GitHub OAuth token 并获取用户 ID"""
    # TODO: 实现 GitHub OAuth token 验证
    return None
