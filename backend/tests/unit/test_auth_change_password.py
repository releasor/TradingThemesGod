"""修改密码相关单元测试。"""

import pytest
from fastapi import HTTPException

from app.core.auth import hash_password, verify_password
from app.schemas.auth import ChangePasswordRequest
from app.services.auth import AuthService


class _FakeUser:
    def __init__(self, password: str):
        self.password_hash = hash_password(password)


class _FakeSession:
    def __init__(self):
        self.committed = False

    async def commit(self):
        self.committed = True


@pytest.mark.asyncio
async def test_change_password_success():
    user = _FakeUser("oldpass1")
    session = _FakeSession()
    service = AuthService(session)  # type: ignore[arg-type]
    await service.change_password(
        user,  # type: ignore[arg-type]
        ChangePasswordRequest(current_password="oldpass1", new_password="newpass1"),
    )
    assert session.committed is True
    assert verify_password("newpass1", user.password_hash)


@pytest.mark.asyncio
async def test_change_password_rejects_wrong_current():
    user = _FakeUser("oldpass1")
    service = AuthService(_FakeSession())  # type: ignore[arg-type]
    with pytest.raises(HTTPException) as exc:
        await service.change_password(
            user,  # type: ignore[arg-type]
            ChangePasswordRequest(current_password="wrong", new_password="newpass1"),
        )
    assert exc.value.status_code == 400
    assert "当前密码不正确" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_change_password_rejects_same_password():
    user = _FakeUser("samepass")
    service = AuthService(_FakeSession())  # type: ignore[arg-type]
    with pytest.raises(HTTPException) as exc:
        await service.change_password(
            user,  # type: ignore[arg-type]
            ChangePasswordRequest(current_password="samepass", new_password="samepass"),
        )
    assert exc.value.status_code == 400
