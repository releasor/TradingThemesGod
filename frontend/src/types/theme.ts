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
  lifecycle_stage?:
    | 'germination'
    | 'fermentation'
    | 'climax'
    | 'divergence'
    | 'ebb'
    | null
  strength_score?: number | null
  lifecycle_confidence?: number | null
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

export interface SourceReference {
  title: string
  url: string
  publisher: string | null
  published_at: string | null
}

export interface ConceptStockLink {
  code: string
  name: string
  relation_type: string
  rationale: string
  relevance_score: number
  is_core: boolean
  sources: SourceReference[]
}

export interface ConceptNode {
  id: number
  name: string
  node_type: string
  description: string | null
  chain_level: 'upstream' | 'midstream' | 'downstream' | null
  market_logic: string | null
  catalysts: string[]
  risks: string[]
  sources: SourceReference[]
  confidence: number
  depth: number
  stocks: ConceptStockLink[]
  children: ConceptNode[]
}

export interface ConceptGraph {
  roots: ConceptNode[]
  node_count: number
  stock_count: number
  max_depth: number
  updated_at: string | null
}

export interface ConceptGraphRefreshResponse {
  theme_id: number
  theme_name: string
  source_count: number
  added_nodes: number
  updated_nodes: number
  stock_links: number
  elapsed_ms: number
  refreshed_at: string
  message: string
}

export interface ConceptGraphBatchItem {
  theme_id: number
  success: boolean
  result: ConceptGraphRefreshResponse | null
  error: string | null
}

export interface ThemeSourceReference {
  title: string
  url: string
  publisher: string | null
  published_at: string | null
}

export interface ThemeProfile {
  definition: string
  core_logic: string
  applications: string[]
  catalysts: string[]
  risks: string[]
  sources: ThemeSourceReference[]
  generated_at: string
}

export interface ThemeDriverEvent {
  id: number
  title: string
  summary: string
  source: string
  url: string
  published_at: string
  relevance_score: number
  crawled_at: string
}

export interface ThemeMarketSnapshot {
  trade_date: string
  up_count: number
  down_count: number
  flat_count: number
  suspended_count: number
  limit_up_count: number | null
  limit_down_count: number | null
  calculated_at: string
  up_down_ratio: number | null
  up_down_display: string
}

export interface ThemeInsightRefreshResponse {
  theme_id: number
  theme_name: string
  profile_updated: boolean
  candidate_events: number
  inserted_events: number
  updated_events: number
  ignored_events: number
  successful_sources: string[]
  failed_sources: string[]
  degraded: boolean
  elapsed_ms: number
  refreshed_at: string
  message: string
  model_name?: string | null
  model_error?: string | null
  model_reasoning?: string | null
  model_raw_response?: string | null
  source_count?: number
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
  chain_stock_counts: {
    upstream: number
    midstream: number
    downstream: number
  }
  concept_graph: ConceptGraph
  profile: ThemeProfile | null
  recent_driver_events: ThemeDriverEvent[]
  market_snapshot: ThemeMarketSnapshot | null
  lifecycle_stage?:
    | 'germination'
    | 'fermentation'
    | 'climax'
    | 'divergence'
    | 'ebb'
    | null
  strength_score?: number | null
  lifecycle_confidence?: number | null
  limit_quality_score?: number | null
  flow_score?: number | null
  leader_clarity_score?: number | null
  breadth_score?: number | null
}
