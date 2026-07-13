"""爬虫 API 端点

提供爬虫运行触发、状态查询和历史记录查询。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.scraper_run import ScraperRunRepository
from app.schemas.scraper import (
    ScraperRunRequest,
    ScraperRunResponse,
    ScraperRunListResponse,
)
from app.scrapers.scheduler import scraper_scheduler

router = APIRouter(prefix="/scraper", tags=["scraper"])


@router.post("/run/{source}", response_model=ScraperRunResponse)
async def run_scraper(
    source: str,
    request: ScraperRunRequest = ScraperRunRequest(),
    db: AsyncSession = Depends(get_db),
):
    """触发爬虫运行

    Args:
        source: 数据源名称（如 eastmoney）
        request: 运行请求参数

    Returns:
        运行记录信息
    """
    try:
        run_id = await scraper_scheduler.run(source, params=request.params)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

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
    source: str | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """列出爬虫运行记录

    Args:
        source: 按数据源筛选（可选）
        limit: 返回数量限制

    Returns:
        运行记录列表
    """
    repo = ScraperRunRepository(db)
    runs = await repo.list_by_source(source=source, limit=limit)

    return ScraperRunListResponse(
        runs=[ScraperRunResponse.model_validate(r) for r in runs],
        total=len(runs),
    )
