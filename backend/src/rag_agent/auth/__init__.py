"""认证模块

提供 OAuth2 认证、用户管理、JWT 令牌等功能
"""
from .oauth2 import (
    authenticate_user,
    create_access_token,
    create_user,
    decode_token,
    get_password_hash,
    get_user,
    get_user_by_email,
    get_user_by_oauth,
    get_user_by_username,
    verify_password,
)
from .dependencies import (
    CurrentActiveUser,
    CurrentSuperUser,
    CurrentUser,
    get_current_active_user,
    get_current_superuser,
    get_current_user,
)

__all__ = [
    "authenticate_user",
    "create_access_token",
    "create_user",
    "decode_token",
    "get_password_hash",
    "get_user",
    "get_user_by_email",
    "get_user_by_oauth",
    "get_user_by_username",
    "verify_password",
    "CurrentActiveUser",
    "CurrentSuperUser",
    "CurrentUser",
    "get_current_active_user",
    "get_current_superuser",
    "get_current_user",
]
