"""Tushare 全局配置服务：DB 优先、env 回退、进程内缓存。"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.tushare_settings import TushareSettings
from app.schemas.tushare_settings import (
    TushareSettingsResponse,
    TushareSettingsUpdate,
    TushareTestResponse,
)
from app.services.secret_store import SecretStore

logger = get_logger(__name__)

SINGLETON_ID = 1


@dataclass(frozen=True)
class TushareRuntime:
    enabled: bool
    token: str
    from_db: bool

    @property
    def ready(self) -> bool:
        return bool(self.enabled) and bool((self.token or "").strip())


_cache: TushareRuntime | None = None


def _runtime_from_env() -> TushareRuntime:
    settings = get_settings()
    return TushareRuntime(
        enabled=bool(settings.TUSHARE_ENABLED),
        token=(settings.TUSHARE_TOKEN or "").strip(),
        from_db=False,
    )


def get_cached_tushare_runtime() -> TushareRuntime:
    """同步读取缓存；未预热时回退 env。"""
    if _cache is not None:
        return _cache
    return _runtime_from_env()


def set_cached_tushare_runtime(runtime: TushareRuntime) -> None:
    global _cache
    _cache = runtime


def clear_tushare_runtime_cache() -> None:
    global _cache
    _cache = None


class TushareSettingsService:
    def __init__(
        self,
        db: AsyncSession,
        *,
        secrets: SecretStore | None = None,
    ):
        self.db = db
        self.secrets = secrets or SecretStore()

    async def _get_row(self) -> TushareSettings | None:
        result = await self.db.execute(
            select(TushareSettings).where(TushareSettings.id == SINGLETON_ID)
        )
        return result.scalar_one_or_none()

    async def ensure_row(self) -> TushareSettings:
        row = await self._get_row()
        if row is not None:
            return row
        row = TushareSettings(id=SINGLETON_ID, enabled=False, token_encrypted=None)
        self.db.add(row)
        await self.db.flush()
        return row

    async def resolve_runtime(self) -> TushareRuntime:
        row = await self._get_row()
        if row is None:
            runtime = _runtime_from_env()
            set_cached_tushare_runtime(runtime)
            return runtime

        token = ""
        if row.token_encrypted:
            try:
                token = self.secrets.decrypt(row.token_encrypted)
            except ValueError:
                logger.warning("tushare_token_decrypt_failed")
                token = ""

        runtime = TushareRuntime(
            enabled=bool(row.enabled),
            token=(token or "").strip(),
            from_db=True,
        )
        set_cached_tushare_runtime(runtime)
        return runtime

    async def get_response(self) -> TushareSettingsResponse:
        row = await self.ensure_row()
        await self.resolve_runtime()
        return TushareSettingsResponse(
            enabled=bool(row.enabled),
            has_token=bool((row.token_encrypted or "").strip()),
            updated_at=row.updated_at,
        )

    async def save(
        self,
        payload: TushareSettingsUpdate,
        *,
        user_id: int | None = None,
    ) -> TushareSettingsResponse:
        row = await self.ensure_row()
        row.enabled = bool(payload.enabled)
        if payload.token is not None and payload.token.strip():
            row.token_encrypted = self.secrets.encrypt(payload.token.strip())
        row.updated_by = user_id
        row.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.resolve_runtime()
        return TushareSettingsResponse(
            enabled=bool(row.enabled),
            has_token=bool((row.token_encrypted or "").strip()),
            updated_at=row.updated_at,
        )

    async def test_connection(
        self,
        *,
        token_override: str | None = None,
    ) -> TushareTestResponse:
        runtime = await self.resolve_runtime()
        token = (token_override or "").strip() or runtime.token
        if not token:
            return TushareTestResponse(success=False, message="未配置 Token，无法测试")

        settings = get_settings()
        api_url = (settings.TUSHARE_API_URL or "").strip()
        # 按「题材采集相关 → 通用基础」顺序探活；积分不足时 trade_cal 常无权限
        concept_src = (settings.TUSHARE_CONCEPT_SRC or "ts").strip() or "ts"
        ths_type = (settings.TUSHARE_THS_INDEX_TYPE or "N").strip() or "N"
        ths_exchange = (settings.TUSHARE_THS_INDEX_EXCHANGE or "A").strip() or "A"

        def _probe() -> TushareTestResponse:
            import tushare as ts

            pro = ts.pro_api(token, http_url=api_url) if api_url else ts.pro_api(token)
            attempts: list[tuple[str, Callable[[], object]]] = [
                ("concept", lambda: pro.concept(src=concept_src)),
                (
                    "ths_index",
                    lambda: pro.ths_index(exchange=ths_exchange, type=ths_type),
                ),
                ("dc_index", lambda: pro.dc_index()),
                (
                    "trade_cal",
                    lambda: pro.trade_cal(
                        exchange="SSE", start_date="20260101", end_date="20260105"
                    ),
                ),
                ("stock_basic", lambda: pro.stock_basic(list_status="L", fields="ts_code")),
            ]

            errors: list[str] = []
            permission_hits = 0
            for name, call in attempts:
                try:
                    frame = call()
                    rows = 0 if frame is None else len(frame)
                    if frame is None or getattr(frame, "empty", True):
                        errors.append(f"{name}: 空结果")
                        continue
                    return TushareTestResponse(
                        success=True,
                        message=f"连接成功（{name} 返回 {rows} 行，可用于题材采集）",
                    )
                except Exception as exc:  # noqa: BLE001
                    text = str(exc).strip() or type(exc).__name__
                    lower = text.lower()
                    if (
                        "权限" in text
                        or "permission" in lower
                        or "积分" in text
                        or "40203" in text
                        or "access" in lower
                    ):
                        permission_hits += 1
                    if "token" in lower and ("不对" in text or "invalid" in lower):
                        return TushareTestResponse(
                            success=False,
                            message=f"连接失败：Token 无效（{text[:160]}）",
                        )
                    errors.append(f"{name}: {text[:120]}")

            if permission_hits >= max(1, len(attempts) - 1):
                return TushareTestResponse(
                    success=False,
                    message=(
                        "Token 可识别，但当前积分/套餐无权访问题材相关接口"
                        "（concept / ths_index / dc_index 等）。"
                        "请到 tushare.pro 提升积分或开通权限后再测。"
                    ),
                )
            detail = "；".join(errors[:3])
            if len(detail) > 220:
                detail = detail[:219] + "…"
            return TushareTestResponse(
                success=False,
                message=f"连接失败：已尝试 {len(attempts)} 个接口均不可用。{detail}",
            )

        return await asyncio.to_thread(_probe)


async def warm_tushare_runtime_cache() -> None:
    """应用启动时预热缓存。"""
    from app.core.database import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as session:
            await TushareSettingsService(session).resolve_runtime()
            await session.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("tushare_runtime_cache_warm_failed", error=str(exc))
        set_cached_tushare_runtime(_runtime_from_env())
