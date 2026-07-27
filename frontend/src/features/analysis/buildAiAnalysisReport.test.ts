import { describe, expect, it } from 'vitest'
import { buildAiAnalysisReport } from './buildAiAnalysisReport'
import type { ShortTermOverviewResponse } from '@/types/short-term'

const overview: ShortTermOverviewResponse = {
  trade_date: '2026-07-24',
  period: 'today',
  period_label: '当日',
  start_date: '2026-07-24',
  end_date: '2026-07-24',
  degraded: false,
  missing_sources: [],
  market_emotion: '情绪强',
  short_term_outlook: '指数与情绪共振，关注主线接力。',
  operation_advice: '优先低位确认后的主线前排。',
  tracking_focus: ['人工智能', '机器人'],
  core_conclusion: '连板接力为主。',
  risk_signals: ['短线情绪不足'],
  sector_count: 12,
  candidate_count: 0,
  strategy_card: {
    title: '指数情绪策略卡',
    index_strength: 'strong',
    emotion_strength: 'strong',
    primary_strategy: '连板接力',
    secondary_strategy: '补涨低吸',
    operation_advice: '强者恒强',
    focus_targets: ['算力'],
    rationale: ['指数强度 1.20（当日），判定为强。'],
  },
}

describe('buildAiAnalysisReport', () => {
  it('composes market and stock evidence into conclusion sections', () => {
    const report = buildAiAnalysisReport({
      overview,
      hotThemes: [
        {
          id: 1,
          name: '人工智能',
          code: 'AI',
          description: null,
          heat_index: 90,
          rise_fall_pct: 3.2,
          stock_count: 40,
          category: '科技',
          tags: [],
          source: null,
        },
      ],
      risingThemes: [
        {
          id: 2,
          name: '机器人',
          code: 'ROBOT',
          description: null,
          heat_index: 80,
          rise_fall_pct: 5.1,
          stock_count: 30,
          category: '科技',
          tags: [],
          source: null,
        },
      ],
      news: [
        {
          id: 1,
          source: 'demo',
          category: '市场',
          title: '算力政策催化',
          summary: null,
          url: 'https://example.com',
          published_at: '2026-07-24T08:00:00Z',
          crawled_at: '2026-07-24T08:01:00Z',
          heat_score: 80,
        },
      ],
      boardCandidates: {
        trade_date: '2026-07-24',
        previous_trade_date: '2026-07-23',
        refreshed_at: '2026-07-24T08:00:00Z',
        degraded: false,
        missing_sources: [],
        excluded_count: 0,
        source_status: {},
        candidates: [
          {
            code: '600001',
            name: '示例股份',
            theme_name: '人工智能',
            price: 12,
            market_cap: 100,
            float_market_cap: 80,
            turnover_rate: 8,
            amount: 1,
            first_limit_up_at: '09:42:00',
            open_board_count: 0,
            score: 80,
            decision: 'candidate',
            matched_rules: ['今日接近异动'],
            excluded_rules: [],
            risk_flags: ['高换手'],
            catalysts: [],
            operation_advice: '观察',
            core_conclusion: '可跟踪',
          },
        ],
      },
      stock: {
        id: 9,
        code: '600519',
        name: '贵州茅台',
        industry: '白酒',
        market_cap: 1,
        current_price: 1600,
        rise_fall_pct: 1.2,
        exchange: 'SH',
        created_at: '',
        updated_at: '',
        recent_events: [],
      },
    })

    expect(report.marketEmotion).toContain('情绪强')
    expect(report.sectorRotation).toContain('机器人')
    expect(report.mainThemes[0]).toContain('人工智能')
    expect(report.nearUnusual[0]).toContain('示例股份')
    expect(report.newsCatalysts[0]).toContain('算力政策催化')
    expect(report.stockTrendNote).toContain('贵州茅台')
    expect(report.shortTermOutlook).toContain('主线接力')
    expect(report.coreConclusion).toContain('连板接力')
  })
})
