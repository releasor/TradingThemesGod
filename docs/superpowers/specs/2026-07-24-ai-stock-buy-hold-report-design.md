# AI 个股买入/持有研判报告设计

## 背景与目标

当前 `/ai-analysis` 页面把短线概览、热门题材、新闻、一进二候选和个股详情在前端拼成模板文案，**并未调用用户配置的 LLM**。按钮「纳入个股研判」仅拉取个股详情并改写一段定位说明，无法回答：

- 是否值得买入；
- 更适合短线、波段还是中长线持有；
- 综合市场上下文后给出可阅读的完整研判报告。

本次目标：在用户登录且已配置默认模型的前提下，服务端聚合上下文并调用 LLM，产出**结构化结论卡 + 完整报告正文**；按用户与股票代码缓存最近一份，支持手动重新生成。无模型时明确提示，不静默用规则模板冒充 AI 结论。

## 范围

### 本次包含

- 新增 `stock_ai_reports` 表及 Alembic 迁移（每用户每股票最多一份最新报告）；
- 后端服务：聚合个股、短线概览、热门/涨幅题材、新闻、一进二候选（若可用）→ 调默认模型 → 校验结构化 JSON → 落库；
- API：`GET` / `POST /api/v1/stocks/{code}/ai-report`（需登录）；
- 前端 `/ai-analysis`：改为「生成 AI 研判」流程；展示结论卡 + 报告正文；未登录 / 无默认模型给出提示与跳转；有缓存先展示并可「重新生成」；
- 保留现有规则拼装面板为可折叠「市场上下文」参考，文案标明非 AI 结论；
- 后端与前端相关单测 / API 测。

### 本次不包含

- LLM 流式输出（SSE）；沿用现有 `adapter.complete()` 一次性返回；
- 报告历史列表（仅保留最近一份）；
- 全局兜底 API Key（未登录或无用户模型时不生成）；
- 龙虎榜真实数据源接入（上下文中可继续用现有代理说明）；
- 自动定时为全市场个股生成报告；
- 将报告视为投资建议的合规产品化（仅在 UI/响应中附免责声明）。

## 总体架构

```text
[AiStockAnalysis UI]
    │  GET  读缓存
    │  POST 生成 / 强制刷新
    ▼
[stock API] ──auth──► StockAiReportService
                          │
                          ├─ StockService / ShortTermService / Theme / News / FirstToSecond
                          ├─ ModelProviderService.get_default() + adapter.complete()
                          ├─ parse_model_json + Pydantic 校验
                          └─ StockAiReportRepository upsert (user_id, stock_code)
```

与题材洞察一致：密钥与模型调用留在后端；前端只传股票代码与可选 `force`。

## 数据模型

### `stock_ai_reports`

每个用户、每只股票最多一条最新报告：

| 字段 | 说明 |
|------|------|
| `id` | 自增主键 |
| `user_id` | 用户外键，级联删除 |
| `stock_code` | 6 位代码，索引 |
| `stock_name` | 生成时快照名称，可空 |
| `verdict` | `buy` \| `watch` \| `avoid` |
| `horizon_short` | 短线适配简述 |
| `horizon_swing` | 波段适配简述 |
| `horizon_medium_long` | 中长线适配简述 |
| `confidence` | 0–100 |
| `summary` | 一句话核心结论 |
| `sections` | JSON：各章节正文 |
| `full_report` | 连贯完整报告正文 |
| `context_digest` | JSON：生成时上下文摘要（题材名、情绪等），便于审计，不必回放全文 |
| `model_provider_id` | 可选，生成所用 provider |
| `model_name` | 生成所用模型名快照 |
| `elapsed_ms` | 生成耗时 |
| `generated_at` | 成功生成时间 |
| `created_at` / `updated_at` | 通用时间字段 |

唯一约束：`(user_id, stock_code)`。查询索引：`user_id`、`stock_code`、`generated_at`。

## API

均需 `get_current_user`。`code` 必须匹配 `^\d{6}$`。

### `GET /api/v1/stocks/{code}/ai-report`

返回该用户该股最近缓存；无记录时 **404**（前端视为「尚未生成」）。

响应：`StockAiReportResponse`，字段与结论卡/报告一一对应：

- `code`、`stock_name`
- `verdict`、`horizon`（`short` / `swing` / `medium_long`，各含 `fit` + `note`）
- `confidence`、`summary`、`sections`、`full_report`
- `model_name`、`generated_at`、`elapsed_ms`
- `disclaimer`（固定中文免责声明）

