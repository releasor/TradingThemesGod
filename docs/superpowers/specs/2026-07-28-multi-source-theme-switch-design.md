# 多源题材分存与看板源切换设计

**日期：** 2026-07-28  
**状态：** 待实现  
**范围：** 题材按采集源分套落库；全量竞速各源独立写入；看板可切换 `active_source` 实时查看

## 背景

当前 `themes.code` 全局唯一，全量竞速只让一个「胜出源」`commit_full`，且 upsert 按 `code` 覆盖并改写 `source`。兜底源（AKShare / 同花顺 / Tushare）只有题材列表，东方财富含成分股；竞速时需长时间等待东财，或超时后丢失东财结果。

产品确认采用 **长期多源并存**：各源数据各自备好，用户可随时切换查看。

## 目标

1. 同一题材代码可在不同 `source` 下各有一行（及各自成分股/快照）。
2. 全量更新时：某源 `collect_full` 完成后即 `commit_full` 到该源命名空间，不互相覆盖。
3. 看板提供数据源切换；列表/排名/策略卡等读数按当前 `active_source` 过滤。
4. 先完成的源可立刻切换查看；东财后到后也可再切到东财（含成分股）。

## 非目标（本迭代）

- 不自动「合并」多源题材为一套视图。
- 不改新闻/催化等非题材主表的多源模型。
- 不做跨源成分股 diff 对比页（可后续加）。
- Tushare 无权限时仍可关闭；不强制开通付费接口。

## 数据模型

### themes

- 去掉全局 `UNIQUE(code)`。
- 新增 **`UNIQUE(source, code)`**（`source` 非空；迁移时 `NULL/''` → `'eastmoney'` 或原值）。
- 查询默认带 `source = :active_source`。

### theme_stocks / theme_market_snapshots

- 仍挂 `theme_id`，随父题材自然分源，无需加 `source` 列。

### 活跃源偏好

- 用户级（登录）：可存 `users` 扩展字段或小型 `user_preferences`；首期可用前端 `localStorage` + 可选后端偏好 API。
- 默认：`eastmoney`（与 `get_default_dashboard_source()` 一致）。
- 未登录：仅 `localStorage`。

## 全量竞速行为变更

| 旧 | 新 |
|----|----|
| 并行采集，仅胜出源 commit | 各源采集完成后 **立即** commit 到本源 |
| 兜底需等东财宽限 | 兜底先落库；东财继续跑，完成后落库东财源 |
| 竞速「失败」若全无胜出 | 以「至少一源成功 commit」为成功；进度展示各源 completed/failed |

细节：

1. `_is_primary_valid` / `_is_fallback_only` 仍用于文案（完整 vs 题材-only），但 **都允许 commit**。
2. 取消：已 commit 的源保留；未完成的源取消采集。
3. `scraper_runs`：每源成功 commit 各记一条（或一条 run 带多源摘要，优先每源一条以兼容「最近成功」）。
4. 前端进度：显示各源「已写入 / 采集中 / 失败」；不再暗示「只有东财完整才算更新成功」。

## API

- `GET /themes`、排名、市场信号等：增加查询参数 `source`（默认取用户/请求的 active source，缺省 `eastmoney`）。
- `GET /scraper/sources?dashboard_only=true`：保持；前端切换器用。
- 可选：`GET/PUT /me/preferences` 含 `active_dashboard_source`（若首期只用 localStorage 可延后）。

## 前端

- 看板刷新控件旁或状态条增加 **数据源 Segmented/Select**：东方财富 / AKShare / 同花顺 / Tushare（仅 `dashboard_selectable` 且库中该源有数据或刚写入的可点；无数据时禁用并提示「尚未采集」）。
- 切换源后 refetch 题材列表与依赖 `source` 的区块。
- 全量进行中：某源变为 completed 时 toast「同花顺数据已就绪，可切换查看」；不强制跳转。
- 「刷新」（行情快刷）仍按当前源的题材 codes 刷涨跌幅（东财/AKShare 报价竞速逻辑可保持，但只更新当前源行）。

## 迁移注意

1. 备份后改唯一约束；重复 `code` 多行若历史已存在需先清洗（正常不应有）。
2. 所有 `Theme.code == x` 的查找改为 `(source, code)` 或「先按 active_source」。
3. 详情页 `/themes/:id` 仍按 id；从列表带入的 id 已属某源。深链旧书签不受影响。
4. 题材库、复盘等入口逐步加 source 过滤；本迭代至少覆盖 **看板主路径**。

## 验收

1. 全量更新：同花顺/AKShare 先完成后，切换到该源可见新题材列表；东财仍显示采集中。
2. 东财完成后切换到东财，可见成分股相关能力（详情/关联）基于东财主题行。
3. 两源同 code 各一行，互不覆盖 `source`。
4. 刷新页面后 `active_source` 偏好仍在（localStorage 或账号偏好）。
5. 关闭 Tushare 时不参与采集与切换列表（或切换时提示未启用）。

## 主要改动面

- Alembic：`themes` 唯一约束  
- Scrapers：`_save_themes` 按 `(source, code)`；`full_race` 多源即时 commit  
- Theme repository/API：`source` 过滤  
- Dashboard：源切换 + 竞速进度文案  
- 测试：迁移语义、commit 不串源、列表过滤、竞速多 commit  

## 风险

- 题材总数统计会按源变化（818 可能变成「当前源」计数）。
- 短线雷达/策略若未带 source，首期需明确：跟随 `active_source` 或仍绑东财；**默认跟随 active_source**。
