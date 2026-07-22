import { beforeEach, describe, expect, it } from 'vitest'
import { useNewsChannelStore } from './newsChannels'

describe('useNewsChannelStore', () => {
  beforeEach(() => {
    localStorage.clear()
    useNewsChannelStore.setState({ disabledSources: [] })
  })

  it('disables and re-enables an individual source', () => {
    useNewsChannelStore.getState().toggleSource('新浪财经')
    expect(useNewsChannelStore.getState().disabledSources).toEqual(['新浪财经'])

    useNewsChannelStore.getState().toggleSource('新浪财经')
    expect(useNewsChannelStore.getState().disabledSources).toEqual([])
  })

  it('keeps newly discovered sources enabled by default', () => {
    useNewsChannelStore.setState({ disabledSources: ['新浪财经'] })

    expect(useNewsChannelStore.getState().isSourceEnabled('财联社')).toBe(true)
    expect(useNewsChannelStore.getState().isSourceEnabled('新浪财经')).toBe(false)
  })
})
