"""进程内短 TTL 概念列表缓存，减轻重叠刷新对东财/AKShare 的重复请求。"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from app.core.config import get_settings

T = TypeVar("T")

EM_THEME_LIST_KEY = "em:theme_list"
AKSHARE_CONCEPT_NAME_EM_KEY = "akshare:concept_name_em"

_cache: dict[str, tuple[float, Any]] = {}
_locks: dict[str, asyncio.Lock] = {}
_locks_guard = asyncio.Lock()


def _ttl_seconds(ttl: float | None) -> float:
    if ttl is not None:
        return max(0.0, float(ttl))
    settings = get_settings()
    return float(getattr(settings, "SCRAPER_CONCEPT_LIST_CACHE_TTL_SECONDS", 60) or 60)


def get(key: str) -> Any | None:
    entry = _cache.get(key)
    if entry is None:
        return None
    expires_at, value = entry
    if time.monotonic() >= expires_at:
        _cache.pop(key, None)
        return None
    return value


def set(key: str, value: Any, ttl: float | None = None) -> None:
    seconds = _ttl_seconds(ttl)
    if seconds <= 0:
        return
    _cache[key] = (time.monotonic() + seconds, value)


def clear() -> None:
    _cache.clear()


async def _lock_for(key: str) -> asyncio.Lock:
    async with _locks_guard:
        lock = _locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            _locks[key] = lock
        return lock


async def get_or_fetch(
    key: str,
    fetch: Callable[[], Awaitable[T]],
    *,
    ttl: float | None = None,
) -> T:
    hit = get(key)
    if hit is not None:
        return hit  # type: ignore[no-any-return]

    lock = await _lock_for(key)
    async with lock:
        hit = get(key)
        if hit is not None:
            return hit  # type: ignore[no-any-return]
        value = await fetch()
        set(key, value, ttl=ttl)
        return value
