import { describe, expect, it } from 'vitest'

import {
  EXTRA_GOAL_CHIPS,
  OPTIMIZE_FRAMEWORKS,
  OPTIMIZE_SAMPLES,
  getFrameworkMeta,
} from './frameworks'
import { lineDiff } from './lineDiff'

describe('optimize frameworks meta', () => {
  it('exposes description for every framework', () => {
    for (const fw of OPTIMIZE_FRAMEWORKS) {
      expect(fw.description.length).toBeGreaterThan(8)
      expect(getFrameworkMeta(fw.id)?.id).toBe(fw.id)
    }
  })

  it('provides goal chips and cold-start samples', () => {
    expect(EXTRA_GOAL_CHIPS.length).toBeGreaterThanOrEqual(4)
    expect(OPTIMIZE_SAMPLES.length).toBeGreaterThanOrEqual(2)
    expect(OPTIMIZE_SAMPLES[0].body.length).toBeGreaterThan(10)
  })
})

describe('lineDiff', () => {
  it('marks added and removed lines', () => {
    const diff = lineDiff('a\nb\nc', 'a\nx\nc')
    expect(diff).toEqual([
      { type: 'same', text: 'a' },
      { type: 'del', text: 'b' },
      { type: 'add', text: 'x' },
      { type: 'same', text: 'c' },
    ])
  })
})
