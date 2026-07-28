"""Tushare Pro 题材爬虫

全量竞速：collect_full 拉取概念板块列表（themes-only），commit_full 落库题材。
接口与 token 均从 Settings 读取（见 TUSHARE_* 环境变量）。
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Any

import tushare as ts
from sqlalchemy import select

from app.core.config import Settings, get_settings
from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.models.theme import Theme
from app.scrapers.anti_scraping import AntiScrapingMiddleware
from app.scrapers.base import BaseScraper
from app.scrapers.draft_types import FullScrapeDraft

logger = get_logger(__name__)

SUPPORTED_CONCEPT_APIS = frozenset({"concept", "ths_index", "dc_index"})


class TushareScraper(BaseScraper):
    """Tushare Pro 概念题材爬虫（全量竞速兜底）。"""

    source_name = "tushare"

    def __init__(self, middleware: AntiScrapingMiddleware | None = None):
        super().__init__(middleware)

    def parse(self, data: Any) -> list[dict[str, Any]]:
        """兼容基类；全量路径走 _parse_concept_themes。"""
        return []

    async def save(self, data: list[dict[str, Any]]) -> int:
        if not data:
            return 0
        return await self._save_themes(data)

    def _settings(self) -> Settings:
        return get_settings()

    def _require_token(self) -> str:
        settings = self._settings()
        if not settings.TUSHARE_ENABLED:
            raise RuntimeError("Tushare 未启用（请设置 TUSHARE_ENABLED=true）")
        token = (settings.TUSHARE_TOKEN or "").strip()
        if not token:
            raise RuntimeError("未配置 TUSHARE_TOKEN，无法使用 Tushare 数据源")
        return token

    def _pro_api(self) -> Any:
        settings = self._settings()
        token = self._require_token()
        api_url = (settings.TUSHARE_API_URL or "").strip()
        if api_url:
            return ts.pro_api(token, http_url=api_url)
        return ts.pro_api(token)

    @staticmethod
    def _normalize_concept_code(code: Any) -> str:
        value = str(code or "").strip().upper()
        if not value:
            return ""
        if value.startswith("TS"):
            return value
        # 去掉交易所后缀，如 885800.TI → 885800
        if "." in value:
            value = value.split(".", 1)[0]
        return f"TS{value}"

    def _parse_concept_themes(self, frame: Any, *, api_name: str) -> list[dict[str, Any]]:
        themes: list[dict[str, Any]] = []
        if frame is None or getattr(frame, "empty", True):
            return themes

        columns = {str(c) for c in getattr(frame, "columns", [])}
        code_column = next(
            (c for c in ("code", "ts_code", "概念代码", "板块代码") if c in columns),
            None,
        )
        name_column = next(
            (c for c in ("name", "概念名称", "板块名称") if c in columns),
            None,
        )
        if code_column is None or name_column is None:
            logger.warning(
                f"[{self.source_name}] {api_name} 缺少 code/name 列: {sorted(columns)}"
            )
            return themes

        for _, row in frame.iterrows():
            code = self._normalize_concept_code(row.get(code_column))
            name = str(row.get(name_column, "")).strip()
            if not code or not name:
                continue
            themes.append(
                {
                    "name": name,
                    "code": code,
                    "heat_index": None,
                    "rise_fall_pct": None,
                    "stock_count": None,
                    "category": None,
                    "source": self.source_name,
                }
            )
        return themes

    def _build_concept_attempts(self, pro: Any) -> list[tuple[str, Callable[[], Any]]]:
        settings = self._settings()
        configured = settings.tushare_concept_api_list()
        unknown = [name for name in configured if name not in SUPPORTED_CONCEPT_APIS]
        if unknown:
            raise RuntimeError(
                "不支持的 TUSHARE_CONCEPT_APIS："
                + ",".join(unknown)
                + f"（可选：{','.join(sorted(SUPPORTED_CONCEPT_APIS))}）"
            )

        src = (settings.TUSHARE_CONCEPT_SRC or "ts").strip() or "ts"
        ths_type = (settings.TUSHARE_THS_INDEX_TYPE or "N").strip() or "N"
        ths_exchange = (settings.TUSHARE_THS_INDEX_EXCHANGE or "A").strip() or "A"

        builders: dict[str, Callable[[], Any]] = {
            "concept": lambda: pro.concept(src=src),
            "ths_index": lambda: pro.ths_index(exchange=ths_exchange, type=ths_type),
            "dc_index": lambda: pro.dc_index(),
        }
        return [(name, builders[name]) for name in configured]

    def _fetch_concept_frame_sync(self) -> tuple[Any, str]:
        """同步拉取概念列表；按配置顺序尝试接口。"""
        pro = self._pro_api()
        errors: list[str] = []
        attempts = self._build_concept_attempts(pro)
        if not attempts:
            raise RuntimeError("TUSHARE_CONCEPT_APIS 为空，无法拉取概念列表")

        for api_name, call in attempts:
            try:
                frame = call()
                if frame is not None and not getattr(frame, "empty", True):
                    return frame, api_name
                errors.append(f"{api_name}: 空结果")
            except Exception as exc:  # noqa: BLE001 — 汇总多接口错误
                errors.append(f"{api_name}: {exc}")
        raise RuntimeError(
            "Tushare 概念接口均不可用（请检查积分/权限与 TUSHARE_CONCEPT_APIS："
            "https://tushare.pro/document/1?doc_id=108）。"
            + "；".join(errors)
        )

    async def collect_full(
        self,
        cancel: asyncio.Event | None = None,
        params: dict[str, Any] | None = None,
        on_progress: Callable[[float], None] | None = None,
    ) -> FullScrapeDraft:
        """采集 Tushare 概念题材草稿（themes-only）。"""
        del params

        def report(pct: float) -> None:
            if on_progress is not None:
                on_progress(max(0.0, min(100.0, pct)))

        if cancel is not None and cancel.is_set():
            raise asyncio.CancelledError()

        settings = self._settings()
        self._require_token()
        max_retries = max(1, int(settings.TUSHARE_MAX_RETRIES or 3))
        logger.info(
            f"[{self.source_name}] 开始全量题材采集（Tushare 概念，不落库；"
            f"apis={settings.tushare_concept_api_list()}）"
        )
        report(10.0)

        last_error: Exception | None = None
        frame = None
        api_name = ""
        for attempt in range(1, max_retries + 1):
            if cancel is not None and cancel.is_set():
                raise asyncio.CancelledError()
            try:
                frame, api_name = await asyncio.to_thread(self._fetch_concept_frame_sync)
                last_error = None
                break
            except Exception as e:
                last_error = e
                logger.warning(
                    f"[{self.source_name}] 获取概念板块失败"
                    f"（第 {attempt}/{max_retries} 次）: {e}"
                )
                if attempt < max_retries:
                    await asyncio.sleep(1.5 * attempt)

        if last_error is not None or frame is None:
            logger.error(f"[{self.source_name}] 获取概念板块失败: {last_error}")
            raise last_error or RuntimeError("获取 Tushare 概念板块失败")

        if cancel is not None and cancel.is_set():
            raise asyncio.CancelledError()

        report(80.0)
        themes = self._parse_concept_themes(frame, api_name=api_name)
        logger.info(
            f"[{self.source_name}] 经 {api_name} 解析到 {len(themes)} 个概念题材"
        )
        report(100.0)
        return FullScrapeDraft(
            source=self.source_name,
            trade_date=date.today() if themes else None,
            themes=themes,
            stocks_by_code={},
        )

    async def _save_themes(self, themes: list[dict[str, Any]]) -> int:
        saved_count = 0
        async with AsyncSessionLocal() as session:
            theme_codes = [t["code"] for t in themes if t.get("code")]
            existing_result = await session.execute(
                select(Theme).where(
                    Theme.code.in_(theme_codes),
                    Theme.deleted_at.is_(None),
                )
            )
            existing_map = {t.code: t for t in existing_result.scalars().all()}

            for theme_data in themes:
                try:
                    theme = existing_map.get(theme_data["code"])
                    if theme:
                        theme.name = theme_data["name"]
                        theme.code = theme_data["code"]
                        if theme_data.get("heat_index") is not None:
                            theme.heat_index = theme_data["heat_index"]
                        if theme_data.get("rise_fall_pct") is not None:
                            theme.rise_fall_pct = theme_data["rise_fall_pct"]
                        if theme_data.get("stock_count") is not None:
                            theme.stock_count = theme_data["stock_count"]
                        if theme_data.get("category") is not None:
                            theme.category = theme_data["category"]
                        theme.source = theme_data.get("source", self.source_name)
                    else:
                        theme = Theme(
                            name=theme_data["name"],
                            code=theme_data["code"],
                            heat_index=theme_data.get("heat_index") or Decimal("0"),
                            rise_fall_pct=theme_data.get("rise_fall_pct")
                            or Decimal("0"),
                            stock_count=theme_data.get("stock_count") or 0,
                            category=theme_data.get("category"),
                            source=theme_data.get("source", self.source_name),
                        )
                        session.add(theme)
                    saved_count += 1
                except Exception as e:
                    logger.error(
                        f"[{self.source_name}] 保存题材失败: {e}, 数据: {theme_data}"
                    )
                    continue

            await session.commit()

        logger.info(f"[{self.source_name}] 保存了 {saved_count} 个题材")
        return saved_count

    async def commit_full(self, draft: FullScrapeDraft) -> int:
        if not draft.themes:
            return 0
        return await self._save_themes(draft.themes)

    async def run(
        self, url: str = "", params: dict[str, Any] | None = None
    ) -> tuple[list[dict[str, Any]], int]:
        """调度器路径：采集并落库题材列表。"""
        del url, params
        draft = await self.collect_full()
        if not draft.themes:
            return [], 0
        saved = await self.commit_full(draft)
        return draft.themes, saved

    async def close(self) -> None:
        await self.middleware.close()
