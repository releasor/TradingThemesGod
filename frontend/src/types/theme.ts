/** 题材相关类型定义
 *
 * 与后端 schemas/theme.py 保持一致。
 */

/** 题材简要信息（列表/排名用） */
export interface ThemeBrief {
  id: number
  name: string
  code: string
  description: string | null
  heat_index: number
  rise_fall_pct: number
  stock_count: number
  category: string | null
  tags: string[] | Record<string, unknown> | null
  source: string | null
}

/** 题材排名响应 */
export interface ThemeRankingResponse {
  items: ThemeBrief[]
  limit: number
}
