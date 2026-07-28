# Tushare 前端数据源配置 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在设置「数据源」页配置 Tushare 启用开关与 Token（加密落库、可测试、竞速即时生效）。

**Architecture:** 单例表 `tushare_settings` + `SecretStore`；进程内缓存供同步路径（`full_race`）读取；API JWT 保护；高级项仍用 env。

**Tech Stack:** FastAPI、SQLAlchemy、Alembic、Fernet、React、React Query

**Spec:** `docs/superpowers/specs/2026-07-28-tushare-frontend-config-design.md`

---

## File map

| File | Responsibility |
|------|----------------|
| `backend/app/models/tushare_settings.py` | ORM 单例 |
| `backend/alembic/versions/021_create_tushare_settings.py` | 迁移 |
| `backend/app/schemas/tushare_settings.py` | GET/PUT/Test schemas |
| `backend/app/services/tushare_settings.py` | resolve/cache/save/test |
| `backend/app/api/integrations.py` | `/integrations/tushare` |
| `backend/app/scrapers/tushare_scraper.py` | 用 runtime 凭据 |
| `backend/app/scrapers/full_race.py` | `tushare_ready` 读 cache |
| `backend/app/main.py` | 挂路由 + lifespan 预热 cache |
| `frontend/src/api/integrations.ts` | API client |
| `frontend/src/features/settings/IntegrationsSettings.tsx` | 数据源页 |
| `SettingsSubnav` / `AppCardNav` / `App.tsx` | 导航与路由 |

---

### Task 1: Model + migration

- Create model `TushareSettings` (`id`, `enabled`, `token_encrypted`, `updated_at`, `updated_by`)
- Migration `021` down from `020`, seed row `id=1, enabled=false`
- Export from `app/models/__init__.py`

### Task 2: Service + schemas + API

- `TushareRuntime(enabled, token)` + module cache
- `resolve_from_db_or_env(db)` → update cache
- `get_cached_runtime()` sync fallback env
- `save(enabled, token_optional, user_id)` encrypt if token non-empty
- `test_connection(token_override?)` → `trade_cal` 轻量调用
- Router GET/PUT/POST test under `/integrations/tushare`
- Register in `main.py`; lifespan warm cache

### Task 3: Wire scraper + full_race

- Scraper `_require_token` / enabled 读 `get_cached_runtime()`（collect 前 `await refresh_cache(db)`）
- `default_full_race_sources` 用 `get_cached_runtime().ready`

### Task 4: Backend tests

- resolve DB vs env; empty token keep; ready gating; API auth mask

### Task 5: Frontend page

- API + IntegrationsSettings（开关、token、保存、测试）
- Subnav / CardNav / App route ProtectedRoute

### Task 6: Verify

- 迁移、pytest、浏览器打开 `/settings/integrations`
