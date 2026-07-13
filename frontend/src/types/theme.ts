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

/** 题材列表查询参数 */
export interface ThemeListParams {
  page: number
  page_size: number
  sort_by: 'heat_index' | 'rise_fall_pct' | 'stock_count' | 'name'
  sort_order: 'asc' | 'desc'
  category?: string
  tags?: string
  q?: string
}

/** 题材列表响应（带分页） */
export interface ThemeListResponse {
  items: ThemeBrief[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

/** 题材分类列表响应 */
export interface ThemeCategoriesResponse {
  categories: string[]
}

/** 产业链环节简要信息 */
export interface IndustryChainBrief {
  id: number
  level: 'upstream' | 'midstream' | 'downstream'
  name: string
  description: string | null
  representative_companies: string[] | Record<string, unknown> | null
  sort_order: number
}

/** 题材详情响应 */
export interface ThemeDetailResponse {
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
  created_at: string
  updated_at: string
  industry_chains: {
    upstream: IndustryChainBrief[]
    midstream: IndustryChainBrief[]
    downstream: IndustryChainBrief[]
  }
}
