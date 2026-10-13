import { apiClient } from '@/api/client'

export type OsDecisionOption = {
  id: number
  run_id: number
  tier: string
  title: string
  content: string
  provider_id: number | null
  raw_reply: string | null
  selected: boolean
  feedback_score: number | null
  feedback_note: string | null
  created_at: string
}

export type OsDecisionRun = {
  id: number
  thread_id: number
  summary: string | null
  provider_ids: number[]
  options: OsDecisionOption[]
  created_at: string
  updated_at: string
}

export type OsDecisionThread = {
  id: number
  user_id: number
  question: string
  constraints: string | null
  status: string
  chosen_option_id: number | null
  outcome_note: string | null
  created_at: string
  updated_at: string
  latest_run: OsDecisionRun | null
}

export async function listOsDecisions(): Promise<OsDecisionThread[]> {
  const { data } = await apiClient.get<OsDecisionThread[]>('/os/decisions')
  return data
}

export async function createOsDecision(input: {
  question: string
  constraints?: string
}): Promise<OsDecisionThread> {
  const { data } = await apiClient.post<OsDecisionThread>('/os/decisions', input)
  return data
}

export async function runOsDecision(
  threadId: number,
  input?: { provider_ids?: number[]; summarize_provider_id?: number | null }
): Promise<OsDecisionThread> {
  const { data } = await apiClient.post<OsDecisionThread>(
    `/os/decisions/${threadId}/run`,
    input ?? {},
    { timeout: 180_000 }
  )
  return data
}

export async function chooseOsDecision(
  threadId: number,
  input: { option_id: number; outcome_note?: string }
): Promise<OsDecisionThread> {
  const { data } = await apiClient.post<OsDecisionThread>(
    `/os/decisions/${threadId}/choose`,
    input
  )
  return data
}

export async function feedbackOsDecisionOption(
  optionId: number,
  input: { score: number; note?: string; apply_to_prompt?: boolean }
): Promise<OsDecisionOption> {
  const { data } = await apiClient.post<OsDecisionOption>(
    `/os/decisions/options/${optionId}/feedback`,
    { apply_to_prompt: true, ...input }
  )
  return data
}

export type OsScoutTemplate = {
  id: string
  title: string
  question: string
  constraints: string
  hint: string
}

export async function listOsDecisionTemplates(): Promise<OsScoutTemplate[]> {
  const { data } = await apiClient.get<OsScoutTemplate[]>('/os/decision-templates')
  return data
}
