import type { ModelProtocol } from '@/api/model-provider'

export type ProviderPresetId =
  | 'openai_compatible'
  | 'deepseek'
  | 'qwen'
  | 'zhipu'
  | 'moonshot'
  | 'siliconflow'
  | 'anthropic'
  | 'gemini'
  | 'ollama'

export type ProviderPreset = {
  id: ProviderPresetId
  label: string
  hint: string
  group: 'domestic' | 'general'
  protocol: ModelProtocol
  /** 选中时写入；空字符串表示不强制覆盖 */
  base_url: string
  model: string
  defaultName: string
}

/** 协议下拉用的厂商预设；国产多为 OpenAI 兼容端点，选中后自动填充地址与模型。 */
export const PROVIDER_PRESETS: ProviderPreset[] = [
  {
    id: 'deepseek',
    label: 'DeepSeek',
    hint: '深度求索官方',
    group: 'domestic',
    protocol: 'openai_compatible',
    base_url: 'https://api.deepseek.com',
    model: 'deepseek-chat',
    defaultName: 'DeepSeek',
  },
  {
    id: 'qwen',
    label: '通义千问',
    hint: '阿里云 DashScope 兼容模式',
    group: 'domestic',
    protocol: 'openai_compatible',
    base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    model: 'qwen-plus',
    defaultName: '通义千问',
  },
  {
    id: 'zhipu',
    label: '智谱 GLM',
    hint: 'BigModel 开放平台',
    group: 'domestic',
    protocol: 'openai_compatible',
    base_url: 'https://open.bigmodel.cn/api/paas/v4',
    model: 'glm-4-flash',
    defaultName: '智谱 GLM',
  },
  {
    id: 'moonshot',
    label: '月之暗面 Kimi',
    hint: 'Moonshot 官方',
    group: 'domestic',
    protocol: 'openai_compatible',
    base_url: 'https://api.moonshot.cn/v1',
    model: 'moonshot-v1-8k',
    defaultName: 'Kimi',
  },
  {
    id: 'siliconflow',
    label: '硅基流动',
    hint: '聚合多家开源模型',
    group: 'domestic',
    protocol: 'openai_compatible',
    base_url: 'https://api.siliconflow.cn/v1',
    model: 'deepseek-ai/DeepSeek-V3',
    defaultName: '硅基流动',
  },
  {
    id: 'openai_compatible',
    label: 'OpenAI 兼容 / 中转端',
    hint: '通用兼容端点，自行填写地址',
    group: 'general',
    protocol: 'openai_compatible',
    base_url: '',
    model: '',
    defaultName: '',
  },
  {
    id: 'anthropic',
    label: 'Anthropic',
    hint: 'Claude 官方或兼容端',
    group: 'general',
    protocol: 'anthropic',
    base_url: 'https://api.anthropic.com',
    model: 'claude-sonnet-4-5',
    defaultName: 'Anthropic',
  },
  {
    id: 'gemini',
    label: 'Gemini',
    hint: 'Google AI Studio',
    group: 'general',
    protocol: 'gemini',
    base_url: 'https://generativelanguage.googleapis.com',
    model: 'gemini-2.0-flash',
    defaultName: 'Gemini',
  },
  {
    id: 'ollama',
    label: 'Ollama',
    hint: '本地推理服务',
    group: 'general',
    protocol: 'ollama',
    base_url: 'http://127.0.0.1:11434',
    model: 'llama3.2',
    defaultName: 'Ollama',
  },
]

export function getPreset(id: ProviderPresetId): ProviderPreset {
  return (
    PROVIDER_PRESETS.find((p) => p.id === id) ??
    PROVIDER_PRESETS.find((p) => p.id === 'openai_compatible')!
  )
}

/** 根据已保存的协议与地址反推预设，用于编辑回显。 */
export function matchPresetId(protocol: ModelProtocol, baseUrl: string): ProviderPresetId {
  const normalized = baseUrl.trim().replace(/\/+$/, '').toLowerCase()

  if (protocol !== 'openai_compatible') {
    const byProtocol = PROVIDER_PRESETS.find(
      (p) => p.group === 'general' && p.protocol === protocol
    )
    return byProtocol?.id ?? 'openai_compatible'
  }

  for (const preset of PROVIDER_PRESETS) {
    if (preset.group !== 'domestic' || !preset.base_url) continue
    const target = preset.base_url.replace(/\/+$/, '').toLowerCase()
    if (normalized === target || normalized.startsWith(`${target}/`)) {
      return preset.id
    }
  }

  return 'openai_compatible'
}

/** 与后端 OpenAICompatibleAdapter.requires_fixed_temperature 保持一致。 */
export function requiresFixedTemperature(model: string): boolean {
  const name = model.trim().toLowerCase()
  if (!name) return false
  const needles = [
    'reasoner',
    'deepseek-r1',
    'deepseek-v4',
    '-thinking',
    'thinking-',
    'o1-pro',
    'o1-mini',
    'o1-preview',
    'o3-mini',
    'o3-pro',
    'o4-mini',
  ]
  if (needles.some((n) => name.includes(n))) return true
  const token = name.includes('/') ? name.slice(name.lastIndexOf('/') + 1) : name
  return token === 'o1' || token === 'o3' || token === 'o4'
}
