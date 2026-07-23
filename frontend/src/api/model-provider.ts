import { apiClient } from '@/api/client'

export type ModelProtocol = 'openai_compatible' | 'anthropic' | 'gemini' | 'ollama'

export interface ModelProvider {
  id: number
  name: string
  protocol: ModelProtocol
  base_url: string
  model: string
  api_key: string
  has_api_key: boolean
  custom_headers: Record<string, string>
  custom_header_names: string[]
  timeout_seconds: number
  temperature: number
  max_tokens: number
  enabled: boolean
  is_default: boolean
}

export interface ModelProviderInput {
  name: string
  protocol: ModelProtocol
  base_url: string
  api_key: string
  model: string
  custom_headers: Record<string, string>
  timeout_seconds: number
  temperature: number
  max_tokens: number
  enabled: boolean
  is_default: boolean
}

export async function fetchModelProviders(): Promise<ModelProvider[]> {
  const { data } = await apiClient.get<ModelProvider[]>('/model-providers')
  return data
}

export async function saveModelProvider(
  input: ModelProviderInput,
  id?: number
): Promise<ModelProvider> {
  const { data } = id
    ? await apiClient.put<ModelProvider>(`/model-providers/${id}`, input)
    : await apiClient.post<ModelProvider>('/model-providers', input)
  return data
}

export async function deleteModelProvider(id: number): Promise<void> {
  await apiClient.delete(`/model-providers/${id}`)
}

export async function testModelProvider(id: number): Promise<string> {
  const { data } = await apiClient.post<{ message: string }>(
    `/model-providers/${id}/test`,
    undefined,
    {
      timeout: 300_000,
    }
  )
  return data.message
}

export async function fetchProviderModels(id: number): Promise<string[]> {
  const { data } = await apiClient.get<{ models: string[] }>(`/model-providers/${id}/models`, {
    timeout: 60_000,
  })
  return data.models
}
