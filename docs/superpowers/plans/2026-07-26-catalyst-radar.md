# 催化雷达 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 落地独立路由 `/catalysts` 双栏催化雷达：对 `theme_driver_events` 做新催化/旧闻与政策/公司分类（规则打底 + 可选模型后台重标），左时间流、右题材摘要并附带新闻标题；经 Nav「复盘研究」进入，读路径不爬网。

**Architecture:** 迁移扩展 `theme_driver_events` 分类列 + `catalyst_classifications` 审计表；`CatalystRuleClassifier` 纯函数；`CatalystService` 提供 feed/summary/ensure；洞察 upsert 后挂钩规则；模型重标 `asyncio.create_task`；前端 `features/catalysts`。

**Tech Stack:** FastAPI、SQLAlchemy Async、Alembic、MySQL 8、pytest、React、TanStack Query、Vitest、Tailwind。

**Spec:** `docs/superpowers/specs/2026-07-26-catalyst-radar-design.md`

**Commits:** 仅在用户明确要求时提交；步骤中的 commit 为建议信息，默认不自动执行。

---

## 文件结构

### 新建

| 文件 | 职责 |
|------|------|
| `backend/alembic/versions/017_create_catalyst_radar.py` | 事件列 + classifications 表 |
| `backend/app/models/catalyst.py` | `CatalystClassification` ORM（事件列改在 theme_driver_event.py） |
| `backend/app/services/catalyst_rules.py` | 规则纯函数 |
| `backend/app/repositories/catalyst.py` | 分类写入、feed 查询、summary 查询 |
| `backend/app/services/catalyst.py` | feed / summary / ensure / 模型入队 |
| `backend/app/schemas/catalyst.py` | API DTO |
| `backend/app/api/catalysts.py` | `/api/v1/catalysts` |
| `backend/tests/unit/test_catalyst_rules.py` | 规则 |
| `backend/tests/unit/test_catalyst_service.py` | 聚合 |
| `backend/tests/unit/test_catalyst_api.py` | API |
| `frontend/src/types/catalyst.ts` | 类型 |
| `frontend/src/api/catalysts.ts` | client |
| `frontend/src/api/catalysts.test.ts` | client 测 |
| `frontend/src/features/catalysts/CatalystRadar.tsx` | 双栏页 |
| `frontend/src/features/catalysts/CatalystFeedPanel.tsx` | 左栏 |
| `frontend/src/features/catalysts/CatalystThemeSummary.tsx` | 右栏 |
| `frontend/src/features/catalysts/CatalystRadar.test.tsx` | UI |

### 修改

| 文件 | 变更 |
|------|------|
| `backend/app/models/theme_driver_event.py` | 四分类列 |
| `backend/app/models/__init__.py` | 注册 |
| `backend/app/repositories/theme_insight.py` | upsert 后调用分类（或 service 层） |
| `backend/app/services/theme_insight.py` | 落库后 `classify_events` |
| `backend/app/main.py` | mount router |
| `frontend/src/components/AppCardNav.tsx` | 催化雷达链接 |
| `frontend/src/components/AppCardNav.test.tsx` | 断言 |
| `frontend/src/App.tsx` | `/catalysts` 路由 |

### 已有可复用

- `ThemeDriverEvent`、`NewsArticle`（标题关键词匹配）
- `SectorRotationSnapshot`（右侧阶段/强度可选）
- `ReviewReportService` 后台任务模式、`get_optional_user`
- `ThemeInsightService.upsert_events` 挂钩点

---

### Task 1: 迁移 + ORM

**Files:** `017_create_catalyst_radar.py`、`theme_driver_event.py`、`catalyst.py`、`models/__init__.py`、`test_catalyst_models.py`

- [ ] **Step 1: 失败测试**

