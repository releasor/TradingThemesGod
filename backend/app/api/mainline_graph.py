"""主线图谱 API。"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, get_optional_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.mainline_graph import (
    MainlineGraphAcceptEdgeRequest,
    MainlineGraphCreateDraftRequest,
    MainlineGraphEdgeItem,
    MainlineGraphEnsureRequest,
    MainlineGraphEnsureResponse,
    MainlineGraphPatchEdgesRequest,
    MainlineGraphThemeConceptResponse,
    MainlineGraphVersionListResponse,
    MainlineGraphVersionMeta,
    MainlineGraphViewResponse,
)
from app.services.mainline_graph import MainlineGraphService

router = APIRouter(prefix="/mainline-graph", tags=["mainline-graph"])


@router.get("/view", response_model=MainlineGraphViewResponse)
async def get_mainline_graph_view(
    trade_date: date | None = Query(None, description="交易日"),
    version_id: int | None = Query(None, description="指定版本"),
    db: AsyncSession = Depends(get_db),
):
    """读取叙事图：优先 published，否则 auto。"""
    return await MainlineGraphService(db).view(trade_date, version_id)


@router.get("/versions", response_model=MainlineGraphVersionListResponse)
async def list_mainline_graph_versions(
    trade_date: date | None = Query(None, description="交易日"),
    db: AsyncSession = Depends(get_db),
):
    """按日列出版本。"""
    return await MainlineGraphService(db).list_versions(trade_date)


@router.post("/ensure", response_model=MainlineGraphEnsureResponse)
async def ensure_mainline_graph(
    payload: MainlineGraphEnsureRequest | None = None,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    """规则生成/刷新当日 auto 版本；可选排队模型建议边。"""
    body = payload or MainlineGraphEnsureRequest()
    user_id = user.id if user else None
    return await MainlineGraphService(db).ensure(
        body.trade_date,
        use_model=body.use_model,
        user_id=user_id,
    )


@router.post("/versions", response_model=MainlineGraphVersionMeta)
async def create_mainline_graph_draft(
    payload: MainlineGraphCreateDraftRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """从 auto/published 克隆 draft。"""
    return await MainlineGraphService(db).create_draft(current_user.id, payload)


@router.patch(
    "/versions/{version_id}/edges",
    response_model=MainlineGraphViewResponse,
)
async def patch_mainline_graph_edges(
    version_id: int,
    payload: MainlineGraphPatchEdgesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """草稿上 upsert/delete 边。"""
    return await MainlineGraphService(db).patch_edges(
        version_id, current_user.id, payload
    )


@router.post(
    "/versions/{version_id}/publish",
    response_model=MainlineGraphVersionMeta,
)
async def publish_mainline_graph_version(
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """draft → published（归档旧 published）。"""
    _ = current_user
    return await MainlineGraphService(db).publish(version_id)


@router.post("/edges/{edge_id}/accept", response_model=MainlineGraphEdgeItem)
async def accept_mainline_graph_edge(
    edge_id: int,
    payload: MainlineGraphAcceptEdgeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """采纳 suggested 边到指定 draft。"""
    return await MainlineGraphService(db).accept_edge(
        edge_id, current_user.id, payload
    )


@router.get(
    "/themes/{theme_id}/concept",
    response_model=MainlineGraphThemeConceptResponse,
)
async def get_mainline_graph_theme_concept(
    theme_id: int,
    trade_date: date | None = Query(None, description="交易日"),
    db: AsyncSession = Depends(get_db),
):
    """题材概念树 + 当日阶段/强度摘要。"""
    return await MainlineGraphService(db).get_theme_concept(theme_id, trade_date)
