/** 股票相关类型定义
 *
 * 与后端 schemas/stock.py 保持一致。
 */

/** 事件简要信息 */
export interface EventBrief {
  id: number
  title: string
  content: string | null
  source: string | null
  event_type: string | null
  published_at: string | null
}

/** 事件列表项（不含 content，减少列表响应体积） */
export interface EventListItem {
  id: number
  title: string
  source: string | null
  event_type: string | null
  published_at: string | null
}

/** 股票简要信息（列表用） */
export interface StockBrief {
  id: number
  code: string
  name: string
  industry: string | null
  market_cap: number | null
  current_price: number | null
  rise_fall_pct: number | null
  exchange: string | null
}

/** 股票详情响应 */
export interface StockDetailResponse {
  id: number
  code: string
  name: string
  industry: string | null
  market_cap: number | null
  current_price: number | null
  rise_fall_pct: number | null
  exchange: string | null
  created_at: string
  updated_at: string
  recent_events: EventListItem[]
}

/** 股票列表响应 */
export interface StockListResponse {
  items: StockBrief[]
  total: number
  page: number
  page_size: number
  total_pages: number
}
