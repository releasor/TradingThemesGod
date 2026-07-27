# A 股交易日历设计

## 背景

复盘台、短线雷达、题材挖掘、主线图谱等均依赖「最近有效交易日」。当前实现仅把周六/周日回退到周五（`ShortTermService.resolve_trade_date`、前端 `marketClock` / `ReviewDesk.resolveTradeDateIso`），**不含法定节假日**。国庆、春节等休市日会被误判为交易日，导致空快照、降级投影或错误数据日。

项目已依赖 AKShare，可拉取新浪源 A 股历史开市日；此前产品决策确认：

| 决策点 | 选择 |
|--------|------|
| 范围 | 前后端共用真实交易日；设置页可同步 |
| 存储 | 落库缓存 |
| 数据源 | 网上拉取（AKShare），不做单日手改/覆盖 |
| 同步 | 启动后台按需同步 + 设置页「同步交易日历」强制刷新 |
| 失败策略 | 用库内旧数据；库空则周末兜底并标记 degraded |

## 目标

1. 提供权威的「是否开市日 / 上一开市日 / 解析交易日」能力，全站统一。
2. 将 AKShare 开市日全量写入数据库，支持离线回退与多 worker 共享。
3. 设置页展示同步状态并支持一键强制同步。
4. 前端复盘日期与盘中状态（`marketClock`）与后端日历一致。

## 范围

### 本次包含

- 迁移与模型：`trading_calendar_days`、`trading_calendar_meta`（单行元信息）
- 领域模块：`TradingCalendar`（`is_trade_day` / `previous_trade_day` / `resolve_trade_date` / `list_trade_days`）
- 同步服务：AKShare `tool_trade_date_hist_sina` → upsert；启动 lifespan 按需同步；`POST` 强制同步
- API：`/api/v1/market/calendar/status`、`/resolve`、`/sync`
- 接线：`ShortTermService.resolve_trade_date` 及复盘/挖矿/主线等委托；`_period_trade_dates`、`_previous_weekday` 等周末逻辑改为日历
- 前端：设置页日历卡片；`marketClock` / 复盘台优先走 status/resolve
- 测试：解析节假日回退、空库兜底、同步 upsert、API、前端 resolve

### 本次不包含

- 单日开市/休市手动覆盖
- 按年可视化日历网格
- 港股/美股日历
- 用行情 `f124` 充当日历源
- 推送「明日休市」通知

## 与已有文档关系

- **替换** 各规格中「非交易日 → 最近有数据日 / 周末回退」的实现口径：统一走本日历；「有数据日」仍可作为无日历数据时的二级兜底（可选，本版以日历 + 周末兜底为主）。
- 复盘台 `2026-07-26-review-desk-event-sourcing-design.md` 中的 `resolve_trade_date` 语义升级为含节假日。
- 短线雷达 `2026-07-25-theme-lifecycle-short-term-radar-design.md` / `2026-07-21-short-term-opportunity-radar-design.md` 中「非交易日默认最近交易日」由本模块落地。
- 前端 `marketClock.ts` 注释中的「不含法定节假日」在本版消除。

## 总体架构

```text
AKShare tool_trade_date_hist_sina
        │
        ▼
TradingCalendarSyncService.sync()
        │
        ├─ trading_calendar_days (trade_date PK)
        └─ trading_calendar_meta (last_synced_at, row_count, last_error, source)
        │
        ▼
TradingCalendar.resolve / is_trade_day / previous_trade_day
        │
        ├─ ShortTermService.resolve_trade_date
        ├─ Review / Mining / MainlineGraph / FirstToSecond
        ├─ GET /market/calendar/status|resolve
        └─ POST /market/calendar/sync
                │
                ▼
Frontend: settings sync card + marketClock + ReviewDesk
```

## 数据模型

### `trading_calendar_days`

| 列 | 类型 | 说明 |
|----|------|------|
| `trade_date` | `DATE` PK | 开市日 |
| `source` | `VARCHAR(32)` | 默认 `akshare_sina` |
| `synced_at` | `TIMESTAMPTZ` | 本行写入/更新时间 |

无「休市日」负表：不在表中的日期视为非开市日（在已同步覆盖的年份范围内）。覆盖区间由 meta 与 `MIN/MAX(trade_date)` 表达。

### `trading_calendar_meta`

单行（`id=1`）元信息：