```python
from app.models.theme_driver_event import ThemeDriverEvent
from app.models.catalyst import CatalystClassification

def test_driver_event_has_classification_columns():
    cols = {c.name for c in ThemeDriverEvent.__table__.columns}
    assert {"freshness", "actor_type", "classified_by", "classified_at"} <= cols

def test_catalyst_classification_indexes():
    names = {i.name for i in CatalystClassification.__table__.indexes}
    assert "idx_catalyst_classifications_event_created" in names
```

- [ ] **Step 2: 实现列与表**

`ThemeDriverEvent` 增加：
- `freshness: Mapped[str] = mapped_column(String(16), nullable=False, default="unknown")`
- `actor_type: Mapped[str] = mapped_column(String(16), nullable=False, default="unknown")`
- `classified_by: Mapped[str | None] = mapped_column(String(16), nullable=True)`
- `classified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)`
- 索引 `idx_theme_driver_events_freshness_published`、`idx_theme_driver_events_actor_published`

`CatalystClassification`：`event_id` FK CASCADE，字段按 spec。

- [ ] **Step 3: Alembic `017`**

`down_revision = "016_create_review_desk_tables"`  
`op.add_column` + `create_table`；MySQL InnoDB/utf8mb4。

- [ ] **Step 4: pytest PASS + `alembic upgrade head`**

---

### Task 2: 规则分类器（TDD）

**Files:** `catalyst_rules.py`、`test_catalyst_rules.py`

- [ ] **Step 1: 测试用例**

```python
def test_replay_when_title_similar_within_14_days():
    current = EventInput(title="某政策再度加码机器人", published_at=..., theme_id=1)
    recent = [EventInput(title="政策加码机器人产业", published_at=current.published_at - timedelta(days=3), ...)]
    result = classify_event(current, recent)
    assert result.freshness == "replay"

def test_policy_keywords():
    assert classify_event(...标题含证监会...).actor_type == "policy"

def test_company_keywords():
    assert classify_event(...标题含中标业绩...).actor_type == "company"

def test_conflict_source_wins_or_other():
    # 按 spec：来源优先，平局 other
    ...

def test_unknown_when_no_signal():
    assert classify_event(...中性标题..., recent=[]).freshness in ("new", "unknown")
    # 无近期相似 → freshness=new；无 actor 词 → actor_type=unknown
```

- [ ] **Step 2: 实现**

```python
@dataclass(frozen=True)
class ClassifyResult:
    freshness: str
    actor_type: str
    confidence: int
    rationale: str

def normalize_title(title: str) -> str: ...
def title_jaccard(a: str, b: str) -> float: ...
def classify_event(current, recent_same_theme: list) -> ClassifyResult: ...
```

阈值：14 日、Jaccard 0.55、关键词表见 spec。

- [ ] **Step 3: pytest PASS**

---

### Task 3: Repository + 应用分类

**Files:** `repositories/catalyst.py`、扩展 insight 挂钩

- [ ] **Step 1: `CatalystRepository`**

```python
async def apply_classification(self, event_id, result: ClassifyResult, *, method: str, model_name=None) -> None:
    # update ThemeDriverEvent columns + insert CatalystClassification

async def list_feed(self, *, freshness=None, actor_type=None, theme_id=None, q=None, start=None, end=None, limit=30, offset=0) -> list[FeedRow]:
    # join Theme for name; order published_at desc

async def count_by_theme(self, theme_id, since: datetime) -> dict: ...

async def list_theme_events(self, theme_id, limit=10) -> list: ...

async def list_news_headlines_for_theme(self, theme_name: str, limit=8) -> list:
    # NewsArticle.title.contains(theme_name) order by published_at/created_at desc
```

- [ ] **Step 2: `classify_event_ids` / `classify_recent(days=7)`** 拉同题材近期事件再跑规则

- [ ] **Step 3: 在 `ThemeInsightService` 成功 `upsert_events` 后**，对插入/更新的 event id 调用分类（try/except 吞掉，不影响洞察主流程）

- [ ] **Step 4: 单测** mock session 或规则层

---

### Task 4: CatalystService + schemas

**Files:** `schemas/catalyst.py`、`services/catalyst.py`、`test_catalyst_service.py`

