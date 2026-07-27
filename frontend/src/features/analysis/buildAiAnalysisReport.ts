import type { NewsArticle } from '@/api/news'
import type { ThemeBrief } from '@/types/theme'
import type {
  FirstToSecondCandidateItem,
  FirstToSecondCandidateResponse,
  ShortTermOverviewResponse,
} from '@/types/short-term'
import type { StockDetailResponse } from '@/types/stock'

export interface AiAnalysisContext {
  overview: ShortTermOverviewResponse | null
  hotThemes: ThemeBrief[]
  risingThemes: ThemeBrief[]
  news: NewsArticle[]
  boardCandidates: FirstToSecondCandidateResponse | null
  stock: StockDetailResponse | null
}

export interface AiAnalysisReport {
  trend: string
  marketEmotion: string
  sectorRotation: string
  mainThemes: string[]
  strongStocks: string[]
  dragonTiger: string
  newsCatalysts: string[]
  riskSignals: string[]
  unusualMoves: string[]
  nearUnusual: string[]
  stockTrendNote: string
  shortTermOutlook: string
  operationAdvice: string
  trackingFocus: string[]
  coreConclusion: string
}

function formatPct(value: number | null | undefined): string {
  if (value == null || Number.isNaN(Number(value))) return '—'
  const num = Number(value)
  return `${num > 0 ? '+' : ''}${num.toFixed(2)}%`
}

function candidateLabel(item: FirstToSecondCandidateItem): string {
  const theme = item.theme_name ? ` · ${item.theme_name}` : ''
  return `${item.name}(${item.code})${theme}`
}

/** 将多源市场数据合成为 AI 个股分析报告结构 */
export function buildAiAnalysisReport(ctx: AiAnalysisContext): AiAnalysisReport {
  const card = ctx.overview?.strategy_card
  const overview = ctx.overview

  const trend = card
    ? `指数强度${card.index_strength === 'strong' ? '偏强' : '偏弱'}，主策略「${card.primary_strategy}」，辅看「${card.secondary_strategy}」。${card.rationale[0] ?? ''}`
    : '暂无指数与策略快照，请先在看板刷新行情。'

  const marketEmotion =
    overview?.market_emotion ||
    (card ? `情绪${card.emotion_strength === 'strong' ? '偏强' : '偏弱'}` : '暂无情绪数据')

  const rotationLeaders = ctx.risingThemes.slice(0, 5).map((theme) => {
    return `${theme.name}(${formatPct(theme.rise_fall_pct)})`
  })
  const sectorRotation =
    rotationLeaders.length > 0
      ? `近端涨幅居前题材：${rotationLeaders.join('、')}。轮动观察板块数约 ${overview?.sector_count ?? '—'}。`
      : '暂无板块涨幅排行，轮动观察暂缺。'

  const mainThemes = ctx.hotThemes.slice(0, 6).map((theme) => {
    return `${theme.name} · 热度 ${Number(theme.heat_index).toFixed(1)} · ${formatPct(theme.rise_fall_pct)}`
  })

  const candidates = ctx.boardCandidates?.candidates ?? []
  const strong = candidates
    .filter((item) => item.decision === 'candidate' || item.decision === 'watch')
    .slice(0, 8)
    .map(candidateLabel)

  const unusualMoves = candidates
    .filter(
      (item) =>
        item.matched_rules.some((rule) => rule.includes('异动') && !rule.includes('接近')) ||
        item.matched_rules.some((rule) => rule.includes('涨停') || rule.includes('封板'))
    )
    .slice(0, 8)
    .map(candidateLabel)

  const nearUnusual = candidates
    .filter((item) => item.matched_rules.some((rule) => rule.includes('接近异动')))
    .slice(0, 8)
    .map(candidateLabel)

  const newsCatalysts = ctx.news.slice(0, 8).map((article) => {
    const when = article.published_at?.slice(0, 16).replace('T', ' ') ?? ''
    return `${when} · ${article.title}`
  })

  const riskSignals = [
    ...(overview?.risk_signals ?? []),
    ...(ctx.stock
      ? []
      : []),
    ...candidates
      .flatMap((item) => item.risk_flags)
      .filter(Boolean)
      .slice(0, 5),
  ]
  const uniqueRisks = [...new Set(riskSignals)]

  let stockTrendNote = '未指定个股。可输入代码后结合长期涨幅与事件再定位。'
  if (ctx.stock) {
    const events = ctx.stock.recent_events
      .slice(0, 3)
      .map((event) => event.title)
      .join('；')
    stockTrendNote = `${ctx.stock.name}(${ctx.stock.code}) 最新涨跌 ${formatPct(ctx.stock.rise_fall_pct)}，行业 ${ctx.stock.industry ?? '未知'}。${
      events ? `近期事件：${events}。` : '暂无个股事件。'
    }请结合上方主线题材判断是否处于风口。`
  }

  const trackingFocus = [
    ...(overview?.tracking_focus ?? card?.focus_targets ?? []),
    ...mainThemes.slice(0, 2),
    ...(ctx.stock ? [`个股 ${ctx.stock.name}(${ctx.stock.code})`] : []),
  ].filter(Boolean)

  const strongNote =
    strong.length > 0 ? `强势观察：${strong.slice(0, 3).join('、')}。` : ''
  const coreConclusion =
    overview?.core_conclusion ||
    (card
      ? `${card.primary_strategy}，辅助观察${card.secondary_strategy}。`
      : '数据不足，暂缓下结论。')

  return {
    trend,
    marketEmotion,
    sectorRotation,
    mainThemes,
    strongStocks: strong.length > 0 ? strong : ['暂无一进二/强势候选（可能需登录或刷新）'],
    dragonTiger: '龙虎榜数据源尚未接入，本版先以涨停链与一进二候选作为资金博弈代理观察。',
    newsCatalysts:
      newsCatalysts.length > 0 ? newsCatalysts : ['暂无可用新闻催化，可稍后刷新资讯。'],
    riskSignals: uniqueRisks.length > 0 ? uniqueRisks : ['暂无明显风险标签'],
    unusualMoves: unusualMoves.length > 0 ? unusualMoves : ['暂无明确异动股标签'],
    nearUnusual: nearUnusual.length > 0 ? nearUnusual : ['暂无接近异动候选'],
    stockTrendNote,
    shortTermOutlook: overview?.short_term_outlook || '等待市场快照更新后再给展望。',
    operationAdvice:
      overview?.operation_advice ||
      card?.operation_advice ||
      '先观察指数与情绪共振，再决定进攻或防守。',
    trackingFocus: [...new Set(trackingFocus)].slice(0, 8),
    coreConclusion: `${coreConclusion}${strongNote}${ctx.stock ? ` 个股侧：${ctx.stock.name} 近端 ${formatPct(ctx.stock.rise_fall_pct)}。` : ''}`,
  }
}