| 列 | 类型 | 说明 |
|----|------|------|
| `id` | `INT` PK | 固定 1 |
| `source` | `VARCHAR(32)` | 最近同步源 |
| `last_synced_at` | `TIMESTAMPTZ` NULL | 最近成功同步时间 |
| `row_count` | `INT` | 成功同步后的行数 |
| `min_date` / `max_date` | `DATE` NULL | 覆盖区间 |
| `last_error` | `TEXT` NULL | 最近一次失败信息（成功则清空） |
| `updated_at` | `TIMESTAMPTZ` | |

## 同步行为

1. **源**：`akshare.tool_trade_date_hist_sina()`（在线程池中调用，避免阻塞 event loop）。
2. **写入**：解析为 `date` 集合后，事务内全量替换或 upsert（推荐：truncate + bulk insert，或 `INSERT ... ON CONFLICT DO UPDATE`）；更新 meta。
3. **启动**：`lifespan` 内 `asyncio.create_task`：若 `last_synced_at` 为空或距今 ≥ 24h，则同步；失败只记日志与 meta.`last_error`，不阻塞 API 启动。
4. **手动**：`POST /api/v1/market/calendar/sync` 强制同步，返回 status DTO。
5. **鉴权**：与现有设置类写操作一致（需登录）；只读 status/resolve 可匿名或与现有公开市场 API 一致（实现时对齐项目惯例）。

## 解析语义

```text
resolve(d | None) -> date
  base = d or today(Asia/Shanghai)
  while not is_trade_day(base):
    base -= 1 day
    if steps > 366 or base < cover_min - buffer: break → weekend_fallback(base)
  return base
```

- **有库数据**：非开市日（周末 + 节假日）回退到上一开市日。
- **空库或查询异常**：退回现有「仅周末回退」逻辑，并在 status 中 `degraded: true`、`missing_sources: ["trading_calendar"]`。
- **覆盖区外的未来日期**：若 `base > max_date`，先按周末回退，再在已知开市日中取 `≤ base` 的最大开市日；若仍无，周末兜底。
- `previous_trade_day(d)`：严格小于 `d` 的最大开市日（供一进二「昨板」等）。
- `_period_trade_dates(start, end)`：区间内表中开市日列表，不再 `weekday < 5`。

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/market/calendar/status` | `last_synced_at`、`row_count`、`min_date`、`max_date`、`last_error`、`degraded`、`today_is_trade_day`、`data_trade_date` |
| GET | `/api/v1/market/calendar/resolve?date=` | `{ input_date, trade_date }`；`date` 可省略 |
| POST | `/api/v1/market/calendar/sync` | 强制同步，返回 status |

## 前端

1. **设置**：在设置导航增加「交易日历」入口（或挂在账号/模型设置页一卡片）：展示同步状态、覆盖区间、错误；按钮「同步交易日历」。
2. **`marketClock`**：优先消费 `status.data_trade_date` / `today_is_trade_day`（可短缓存 1–5 分钟）；拉取失败时保留本地周末逻辑作兜底。
3. **复盘台**：`resolveTradeDateIso` 改为调用 `resolve` API，或在加载日复盘前用 status 纠正 URL；后端 `get_day` 仍二次解析，保证最终一致。

## 错误与降级

| 场景 | 行为 |
|------|------|
| AKShare 超时/空结果 | sync 失败，保留旧表，meta 记 error |
| 库无行 | resolve 周末兜底；status.`degraded=true` |
| 同步进行中重复 POST | 允许串行锁或返回「同步中」（实现选简单锁/单飞） |

## 测试要点

- 节假日（如国庆中间某周一）`resolve` → 节前最后开市日（用 fixture 注入日历行，不打真网）。
- 周末仍回退到周五。
- 空库 → 周末兜底 + degraded。
- sync mock AKShare → 行数与 meta 更新。
- 前端：status 显示；sync 按钮触发；周末/节假日 URL 纠正（可 mock API）。

## 验收标准

1. 迁移可执行；表存在且 meta 单行可初始化。
2. 手动 sync 成功后 status 显示覆盖区间与 `last_synced_at`。
3. 注入「周一非开市」fixture 后，复盘/短线 `resolve_trade_date` 回退到上周五（或上一个开市日），而非该周一。
4. 断网/mock 失败时业务 API 仍可用（周末兜底）。
5. 设置页可完成一次同步并看到成功状态。

## 交付顺序建议

1. 迁移 + ORM + repository  
2. Sync service（可 mock）+ TradingCalendar 解析  
3. 接线 `resolve_trade_date` 与 period/previous helpers  
4. API + lifespan 按需同步  
5. 前端 status/sync + marketClock / ReviewDesk  
6. 测试与冒烟  
