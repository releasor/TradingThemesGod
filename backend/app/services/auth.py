"""用户注册与登录服务。"""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _response(self, user: User) -> UserResponse:
        return UserResponse(
            id=user.id,
            username=user.username,
            created_at=user.created_at,
        )

    async def register(self, payload: RegisterRequest) -> TokenResponse:
        user = User(
            username=payload.username,
            password_hash=hash_password(payload.password),
        )
        self.session.add(user)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise HTTPException(status.HTTP_409_CONFLICT, "用户名已存在") from exc
        await self.session.refresh(user)
        return TokenResponse(
            access_token=create_access_token(user_id=user.id, username=user.username)
        )

    async def login(self, payload: LoginRequest) -> TokenResponse:
        user = await self.session.scalar(
            select(User).where(User.username == payload.username)
        )
        if user is None or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户名或密码错误")
        return TokenResponse(
            access_token=create_access_token(user_id=user.id, username=user.username)
        )

    async def me(self, user: User) -> UserResponse:
        return self._response(user)
