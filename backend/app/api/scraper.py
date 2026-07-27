"""爬虫 API 端点

提供爬虫运行触发、状态查询和历史记录查询。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domain.scraper_sources import list_registered_scraper_sources
from app.repositories.scraper_run import ScraperRunRepository
from app.schemas.scraper import (
    ScraperRunRequest,
    ScraperRunResponse,
    ScraperRunListResponse,
    ScraperSourceListResponse,
    ScraperSourceResponse,
    ThemeQuotesRefreshResponse,
)
from app.scrapers.eastmoney import EastMoneyScraper
from app.scrapers.scheduler import scraper_scheduler
from datetime import datetime, timezone

# 速率限制器
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/scraper", tags=["scraper"])


@router.get("/sources", response_model=ScraperSourceListResponse)
async def list_scraper_sources(
    dashboard_only: bool = Query(default=False, description="仅返回看板可选数据源"),
):
    """列出已注册的爬虫数据源及说明。"""
    sources = list_registered_scraper_sources(dashboard_only=dashboard_only)
    payload = [
        ScraperSourceResponse(
            id=item.id,
            label=item.label,
            description=item.description,
            dashboard_selectable=item.dashboard_selectable,
            is_default=item.is_default,
        )
        for item in sources
    ]
    return ScraperSourceListResponse(sources=payload, count=len(payload))


@router.post("/run/{source}", response_model=ScraperRunResponse)
@limiter.limit("5/minute")  # 每分钟最多 5 次请求
async def run_scraper(
    request: Request,
    source: str,
    body: ScraperRunRequest = ScraperRunRequest(),
    db: AsyncSession = Depends(get_db),
):
    """触发爬虫运行

    Args:
        request: FastAPI 请求对象（用于速率限制）
        source: 数据源名称（如 eastmoney）
        body: 运行请求参数

    Returns:
        运行记录信息
    """
    try:
        run_id = await scraper_scheduler.run(source, params=body.params)
    except ValueError as e:
        detail = str(e)
        status_code = 409 if "正在运行中" in detail else 404
        raise HTTPException(status_code=status_code, detail=detail)

    # 查询刚创建的记录
    repo = ScraperRunRepository(db)
    run = await repo.get(run_id)
    if run is None:
        raise HTTPException(status_code=500, detail="创建运行记录失败")

    return ScraperRunResponse.model_validate(run)


@router.get("/status/{run_id}", response_model=ScraperRunResponse)
async def get_scraper_status(
    run_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取爬虫运行状态

    Args:
        run_id: 运行记录 ID

    Returns:
        运行记录信息
    """
    repo = ScraperRunRepository(db)
    run = await repo.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="运行记录不存在")

    return ScraperRunResponse.model_validate(run)


@router.get("/runs", response_model=ScraperRunListResponse)
async def list_scraper_runs(
    source: str | None = Query(default=None, description="按数据源筛选"),
    status: str | None = Query(default=None, description="按状态筛选"),
    limit: int = Query(default=20, ge=1, le=100, description="返回数量限制"),
    db: AsyncSession = Depends(get_db),
):
    """列出爬虫运行记录

    Args:
        source: 按数据源筛选（可选）
        status: 按状态筛选（可选）
        limit: 返回数量限制

    Returns:
        运行记录列表
    """
    repo = ScraperRunRepository(db)
    await repo.fail_stale_running()
    await db.commit()
    runs = await repo.list_by_source(source=source, limit=limit, status=status)

    return ScraperRunListResponse(
        runs=[ScraperRunResponse.model_validate(r) for r in runs],
        count=len(runs),
    )


@router.post("/refresh-quotes", response_model=ThemeQuotesRefreshResponse)
@limiter.limit("10/minute")
async def refresh_theme_quotes(request: Request):
    """仅刷新题材列表涨跌幅/热度，不抓取成分股。

    与全量 eastmoney 采集解耦：全量进行中仍可刷新行情。
    """
    if scraper_scheduler.is_quotes_refresh_running():
        raise HTTPException(status_code=409, detail="行情刷新进行中，请稍后再试")

    async with scraper_scheduler.quotes_refresh_lock:
        scraper = EastMoneyScraper()
        try:
            trade_date, themes_updated = await scraper.refresh_theme_quotes()
        except Exception as exc:
            raise HTTPException(
                status_code=502, detail=f"题材行情刷新失败：{exc}"
            ) from exc
        finally:
            await scraper.close()

    return ThemeQuotesRefreshResponse(
        trade_date=trade_date,
        themes_updated=themes_updated,
        refreshed_at=datetime.now(timezone.utc),
    )
