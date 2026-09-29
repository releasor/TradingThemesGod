import { describe, expect, it } from 'vitest'
import { filterModels, fuzzyScore } from './modelFuzzy'

describe('modelFuzzy', () => {
  it('ranks exact and prefix matches highest', () => {
    expect(fuzzyScore('grok', 'grok')).toBeGreaterThan(fuzzyScore('grok', 'grok-2'))
    expect(fuzzyScore('gpt', 'gpt-4o')).toBeGreaterThan(fuzzyScore('gpt', 'chatgpt'))
  })

  it('matches subsequence for fuzzy queries', () => {
    expect(fuzzyScore('dsk', 'deepseek-chat')).toBeGreaterThan(0)
    expect(fuzzyScore('zzz', 'deepseek-chat')).toBe(0)
  })

  it('filters and sorts models by relevance', () => {
    const models = ['claude-3', 'gpt-4o', 'gpt-4.1', 'deepseek-chat', 'grok']
    expect(filterModels(models, 'gpt')).toEqual(['gpt-4o', 'gpt-4.1'])
    expect(filterModels(models, '')).toHaveLength(5)
    expect(filterModels(models, 'xyz')).toEqual([])
  })
})