### `POST /api/v1/stocks/{code}/ai-report`

生成或刷新报告。

请求体（可选）：

```json
{ "force": false }
```

约定（避免前后端各写一套）：

- 前端进入某股时优先 `GET`；404 再 `POST { force: false }` 首次生成。
- 「重新生成」一律 `POST { force: true }`。
- 服务端：`force=false` 且已有缓存时直接返回缓存，不重复计费；`force=true` 始终重新调用模型。

行为：

1. 校验股票存在；不存在 404。
2. 若 `force=false` 且已有缓存 → 直接返回缓存。
3. 解析默认模型；无默认或未启用 → **409**，detail 明确提示去模型设置配置。
4. 聚合上下文（见下）→ 调 LLM（`json_mode=True`，超时建议 ≥120s，`max_tokens` 足够覆盖长文）。
5. 解析失败或校验失败 → **502**，不覆盖旧缓存。
6. Upsert 后返回 `StockAiReportResponse`，附 `elapsed_ms`。

前端 axios 超时与题材洞察一致（约 300s）。

## 上下文聚合（服务端）

至少包含：

- 个股详情（价格、涨跌、行业、最近事件）；
- 短线概览 / 策略卡（情绪、展望、建议、指数与情绪强度）；
- 热门题材 Top N、涨幅题材 Top N（名称、涨跌、热度）；
- 新闻标题/摘要 Top N；
- 一进二 / 异动候选（调用失败则标记 `missing_sources`，不阻断生成）；
- 固定免责声明指令：非投资建议，只能依据输入事实推断。

上下文文本总长度需截断（对齐 concept graph 量级，避免爆 token）。

## LLM 输出契约

System：A 股短线/波段研究员；只依据输入；输出严格 JSON；必须含免责意识（报告内注明「供参考，非投资建议」）。

JSON 字段：

```json
{
  "verdict": "buy|watch|avoid",
  "horizon": {
    "short": { "fit": "suitable|neutral|unsuitable", "note": "..." },
    "swing": { "fit": "suitable|neutral|unsuitable", "note": "..." },
    "medium_long": { "fit": "suitable|neutral|unsuitable", "note": "..." }
  },
  "confidence": 0,
  "summary": "...",
  "sections": {
    "trend": "...",
    "emotion_rotation": "...",
    "themes_catalysts": "...",
    "stock_position": "...",
    "scenarios_actions": "...",
    "risks": "..."
  },
  "full_report": "连贯完整正文……"
}
```

落库时将 `horizon.*.note` 写入对应列；`fit` 可并入 note 前缀或存入 `sections` 旁的扩展 JSON（实现时优先：horizon 列存「适合/中性/不适合 — note」拼接，`sections` 保持纯章节）。

## 前端 UX

1. 输入 6 位代码；主按钮文案：**生成 AI 研判**。
2. 未登录：提示登录，禁用生成。
3. 已登录、点生成：
   - 先 `GET`；有缓存则展示并显示「生成于 …」+ **重新生成**；
   - 无缓存则 `POST`；
   - 409 → 提示去 `/settings/models`；
   - 其他错误 → 明确错误文案。
4. **结论卡**：verdict 中文标签（买入/观望/回避）、三档持有适配、信心分、summary。
5. **完整报告**：优先渲染 `full_report`；其下可展开 `sections` 分节。
6. **市场上下文**：现有 `buildAiAnalysisReport` 面板折叠收起，标题注明「规则汇总 · 非 AI 结论」。
7. 页脚免责声明固定展示。

## 错误与降级

| 情况 | 行为 |
|------|------|
| 未登录 | 前端拦截；API 401 |
| 无默认模型 | 409 + 引导文案 |
| 股票不存在 | 404 |
| 模型超时/失败 | 502，保留旧缓存 |
| 一进二等子源失败 | 仍生成，context 标注缺失 |

## 测试要点

- Service：有/无 provider；JSON 校验失败不覆盖旧报告；upsert 唯一键。
- API：401/404/409/200；force 刷新更新 `generated_at`。
- 前端：未登录提示；无模型 409 提示；有缓存展示；重新生成调用 `force=true`；结论卡与报告渲染。

## 风险与约束

- 长上下文与 `max_tokens` 可能导致耗时与费用上升；需截断与超时配置。
- 模型幻觉：提示词强调「仅依据输入」；UI 免责声明。
- 不把规则模板结果在无模型时标为「AI 报告」。
