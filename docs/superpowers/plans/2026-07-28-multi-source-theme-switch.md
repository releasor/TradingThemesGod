# 多源题材分存与看板源切换 Implementation Plan

> **For agentic workers:** Implement task-by-task. Checkbox tracking optional.

**Goal:** 题材按 source 分存；全量各源即时 commit；看板可切换 active_source。

**Architecture:** `UNIQUE(source,code)`；竞速每源完成后 commit；API `source=` 过滤；前端 localStorage 活跃源。

**Tech Stack:** Alembic, SQLAlchemy, FastAPI, React Query

**Spec:** `docs/superpowers/specs/2026-07-28-multi-source-theme-switch-design.md`

## Tasks

1. Migration + Theme model: drop unique on code, unique(source,code), backfill source
2. Scrapers `_save_themes` lookup by (source, code)
3. full_race: commit each completed draft immediately; success if any commit
4. Theme repo/API: source filter on list/ranking/signals
5. Dashboard: source switcher + query param
6. Tests + verify
