/** 主线图谱 API */

import { apiClient } from '@/api/client'
import type {
  MainlineGraphAcceptEdgeRequest,
  MainlineGraphCreateDraftRequest,
  MainlineGraphEdgeItem,
  MainlineGraphEnsureRequest,
  MainlineGraphEnsureResponse,
  MainlineGraphPatchEdgesRequest,
  MainlineGraphThemeConceptParams,
  MainlineGraphThemeConceptResponse,
  MainlineGraphVersionListResponse,
  MainlineGraphVersionMeta,
  MainlineGraphVersionsParams,
  MainlineGraphViewParams,
  MainlineGraphViewResponse,
} from '@/types/mainline-graph'

export async function fetchMainlineGraphView(
  params: MainlineGraphViewParams = {}
): Promise<MainlineGraphViewResponse> {
  const { data } = await apiClient.get<MainlineGraphViewResponse>('/mainline-graph/view', {
    params: {
      ...(params.trade_date ? { trade_date: params.trade_date } : {}),
      ...(params.version_id != null ? { version_id: params.version_id } : {}),
    },
  })
  return data
}

export async function fetchMainlineGraphVersions(
  params: MainlineGraphVersionsParams = {}
): Promise<MainlineGraphVersionListResponse> {
  const { data } = await apiClient.get<MainlineGraphVersionListResponse>(
    '/mainline-graph/versions',
    {
      params: {
        ...(params.trade_date ? { trade_date: params.trade_date } : {}),
      },
    }
  )
  return data
}

export async function ensureMainlineGraph(
  params: MainlineGraphEnsureRequest = {}
): Promise<MainlineGraphEnsureResponse> {
  const { data } = await apiClient.post<MainlineGraphEnsureResponse>(
    '/mainline-graph/ensure',
    {
      ...(params.trade_date ? { trade_date: params.trade_date } : {}),
      use_model: params.use_model ?? false,
    },
    { timeout: 60_000 }
  )
  return data
}

export async function createMainlineGraphDraft(
  body: MainlineGraphCreateDraftRequest = {}
): Promise<MainlineGraphVersionMeta> {
  const { data } = await apiClient.post<MainlineGraphVersionMeta>(
    '/mainline-graph/versions',
    body
  )
  return data
}

export async function patchMainlineGraphEdges(
  versionId: number,
  body: MainlineGraphPatchEdgesRequest
): Promise<MainlineGraphViewResponse> {
  const { data } = await apiClient.patch<MainlineGraphViewResponse>(
    `/mainline-graph/versions/${versionId}/edges`,
    body
  )
  return data
}

export async function publishMainlineGraphVersion(
  versionId: number
): Promise<MainlineGraphVersionMeta> {
  const { data } = await apiClient.post<MainlineGraphVersionMeta>(
    `/mainline-graph/versions/${versionId}/publish`
  )
  return data
}

export async function acceptMainlineGraphEdge(
  edgeId: number,
  body: MainlineGraphAcceptEdgeRequest
): Promise<MainlineGraphEdgeItem> {
  const { data } = await apiClient.post<MainlineGraphEdgeItem>(
    `/mainline-graph/edges/${edgeId}/accept`,
    body
  )
  return data
}

export async function fetchMainlineThemeConcept(
  themeId: number,
  params: MainlineGraphThemeConceptParams = {}
): Promise<MainlineGraphThemeConceptResponse> {
  const { data } = await apiClient.get<MainlineGraphThemeConceptResponse>(
    `/mainline-graph/themes/${themeId}/concept`,
    {
      params: {
        ...(params.trade_date ? { trade_date: params.trade_date } : {}),
      },
      // 读库本身很快；若后端被旧版长事务占满，默认 10s 会误报超时
      timeout: 30_000,
    }
  )
  return data
}