- [ ] **Step 1: Schema**

```python
class CatalystFeedItem(BaseModel): ...
class CatalystFeedResponse(BaseModel):
    items: list[CatalystFeedItem]
    total: int | None = None

class CatalystThemeSummaryResponse(BaseModel):
    theme_id: int
    theme_name: str
    lifecycle_stage: str | None = None
    strength_score: int | None = None
    counts: dict[str, int]
    recent_events: list[CatalystFeedItem]
    news_headlines: list[NewsHeadlineItem]  # title, url, published_at, match_note="关键词匹配"
```

- [ ] **Step 2: Service**

```python
class CatalystService:
    async def get_feed(...) -> CatalystFeedResponse: ...
    async def get_theme_summary(theme_id: int) -> CatalystThemeSummaryResponse: ...
    async def ensure_classify(self, *, days=7, use_model=False, user_id=None) -> dict:
        # 1) 规则批处理近 days 日 unknown/未分类
        # 2) if use_model and user_id: create_task background reclassify
        # return {classified_rules: n, model_queued: bool}
```

右侧 lifecycle：查最近 `sector_rotation_snapshots`；无则 null。

- [ ] **Step 3: 模型重标后台**（可简化：JSON 要求 freshness/actor_type/confidence/rationale；失败保留规则）

- [ ] **Step 4: 测试** feed 筛选、summary 无新闻、ensure 规则计数

---

### Task 5: API

**Files:** `api/catalysts.py`、`main.py`、`test_catalyst_api.py`

```python
router = APIRouter(prefix="/catalysts", tags=["catalysts"])

@router.get("/feed")
@router.get("/themes/{theme_id}/summary")
@router.post("/classify/ensure")  # optional user; use_model 仅当 user 存在且显式 true
```

Mount：`app.include_router(catalysts_router, prefix="/api/v1")`

测试：patch service，断言 200。

---

### Task 6: Frontend API + 类型

- [ ] `types/catalyst.ts`、`api/catalysts.ts`、`catalysts.test.ts`
- [ ] `fetchCatalystFeed`、`fetchCatalystThemeSummary`、`ensureCatalystClassify`
- [ ] vitest PASS

---

### Task 7: UI + Nav

- [ ] `AppCardNav` 增加 `{ label: '催化雷达', href: '/catalysts', ariaLabel: '进入催化雷达' }`
- [ ] `App.tsx` lazy `/catalysts`
- [ ] `CatalystRadar`：左筛选+列表，右 summary；选中 themeId 用 searchParams；进入可选静默 `ensure`（`use_model: false`）
- [ ] 徽章：新催化/旧闻、政策/公司/其他/未知
- [ ] 测试：渲染 feed 项、Nav href、空态

```
pnpm exec vitest run src/api/catalysts.test.ts src/features/catalysts/CatalystRadar.test.tsx src/components/AppCardNav.test.tsx
```

---

### Task 8: 迁移 + 冒烟

```bash
cd backend
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python.exe -m pytest tests/unit/test_catalyst_*.py -q
cd ../frontend
pnpm exec vitest run src/api/catalysts.test.ts src/features/catalysts/CatalystRadar.test.tsx src/components/AppCardNav.test.tsx
```

手工：Nav → 催化雷达；`GET /api/v1/catalysts/feed` 200；ensure 后事件列非 unknown（有数据时）。

---

## Spec coverage

| Spec 项 | Task |
|---------|------|
| 列 + classifications 表 | 1 |
| 规则分类 | 2–3 |
| 洞察挂钩 | 3 |
| feed / summary / ensure | 4–5 |
| 模型后台可选 | 4 |
| 双栏 UI + Nav | 6–7 |
| 读路径不爬网 | 4–5（禁止 scraper 调用） |

## 执行交接

Plan complete and saved to `docs/superpowers/plans/2026-07-26-catalyst-radar.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — 每任务子代理 + 复查  
2. **Inline Execution** — 本会话连续推进  

Which approach?
