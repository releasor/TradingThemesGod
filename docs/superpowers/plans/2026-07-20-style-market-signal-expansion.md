# Style Market Signal Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将完整风格因子板块归入现有市场表现区域。

**Architecture:** 保持代码集合为唯一分类来源，只扩充已核实的东方财富板块代码。所有普通题材排除查询和市场表现包含查询继续复用现有 SQLAlchemy 条件。

**Tech Stack:** Python 3.12、SQLAlchemy、pytest、FastAPI

---

### Task 1: 扩充市场表现分类

**Files:**
- Modify: `backend/tests/unit/test_theme_classification.py`
- Modify: `backend/app/domain/theme_classification.py`

- [x] **Step 1: 写失败的完整风格代码测试**

在 `test_theme_classification.py` 中断言 17 个新增代码均满足 `is_market_signal(code) is True`，并断言 `BK0683` 为普通题材。

- [x] **Step 2: 运行测试确认新增代码尚未被识别**

Run: `cd backend; .\.venv\Scripts\python.exe -m pytest tests/unit/test_theme_classification.py -q`

Expected: 新增风格代码断言失败。

- [x] **Step 3: 扩充显式代码集合**

将 `BK1112`、`BK1139`、`BK1635`、`BK1636`、`BK1640`、`BK1641`、`BK1643`、`BK1662` 至 `BK1670` 和 `BK1672` 加入 `MARKET_SIGNAL_CODES`，保留现有市场行为代码。

- [x] **Step 4: 运行分类、仓储和 API 回归**

Run: `cd backend; .\.venv\Scripts\python.exe -m pytest tests/unit/test_theme_classification.py tests/unit/test_theme_repository.py tests/unit/test_theme_service.py tests/integration/test_theme_api.py -q`

Expected: PASS。

- [x] **Step 5: 执行 Ruff、Black 和真实接口回读**

Run: `cd backend; .\.venv\Scripts\python.exe -m ruff check app/domain/theme_classification.py tests/unit/test_theme_classification.py; .\.venv\Scripts\python.exe -m black --check app/domain/theme_classification.py tests/unit/test_theme_classification.py`

Expected: 静态检查通过；市场表现接口包含新增风格板块，普通题材接口不包含这些代码。
