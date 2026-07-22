import { describe, it, expect, beforeEach } from 'vitest'
import { useDashboardStore } from './dashboard'

describe('useDashboardStore', () => {
  beforeEach(() => {
    // 重置 store 到初始状态
    useDashboardStore.setState({
      limit: 20,
      showCharts: true,
      showStats: true,
    })
  })

  it('has correct initial state', () => {
    const state = useDashboardStore.getState()
    expect(state.limit).toBe(20)
    expect(state.showCharts).toBe(true)
    expect(state.showStats).toBe(true)
  })

  it('setLimit updates the limit', () => {
    useDashboardStore.getState().setLimit(50)
    expect(useDashboardStore.getState().limit).toBe(50)
  })

  it('toggleCharts toggles showCharts', () => {
    const { toggleCharts } = useDashboardStore.getState()

    toggleCharts()
    expect(useDashboardStore.getState().showCharts).toBe(false)

    toggleCharts()
    expect(useDashboardStore.getState().showCharts).toBe(true)
  })

  it('toggleStats toggles showStats', () => {
    const { toggleStats } = useDashboardStore.getState()

    toggleStats()
    expect(useDashboardStore.getState().showStats).toBe(false)

    toggleStats()
    expect(useDashboardStore.getState().showStats).toBe(true)
  })

  it('setLimit to various values', () => {
    const { setLimit } = useDashboardStore.getState()

    setLimit(10)
    expect(useDashboardStore.getState().limit).toBe(10)

    setLimit(100)
    expect(useDashboardStore.getState().limit).toBe(100)

    setLimit(1)
    expect(useDashboardStore.getState().limit).toBe(1)
  })
})
