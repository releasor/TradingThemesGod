"""数据源集成配置 API（Tushare 等）。"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.tushare_settings import (
    TushareSettingsResponse,
    TushareSettingsUpdate,
    TushareTestRequest,
    TushareTestResponse,
)
from app.services.tushare_settings import TushareSettingsService

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/tushare", response_model=TushareSettingsResponse)
async def get_tushare_settings(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    return await TushareSettingsService(db).get_response()


@router.put("/tushare", response_model=TushareSettingsResponse)
async def update_tushare_settings(
    payload: TushareSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = TushareSettingsService(db)
    result = await service.save(payload, user_id=current_user.id)
    await db.commit()
    return result


@router.post("/tushare/test", response_model=TushareTestResponse)
async def test_tushare_settings(
    payload: TushareTestRequest | None = None,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    body = payload or TushareTestRequest()
    return await TushareSettingsService(db).test_connection(token_override=body.token)
