"""题材挖掘 API。"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, get_optional_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.mining import (
    MiningBoardResponse,
    MiningCardItem,
    MiningEnsureResponse,
    MiningNoteResponse,
)
from app.services.mining import MiningService

router = APIRouter(prefix="/mining", tags=["mining"])


@router.get("/board", response_model=MiningBoardResponse)
async def get_mining_board(
    trade_date: date | None = Query(None, description="交易日"),
    db: AsyncSession = Depends(get_db),
):
    """三列题材挖掘看板。"""
    return await MiningService(db).get_board(trade_date)


@router.get("/cards/{card_id}", response_model=MiningCardItem)
async def get_mining_card(
    card_id: int,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    """挖掘卡详情（含全部 members；登录用户附带 note）。"""
    user_id = user.id if user else None
    return await MiningService(db).get_card(card_id, user_id=user_id)


@router.post("/ensure", response_model=MiningEnsureResponse)
async def ensure_mining(
    trade_date: date | None = Query(None, description="交易日"),
    db: AsyncSession = Depends(get_db),
):
    """幂等重算指定交易日题材挖掘快照。"""
    return await MiningService(db).ensure(trade_date)


@router.post("/cards/{card_id}/note/ensure", response_model=MiningNoteResponse)
async def ensure_mining_note(
    card_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """确保点评存在：标记 pending 并后台生成，请求路径不调用 LLM。"""
    return await MiningService(db).ensure_note(card_id, current_user.id)
