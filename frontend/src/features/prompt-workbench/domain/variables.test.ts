import { describe, expect, it } from 'vitest'

import { extractVariables, fillVariables } from './variables'

describe('extractVariables', () => {
  it('extracts unique names in order', () => {
    expect(
      extractVariables('为 {{audience}} 写 {{format}}，再给 {{audience}}')
    ).toEqual(['audience', 'format'])
  })
})

describe('fillVariables', () => {
  it('replaces known variables', () => {
    expect(
      fillVariables('你好 {{name}}', { name: 'Alice' })
    ).toBe('你好 Alice')
  })
})
