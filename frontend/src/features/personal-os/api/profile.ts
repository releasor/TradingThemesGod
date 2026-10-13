import { apiClient } from '@/api/client'

export type MemoryPolicy = {
  inject_profile: boolean
  note_top_k: number
  recent_turns: number
}

export type ModuleFlags = {
  chat: boolean
  memory: boolean
  journal: boolean
  reports: boolean
  decisions: boolean
}

export type ModelPrefs = {
  default_provider_id: number | null
  compare_provider_ids: number[]
}

export type OsProfile = {
  id: number
  user_id: number
  display_name: string | null
  goals: string | null
  health_baseline: Record<string, unknown>
  system_prompt: string
  memory_policy: MemoryPolicy
  module_flags: ModuleFlags
  model_prefs: ModelPrefs
  report_prompt_appendix: string | null
  decision_prompt_appendix: string | null
  created_at: string
  updated_at: string
}

export async function fetchOsProfile(): Promise<OsProfile> {
  const { data } = await apiClient.get<OsProfile>('/os/profile')
  return normalizeProfile(data)
}

export async function updateOsProfile(
  input: Partial<{
    display_name: string | null
    goals: string | null
    health_baseline: Record<string, unknown>
    system_prompt: string
    memory_policy: MemoryPolicy
    module_flags: ModuleFlags
    model_prefs: ModelPrefs
    report_prompt_appendix: string | null
    decision_prompt_appendix: string | null
  }>
): Promise<OsProfile> {
  const { data } = await apiClient.patch<OsProfile>('/os/profile', input)
  return normalizeProfile(data)
}

function normalizeProfile(data: OsProfile): OsProfile {
  return {
    ...data,
    report_prompt_appendix: data.report_prompt_appendix ?? null,
    decision_prompt_appendix: data.decision_prompt_appendix ?? null,
    memory_policy: {
      inject_profile: data.memory_policy?.inject_profile ?? true,
      note_top_k: data.memory_policy?.note_top_k ?? 5,
      recent_turns: data.memory_policy?.recent_turns ?? 20,
    },
    module_flags: {
      chat: data.module_flags?.chat ?? true,
      memory: data.module_flags?.memory ?? true,
      journal: data.module_flags?.journal ?? true,
      reports: data.module_flags?.reports ?? true,
      decisions: data.module_flags?.decisions ?? true,
    },
    model_prefs: {
      default_provider_id: data.model_prefs?.default_provider_id ?? null,
      compare_provider_ids: data.model_prefs?.compare_provider_ids ?? [],
    },
  }
}
