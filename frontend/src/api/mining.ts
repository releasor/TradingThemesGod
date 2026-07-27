/** 题材挖掘 API */

import { apiClient } from '@/api/client'
import type {
  MiningBoardParams,
  MiningBoardResponse,
  MiningCardItem,
  MiningEnsureParams,
  MiningEnsureResponse,
  MiningNoteResponse,
} from '@/types/mining'

export async function fetchMiningBoard(
  params: MiningBoardParams = {}
): Promise<MiningBoardResponse> {
  const { data } = await apiClient.get<MiningBoardResponse>('/mining/board', {
    params: {
      ...(params.trade_date ? { trade_date: params.trade_date } : {}),
    },
  })
  return data
}

export async function fetchMiningCard(cardId: number): Promise<MiningCardItem> {
  const { data } = await apiClient.get<MiningCardItem>(`/mining/cards/${cardId}`)
  return data
}

export async function ensureMining(
  params: MiningEnsureParams = {}
): Promise<MiningEnsureResponse> {
  const { data } = await apiClient.post<MiningEnsureResponse>('/mining/ensure', null, {
    params: {
      ...(params.trade_date ? { trade_date: params.trade_date } : {}),
    },
    timeout: 60_000,
  })
  return data
}

export async function ensureMiningNote(cardId: number): Promise<MiningNoteResponse> {
  const { data } = await apiClient.post<MiningNoteResponse>(
    `/mining/cards/${cardId}/note/ensure`,
    null,
    { timeout: 60_000 }
  )
  return data
}
