import { describe, expect, it } from 'vitest'

import { matchPresetId, PROVIDER_PRESETS, requiresFixedTemperature } from './providerPresets'

describe('providerPresets', () => {
  it('includes domestic OpenAI-compatible presets with base urls', () => {
    const domestic = PROVIDER_PRESETS.filter((p) => p.group === 'domestic')
    expect(domestic.map((p) => p.id)).toEqual([
      'deepseek',
      'qwen',
      'zhipu',
      'moonshot',
      'siliconflow',
    ])
    for (const preset of domestic) {
      expect(preset.protocol).toBe('openai_compatible')
      expect(preset.base_url.startsWith('https://')).toBe(true)
      expect(preset.model.length).toBeGreaterThan(0)
    }
  })

  it('matches saved deepseek and qwen urls back to presets', () => {
    expect(matchPresetId('openai_compatible', 'https://api.deepseek.com')).toBe('deepseek')
    expect(
      matchPresetId(
        'openai_compatible',
        'https://dashscope.aliyuncs.com/compatible-mode/v1/'
      )
    ).toBe('qwen')
    expect(matchPresetId('anthropic', 'https://api.anthropic.com')).toBe('anthropic')
    expect(matchPresetId('openai_compatible', 'https://custom.proxy.dev/v1')).toBe(
      'openai_compatible'
    )
  })

  it('detects models that require temperature=1', () => {
    expect(requiresFixedTemperature('deepseek-reasoner')).toBe(true)
    expect(requiresFixedTemperature('deepseek-v4-pro')).toBe(true)
    expect(requiresFixedTemperature('deepseek-chat')).toBe(false)
  })
})
