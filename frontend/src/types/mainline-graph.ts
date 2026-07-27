/** 主线图谱 API 类型 */

import type { ConceptGraph } from '@/types/theme'

export type MainlineGraphMode = 'narrative' | 'concept'

export type MainlineGraphVersionKind = 'auto' | 'draft' | 'published'

export type MainlineGraphVersionStatus = 'open' | 'published' | 'archived'

export type MainlineGraphEdgeMethod = 'rules' | 'model' | 'manual'

export type MainlineGraphEdgeStatus = 'active' | 'suggested' | 'rejected'

export type MainlineGraphNodeRole = 'mainline' | 'branch' | 'other'

export interface MainlineGraphVersionMeta {
  id: number
  trade_date: string
  kind: string
  title: string | null
  status: string
  parent_version_id: number | null
  created_by: number | null
  published_at: string | null
  meta: Record<string, unknown>
  created_at: string | null
  updated_at: string | null
}

export interface MainlineGraphNodeItem {
  id: number
  theme_id: number
  theme_name: string
  mainline_score: number
  strength_score: number
  lifecycle_stage: string
  role: string
  payload: Record<string, unknown> | null
}

export interface MainlineGraphEdgeItem {
  id: number
  from_theme_id: number
  to_theme_id: number
  weight: number
  method: string
  status: string
  rationale: string
  created_by: number | null
}

export interface MainlineGraphViewResponse {
  trade_date: string
  version: MainlineGraphVersionMeta | null
  nodes: MainlineGraphNodeItem[]
  edges: MainlineGraphEdgeItem[]
  empty: boolean
}

export interface MainlineGraphVersionListResponse {
  trade_date: string
  items: MainlineGraphVersionMeta[]
}

export interface MainlineGraphEnsureResponse {
  trade_date: string
  version_id: number
  node_count: number
  edge_count: number
  model_queued: boolean
  generated_at: string | null
  elapsed_ms: number
}

export interface MainlineGraphThemeConceptResponse {
  theme_id: number
  theme_name: string
  trade_date: string | null
  lifecycle_stage: string | null
  strength_score: number | null
  mainline_score: number | null
  concept_graph: ConceptGraph
}

export interface MainlineGraphViewParams {
  trade_date?: string
  version_id?: number
}

export interface MainlineGraphVersionsParams {
  trade_date?: string
}

export interface MainlineGraphEnsureRequest {
  trade_date?: string
  use_model?: boolean
}

export interface MainlineGraphCreateDraftRequest {
  trade_date?: string
  source_version_id?: number
  title?: string
}

export interface MainlineGraphEdgePatch {
  op: 'upsert' | 'delete'
  edge_id?: number
  from_theme_id?: number
  to_theme_id?: number
  weight?: number
  method?: string
  status?: string
  rationale?: string
}

export interface MainlineGraphPatchEdgesRequest {
  edges: MainlineGraphEdgePatch[]
}

export interface MainlineGraphAcceptEdgeRequest {
  draft_version_id: number
}

export interface MainlineGraphThemeConceptParams {
  trade_date?: string
}
