import { describe, expect, it, vi } from 'vitest'
import { apiClient } from '@/api/client'
import {
  analyzeShortTermFromDatabase,
  fetchFirstToSecondCandidates,
  fetchShortTermOverview,
  fetchShortTermSectors,
  refreshFirstToSecondCandidates,
  refreshShortTermData,
  refreshShortTermSignals,
} from './short-term'

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

describe('short-term api', () => {
  it('fetches overview with trade date', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        trade_date: '2026-07-21',
        period: 'current_week',
        period_label: '本周',
        start_date: '2026-07-20',
        end_date: '2026-07-21',
        degraded: false,
        missing_sources: [],
        market_emotion: '情绪强',
        short_term_outlook: '指数与情绪共振',
        operation_advice: '做连板',
        tracking_focus: ['连板梯队'],
        core_conclusion: '优先主线前排',
        risk_signals: [],
        sector_count: 3,
        candidate_count: 0,
        strategy_card: {
          title: '指数情绪策略卡',
          index_strength: 'strong',
          emotion_strength: 'strong',
          primary_strategy: '连板接力',
          secondary_strategy: '主升分歧接力',
          operation_advice: '指数强、情绪强，做连板。',
          focus_targets: ['连板梯队'],
          rationale: ['日均连板 28.0'],
        },
      },
    })

    const result = await fetchShortTermOverview({
      tradeDate: '2026-07-21',
      period: 'current_week',
    })

    expect(apiClient.get).toHaveBeenCalledWith('/short-term/overview', {
      params: { trade_date: '2026-07-21', period: 'current_week' },
      timeout: 30_000,
    })
    expect(result.period_label).toBe('本周')
    expect(result.strategy_card.primary_strategy).toBe('连板接力')
  })

  it('fetches overview with a custom date range', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        trade_date: '2026-07-17',
        period: 'custom',
        period_label: '自定义',
        start_date: '2026-07-03',
        end_date: '2026-07-17',
        degraded: false,
        missing_sources: [],
        market_emotion: '情绪弱',
        short_term_outlook: '指数强但情绪弱',
        operation_advice: '做补涨趋势与切换',
        tracking_focus: ['低位补涨'],
        core_conclusion: '补涨趋势与切换',
        risk_signals: ['短线情绪不足'],
        sector_count: 3,
        candidate_count: 0,
        strategy_card: {
          title: '指数情绪策略卡',
          index_strength: 'strong',
          emotion_strength: 'weak',
          primary_strategy: '补涨趋势与切换',
          secondary_strategy: '轮动低吸',
          operation_advice: '指数强但情绪弱，做补涨、趋势和高低切换。',
          focus_targets: ['低位补涨'],
          rationale: ['日均连板 3.5'],
        },
      },
    })

    const result = await fetchShortTermOverview({
      period: 'custom',
      startDate: '2026-07-03',
      endDate: '2026-07-17',
    })

    expect(apiClient.get).toHaveBeenCalledWith('/short-term/overview', {
      params: {
        period: 'custom',
        start_date: '2026-07-03',
        end_date: '2026-07-17',
      },
      timeout: 30_000,
    })
    expect(result.period_label).toBe('自定义')
  })

  it('fetches first-to-second live candidates', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        trade_date: '2026-07-21',
        previous_trade_date: '2026-07-20',
        refreshed_at: '2026-07-21T10:30:00Z',
        degraded: true,
        missing_sources: ['model_catalyst'],
        candidates: [
          {
            code: '000001',
            name: '平安银行',
            theme_name: '金融科技',
            price: 12.3,
            market_cap: 120,
            float_market_cap: 60,
            turnover_rate: 8.5,
            amount: 9.2,
            first_limit_up_at: '09:42:00',
            open_board_count: 0,
            score: 86,
            decision: 'candidate',
            matched_rules: ['今日仍在涨停池'],
            excluded_rules: [],
            risk_flags: ['模型催化缺失'],
            catalysts: ['行业催化：金融科技'],
            operation_advice: '只做换手晋级确认。',
            core_conclusion: '具备一进二观察价值。',
          },
        ],
        excluded_count: 2,
        source_status: { limit_pool: 'success' },
      },
    })

    const result = await fetchFirstToSecondCandidates({ tradeDate: '2026-07-21' })

    expect(apiClient.get).toHaveBeenCalledWith('/short-term/first-to-second', {
      params: { trade_date: '2026-07-21' },
      timeout: 300_000,
    })
    expect(result.candidates[0].code).toBe('000001')
  })

  it('refreshes first-to-second live candidates', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: {
        trade_date: '2026-07-21',
        previous_trade_date: '2026-07-20',
        refreshed_at: '2026-07-21T10:31:00Z',
        degraded: false,
        missing_sources: [],
        candidates: [],
        excluded_count: 0,
        source_status: { limit_pool: 'success' },
      },
    })

    await refreshFirstToSecondCandidates({ tradeDate: '2026-07-21' })

    expect(apiClient.post).toHaveBeenCalledWith('/short-term/first-to-second/refresh', null, {
      params: { trade_date: '2026-07-21' },
      timeout: 300_000,
    })
  })

  it('refreshes strategy card market data', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: {
        trade_date: '2026-07-21',
        period: 'today',
        period_label: '当日',
        start_date: '2026-07-21',
        end_date: '2026-07-21',
        degraded: false,
        missing_sources: [],
        market_emotion: '情绪强',
        short_term_outlook: '当前更适合连板接力。',
        operation_advice: '做连板',
        tracking_focus: ['连板梯队'],
        core_conclusion: '连板接力。',
        risk_signals: [],
        sector_count: 3,
        candidate_count: 0,
        strategy_card: {
          title: '指数情绪策略卡 · 当日',
          index_strength: 'strong',
          emotion_strength: 'strong',
          primary_strategy: '连板接力',
          secondary_strategy: '主升分歧接力',
          operation_advice: '指数强、情绪强，做连板。',
          focus_targets: ['连板梯队'],
          rationale: ['指数强度 0.80'],
        },
      },
    })

    await refreshShortTermData({ period: 'today' })

    expect(apiClient.post).toHaveBeenCalledWith('/short-term/overview/refresh-data', null, {
      params: { period: 'today' },
      timeout: 300_000,
    })
  })

  it('analyzes strategy card from database', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: {
        trade_date: '2026-07-21',
        period: 'today',
        period_label: '当日',
        start_date: '2026-07-21',
        end_date: '2026-07-21',
        degraded: false,
        missing_sources: [],
        market_emotion: '情绪弱',
        short_term_outlook: '当前更适合补涨趋势与切换。',
        operation_advice: '做补涨',
        tracking_focus: ['低位补涨'],
        core_conclusion: '补涨趋势与切换。',
        risk_signals: ['短线情绪不足'],
        sector_count: 3,
        candidate_count: 0,
        strategy_card: {
          title: '指数情绪策略卡 · 当日',
          index_strength: 'strong',
          emotion_strength: 'weak',
          primary_strategy: '补涨趋势与切换',
          secondary_strategy: '轮动低吸',
          operation_advice: '指数强但情绪弱，做补涨。',
          focus_targets: ['低位补涨'],
          rationale: ['指数强度 0.39'],
        },
      },
    })

    await analyzeShortTermFromDatabase({ period: 'today' })

    expect(apiClient.post).toHaveBeenCalledWith('/short-term/overview/analyze', null, {
      params: { period: 'today' },
      timeout: 300_000,
    })
  })

  it('passes AbortSignal to fetchShortTermOverview', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: { period_label: '当日' } })
    const signal = new AbortController().signal

    await fetchShortTermOverview({ period: 'today' }, signal)

    expect(apiClient.get).toHaveBeenCalledWith(
      '/short-term/overview',
      expect.objectContaining({ signal, timeout: 30_000 })
    )
  })

  it('passes AbortSignal to refreshShortTermData', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { period_label: '当日' } })
    const signal = new AbortController().signal

    await refreshShortTermData({ period: 'today' }, signal)

    expect(apiClient.post).toHaveBeenCalledWith(
      '/short-term/overview/refresh-data',
      null,
      expect.objectContaining({ signal, timeout: 300_000 })
    )
  })

  it('passes AbortSignal to fetchFirstToSecondCandidates', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: { candidates: [] } })
    const signal = new AbortController().signal

    await fetchFirstToSecondCandidates({ tradeDate: '2026-07-21' }, signal)

    expect(apiClient.get).toHaveBeenCalledWith(
      '/short-term/first-to-second',
      expect.objectContaining({ signal, timeout: 300_000 })
    )
  })

  it('passes AbortSignal to refreshFirstToSecondCandidates', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { candidates: [] } })
    const signal = new AbortController().signal

    await refreshFirstToSecondCandidates({ tradeDate: '2026-07-21' }, signal)

    expect(apiClient.post).toHaveBeenCalledWith(
      '/short-term/first-to-second/refresh',
      null,
      expect.objectContaining({ signal, timeout: 300_000 })
    )
  })

  it('passes AbortSignal to refreshShortTermSignals', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { refreshed_at: '2026-07-21T10:00:00Z' } })
    const signal = new AbortController().signal

    await refreshShortTermSignals('2026-07-21', signal)

    expect(apiClient.post).toHaveBeenCalledWith(
      '/short-term/signals/refresh',
      null,
      expect.objectContaining({ signal, timeout: 300_000 })
    )
  })

  it('passes AbortSignal to fetchShortTermSectors', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: { sectors: [] } })
    const signal = new AbortController().signal

    await fetchShortTermSectors('2026-07-21', signal)

    expect(apiClient.get).toHaveBeenCalledWith(
      '/short-term/sectors',
      expect.objectContaining({ signal, timeout: 30_000 })
    )
  })
})
