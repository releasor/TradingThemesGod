# 题材挖掘 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 落地 `/mining` 三列题材挖掘（低位分支 / 补涨 / 隐性龙头），双层题材卡→个股明细，日快照落库，可选模型点评；Nav「复盘研究」入口。

**Architecture:** `mining_rules` 纯函数消费 `sector_rotation_snapshots` + 成分股涨跌 → 写入 `theme_mining_cards` / `theme_mining_members`；`MiningService.ensure` 幂等；board/card API；note 后台 LLM；refresh_signals 挂钩。

**Tech Stack:** FastAPI、SQLAlchemy Async、Alembic、MySQL 8、pytest、React、TanStack Query、Vitest。

**Spec:** `docs/superpowers/specs/2026-07-26-theme-mining-design.md`

**Commits:** 仅用户明确要求时提交。

---

## 文件结构

### 新建

| 文件 | 职责 |
|------|------|
| `backend/alembic/versions/018_create_theme_mining_tables.py` | 三表 |
| `backend/app/models/theme_mining.py` | ORM |
| `backend/app/services/mining_rules.py` | 纯函数规则 |
| `backend/app/repositories/theme_mining.py` | 幂等写入与查询 |
| `backend/app/services/mining.py` | ensure / board / note |
| `backend/app/schemas/mining.py` | DTO |
| `backend/app/api/mining.py` | `/api/v1/mining` |
| `backend/tests/unit/test_mining_models.py` | |
| `backend/tests/unit/test_mining_rules.py` | |
| `backend/tests/unit/test_mining_service.py` | |
| `backend/tests/unit/test_mining_api.py` | |
| `frontend/src/types/mining.ts` | |
| `frontend/src/api/mining.ts` | |
| `frontend/src/api/mining.test.ts` | |
| `frontend/src/features/mining/ThemeMiningBoard.tsx` | |
| `frontend/src/features/mining/MiningColumn.tsx` | |
| `frontend/src/features/mining/MiningCard.tsx` | |
| `frontend/src/features/mining/ThemeMiningBoard.test.tsx` | |

### 修改

| 文件 | 变更 |
|------|------|
| `backend/app/models/__init__.py` | 注册 |
| `backend/app/main.py` | mount |
| `backend/app/services/short_term.py` | refresh 后挂钩 ensure |
| `frontend/src/components/AppCardNav.tsx` | 题材挖掘链接 |
| `frontend/src/components/AppCardNav.test.tsx` | |
| `frontend/src/App.tsx` | `/mining` |

---

### Task 1: 迁移 + ORM

- [ ] 测试列/唯一约束/索引名  
- [ ] `ThemeMiningCard` / `ThemeMiningMember` / `ThemeMiningNote`  
- [ ] Alembic `018_create_theme_mining_tables`，`down_revision=017_create_catalyst_radar`  
- [ ] InnoDB utf8mb4；`alembic upgrade head`；pytest models PASS  

---

### Task 2: mining_rules（TDD）

```python
@dataclass
class ThemeMiningInput:
    theme_id: int
    lifecycle_stage: str
    strength_score: int
    leader_clarity_score: int | None
    flow_score: int | None
    stocks: list[StockMetric]  # stock_id, rise_fall_pct, heat?

def mine_theme(inp: ThemeMiningInput) -> list[CardDraft]:
    # returns 0–3 drafts with type + members
```

测试：low_branch 滞后股；catch_up 中位下正涨；hidden_leader 非 Top2；无涨跌不出卡。

---

### Task 3: Repository

- `replace_day_cards(trade_date, cards_with_members)` — 删当日旧卡或按 unique upsert 后替换 members  
- `list_board(trade_date)` — 按 type 分组  
- `get_card(card_id)`  
- `upsert_note(...)` / `get_note(card_id, user_id)`  

---

### Task 4: MiningService

- `ensure(trade_date=None)` — resolve date；拉 Top 题材快照 + 成分股；规则；写入；返回 counts  
- `get_board(trade_date=None)`  
- `get_card(id, user_id=None)`  
- `ensure_note(card_id, user_id)` — pending + create_task 后台  

题材池：从 `sector_rotation_snapshots` 当日取 Top 40 by strength。  
成分股：`theme_stocks` join `stocks`。  
概念标签：可选查 `concept_node_stocks` 取一 node。

---

### Task 5: API + short_term 挂钩

```python
GET /mining/board
GET /mining/cards/{id}
POST /mining/ensure
POST /mining/cards/{id}/note/ensure  # get_current_user
```

`refresh_signals` finally/success：`try MiningService(session).ensure(trade_date)` except log.

---

### Task 6: Frontend API

`fetchMiningBoard`, `fetchMiningCard`, `ensureMining`, `ensureMiningNote` + vitest。

---

### Task 7: UI + Nav

三列 `MiningColumn`；卡可展开 members；日期选择；ensure 按钮；点评。  
Nav 增加题材挖掘；`App.tsx` lazy `/mining`。

---

### Task 8: 冒烟

```bash
pytest tests/unit/test_mining_*.py -q
pnpm exec vitest run src/api/mining.test.ts src/features/mining/ThemeMiningBoard.test.tsx src/components/AppCardNav.test.tsx
alembic upgrade head
curl POST /api/v1/mining/ensure && GET /api/v1/mining/board
```

---

## Spec coverage

| 项 | Task |
|----|------|
| 三表 | 1 |
| 规则三类 | 2 |
| 快照 ensure | 3–4 |
| board/card/note API | 5 |
| 三列双层 UI | 6–7 |
| refresh 挂钩 | 5 |

## 执行交接

Plan saved to `docs/superpowers/plans/2026-07-26-theme-mining.md`.

**1. Subagent-Driven (recommended)**  
**2. Inline Execution**  

Which approach?
