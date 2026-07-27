# 主线图谱平台 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 落地 `/mainline-graph` 双模主线图谱平台一期：版本化叙事图（规则边 + 建议边 + 人工编辑草稿/发布）、ECharts 图+抽屉、概念树模式；二期动画只留接口位不实现。

**Architecture:** `mainline_graph_versions/nodes/edges` 落库；`mainline_graph_rules` 算 Jaccard 边；`MainlineGraphService.ensure` 写 auto；draft 编辑与 publish；前端 echarts-for-react；概念树复用现有 graph API。

**Tech Stack:** FastAPI、SQLAlchemy、Alembic、MySQL、pytest、React、ECharts、TanStack Query、Vitest。

**Spec:** `docs/superpowers/specs/2026-07-26-mainline-graph-platform-design.md`

**Commits:** 仅用户要求时提交。

---

## 文件结构

### 新建

| 文件 | 职责 |
|------|------|
| `backend/alembic/versions/019_create_mainline_graph_tables.py` | 三表 |
| `backend/app/models/mainline_graph.py` | ORM |
| `backend/app/services/mainline_graph_rules.py` | Jaccard / 定向 |
| `backend/app/repositories/mainline_graph.py` | CRUD 版本/节点/边 |
| `backend/app/services/mainline_graph.py` | ensure / view / draft / publish |
| `backend/app/schemas/mainline_graph.py` | DTO |
| `backend/app/api/mainline_graph.py` | router |
| `backend/tests/unit/test_mainline_graph_*.py` | models/rules/service/api |
| `frontend/src/types/mainline-graph.ts` | |
| `frontend/src/api/mainline-graph.ts` | |
| `frontend/src/features/mainline-graph/*` | Page/Chart/Drawer/ConceptMode |

### 修改

| 文件 | 变更 |
|------|------|
| `models/__init__.py`、`main.py` | 注册挂载 |
| `short_term.py` | 可选 ensure 挂钩 |
| `AppCardNav.tsx`、`App.tsx` | Nav + `/mainline-graph` |
| 可选：抽 `ConceptGraphTree` 供详情与本页共用 |

---

### Task 1: 迁移 + ORM

- versions / nodes / edges 按 spec；唯一约束与索引  
- `019` down_revision=`018_create_theme_mining_tables`  
- pytest models；`alembic upgrade head`

### Task 2: rules（TDD）

```python
def build_edges(themes: list[ThemeSnap], overlap: dict[tuple[int,int], float], *, jaccard_min=0.12, top_main=5) -> list[EdgeDraft]
```

测试：定向 from 高 mainline；阈值过滤；平局 theme_id。

### Task 3: Repository

- create_auto_version(trade_date, nodes, edges) 替换当日 auto  
- clone_version → draft  
- list/get view payload  
- upsert_edge / delete_edge on draft  
- publish_version（归档旧 published）  
- accept_suggested_edge  

### Task 4: Service

- ensure：拉 Top30 快照 + 批量算 overlap（SQL 或 Python 集合）  
- view(trade_date|version_id) 默认 published 否则 auto  
- create_draft / patch_edges / publish  
- optional model suggest background（可先 stub 队列 + 空实现，测 model_queued）  

Overlap：对 Top 主题一次查出 theme_id→set(stock_id)，内存 Jaccard。

### Task 5: API

```
GET  /mainline-graph/view
GET  /mainline-graph/versions
POST /mainline-graph/ensure
POST /mainline-graph/versions
PATCH /mainline-graph/versions/{id}/edges
POST /mainline-graph/versions/{id}/publish
POST /mainline-graph/edges/{id}/accept
GET  /mainline-graph/themes/{id}/concept
```

挂 short_term refresh 可选 ensure。

### Task 6–7: Frontend

- API client + types + tests  
- Page 双模；NarrativeChart（echarts graph）；Drawer；编辑条  
- Concept mode：fetch concept + 强度条  
- Nav 链接  

### Task 8: 冒烟

pytest + vitest；ensure → view 有边；手工打开 `/mainline-graph`。

---

## Spec coverage

| 一期项 | Task |
|--------|------|
| 三表版本化 | 1,3 |
| 规则边 | 2,4 |
| 编辑/发布 | 3–5 |
| 双模 UI | 6–7 |
| 模型建议 | 4（可 stub） |
| 二期动画 | 不做 |

## 执行交接

Plan: `docs/superpowers/plans/2026-07-26-mainline-graph-platform.md`

**1. Subagent-Driven (recommended)**  
**2. Inline Execution**  

Which approach?
