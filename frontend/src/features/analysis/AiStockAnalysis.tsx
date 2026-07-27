import { useMemo, useState, type FormEvent, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertTriangle,
  Flame,
  LineChart,
  Loader2,
  Newspaper,
  RefreshCw,
  Sparkles,
  Target,
  TrendingUp,
  Waves,
} from 'lucide-react'
import { AppCardNav } from '@/components/AppCardNav'
import { GlowCard } from '@/components/GlowCard'
import { fetchNews } from '@/api/news'
import { fetchThemeRanking, fetchThemes } from '@/api/theme'
import { fetchStockDetail } from '@/api/stock'
import { analyzeShortTermFromDatabase } from '@/api/short-term'

/** 市场上下文请求超时：避免像一进二/补快照那样拖成数分钟 */
const CONTEXT_TIMEOUT_MS = 15_000
import { fetchStockAiReport, generateStockAiReport } from '@/api/stock-ai-report'
import { useAuthStore } from '@/stores/auth'
import {
  formatRefreshDurationMs,
  useRefreshTimer,
} from '@/hooks/useRefreshTimer'
import {
  buildAiAnalysisReport,
  type AiAnalysisReport,
} from '@/features/analysis/buildAiAnalysisReport'
import type {
  HorizonFit,
  StockAiReport,
  StockAiVerdict,
} from '@/types/stock-ai-report'

type ContextRefreshStatus =
  | { kind: 'idle' }
  | { kind: 'running' }
  | { kind: 'success'; refreshedAt: number; elapsedMs: number }
  | { kind: 'error'; message: string; elapsedMs: number }

function ReportSection({
  title,
  icon,
  children,
}: {
  title: string
  icon: React.ReactNode
  children: ReactNode
}) {
  return (
    <GlowCard>
      <section className="space-y-3 p-4">
        <div className="flex items-center gap-2">
          <span className="text-primary">{icon}</span>
          <h2 className="text-sm font-semibold tracking-tight">{title}</h2>
        </div>
        <div className="text-sm leading-relaxed text-muted-foreground">{children}</div>
      </section>
    </GlowCard>
  )
}

function BulletList({ items }: { items: string[] }) {
  return (
    <ul className="space-y-1.5">
      {items.map((item) => (
        <li key={item} className="flex gap-2">
          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-primary/70" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  )
}

const VERDICT_LABEL: Record<StockAiVerdict, string> = {
  buy: '买入',
  watch: '观望',
  avoid: '回避',
}

const FIT_LABEL: Record<HorizonFit, string> = {
  suitable: '适合',
  neutral: '中性',
  unsuitable: '不适合',
}

function getApiErrorMessage(error: unknown, fallback: string): string {
  const value = error as {
    response?: { status?: number; data?: { detail?: string; message?: string } }
    message?: string
  }
  return (
    value.response?.data?.detail ||
    value.response?.data?.message ||
    value.message ||
    fallback
  )
}

function getApiStatus(error: unknown): number | undefined {
  return (error as { response?: { status?: number } })?.response?.status
}

function normalizeStockCode(raw: string): string {
  return raw
    .replace(/[０-９]/g, (digit) => String.fromCharCode(digit.charCodeAt(0) - 0xff10 + 0x30))
    .replace(/\D/g, '')
    .slice(0, 6)
}

function formatGeneratedAt(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

function AiVerdictCard({ report }: { report: StockAiReport }) {
  return (
    <GlowCard className="border-primary/30">
      <section className="space-y-4 p-5">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <Target className="h-5 w-5 text-primary" />
            <h2 className="text-base font-semibold tracking-tight">AI 研判结论</h2>
          </div>
          <p className="text-xs text-muted-foreground">
            {report.stock_name ? `${report.stock_name}(${report.code})` : report.code}
            {report.model_name ? ` · ${report.model_name}` : ''}
          </p>
        </div>
        <p className="text-xs text-muted-foreground">
          生成于 {formatGeneratedAt(report.generated_at)}
          {report.elapsed_ms ? ` · 耗时 ${formatRefreshDurationMs(report.elapsed_ms)}` : ''}
        </p>

        <div className="flex flex-wrap items-center gap-3">
          <span className="rounded-xl bg-primary px-4 py-2 text-base font-semibold text-primary-foreground">
            {VERDICT_LABEL[report.verdict]}
          </span>
          <span className="rounded-xl border border-border px-3 py-2 text-sm">
            信心 {report.confidence}
          </span>
        </div>

        <p className="text-sm font-medium text-foreground">{report.summary}</p>

        <div className="grid gap-3">
          {(
            [
              ['短线', report.horizon.short],
              ['波段', report.horizon.swing],
              ['中长线', report.horizon.medium_long],
            ] as const
          ).map(([label, slot]) => (
            <div key={label} className="rounded-xl border border-border/70 bg-muted/20 p-3">
              <p className="text-xs text-muted-foreground">{label}</p>
              <p className="mt-1 text-sm font-medium text-foreground">{FIT_LABEL[slot.fit]}</p>
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{slot.note}</p>
            </div>
          ))}
        </div>
      </section>
    </GlowCard>
  )
}

function AiFullReport({ report }: { report: StockAiReport }) {
  const sectionEntries: Array<[string, string]> = [
    ['近期趋势', report.sections.trend],
    ['情绪与轮动', report.sections.emotion_rotation],
    ['主线与催化', report.sections.themes_catalysts],
    ['个股定位', report.sections.stock_position],
    ['情景与操作', report.sections.scenarios_actions],
    ['风险', report.sections.risks],
  ]

  return (
    <div className="space-y-4">
      <GlowCard>
        <section className="space-y-3 p-5">
          <h2 className="text-sm font-semibold tracking-tight">完整研判报告</h2>
          <div className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
            {report.full_report}
          </div>
        </section>
      </GlowCard>

      <div className="space-y-3">
        {sectionEntries.map(([title, body]) =>
          body ? (
            <GlowCard key={title}>
              <section className="space-y-2 p-4">
                <h3 className="text-sm font-medium text-foreground">{title}</h3>
                <p className="text-sm leading-relaxed text-muted-foreground">{body}</p>
              </section>
            </GlowCard>
          ) : null
        )}
      </div>

      <p className="text-xs text-muted-foreground">{report.disclaimer}</p>
    </div>
  )
}

function MarketContextPanel({
  report,
  isLoading,
}: {
  report: AiAnalysisReport
  isLoading: boolean
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-base font-semibold tracking-tight">市场上下文</h2>
        <span className="text-xs text-muted-foreground">规则汇总 · 供 AI 参考</span>
      </div>
      {isLoading && (
        <p className="text-sm text-muted-foreground">正在加载市场上下文…</p>
      )}
      <ReportSection title="近期趋势" icon={<LineChart className="h-4 w-4" />}>
        <p>{report.trend}</p>
      </ReportSection>
      <ReportSection title="市场情绪" icon={<Waves className="h-4 w-4" />}>
        <p>{report.marketEmotion}</p>
      </ReportSection>
      <ReportSection title="板块轮动" icon={<TrendingUp className="h-4 w-4" />}>
        <p>{report.sectorRotation}</p>
      </ReportSection>
      <ReportSection title="主线题材与强势股" icon={<Flame className="h-4 w-4" />}>
        <p className="mb-2 font-medium text-foreground">主线题材</p>
        <BulletList items={report.mainThemes.length ? report.mainThemes : ['暂无热门题材']} />
        <p className="mb-2 mt-4 font-medium text-foreground">强势股观察</p>
        <BulletList items={report.strongStocks} />
      </ReportSection>
      <ReportSection title="龙虎榜核心动向" icon={<Target className="h-4 w-4" />}>
        <p>{report.dragonTiger}</p>
      </ReportSection>
      <ReportSection title="新闻时间催化驱动" icon={<Newspaper className="h-4 w-4" />}>
        <BulletList items={report.newsCatalysts} />
      </ReportSection>
      <ReportSection title="风险信号" icon={<AlertTriangle className="h-4 w-4" />}>
        <BulletList items={report.riskSignals} />
      </ReportSection>
      <ReportSection title="异动与接近异动" icon={<Sparkles className="h-4 w-4" />}>
        <p className="mb-2 font-medium text-foreground">异动股票</p>
        <BulletList items={report.unusualMoves} />
        <p className="mb-2 mt-4 font-medium text-foreground">今日接近异动</p>
        <BulletList items={report.nearUnusual} />
      </ReportSection>
      <ReportSection title="个股定位（规则）" icon={<LineChart className="h-4 w-4" />}>
        <p>{report.stockTrendNote}</p>
      </ReportSection>
      <GlowCard>
        <section className="space-y-3 p-4">
          <h3 className="text-sm font-semibold text-foreground">规则汇总结论（非 AI）</h3>
          <div className="grid gap-3">
            <div className="rounded-xl border border-border/70 bg-muted/20 p-3">
              <p className="text-xs text-muted-foreground">短期展望</p>
              <p className="mt-1 text-sm text-foreground">{report.shortTermOutlook}</p>
            </div>
            <div className="rounded-xl border border-border/70 bg-muted/20 p-3">
              <p className="text-xs text-muted-foreground">操作建议</p>
              <p className="mt-1 text-sm text-foreground">{report.operationAdvice}</p>
            </div>
          </div>
          <p className="text-sm text-foreground">{report.coreConclusion}</p>
        </section>
      </GlowCard>
    </div>
  )
}

/** AI 个股分析：左栏市场上下文，右栏 AI 研判（结合左侧上下文由后端聚合生成） */
export function AiStockAnalysis() {
  const token = useAuthStore((state) => state.token)
  const queryClient = useQueryClient()
  const [codeInput, setCodeInput] = useState('')
  const [activeCode, setActiveCode] = useState<string | null>(null)
  const [codeError, setCodeError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [needsModelSetup, setNeedsModelSetup] = useState(false)
  const [contextRefreshStatus, setContextRefreshStatus] =
    useState<ContextRefreshStatus>({ kind: 'idle' })
  const isRefreshingContext = contextRefreshStatus.kind === 'running'
  const { elapsedLabel: contextRefreshElapsed } = useRefreshTimer(isRefreshingContext)

  // 只用库内分析 + 短超时；本页不再请求一进二（外网拉取会拖垮整站）
  const overviewQuery = useQuery({
    queryKey: ['ai-analysis-overview'],
    queryFn: () =>
      analyzeShortTermFromDatabase({ period: 'today' }, { timeout: CONTEXT_TIMEOUT_MS }),
    staleTime: 60_000,
    retry: false,
  })
  const hotThemesQuery = useQuery({
    queryKey: ['ai-analysis-hot-themes'],
    queryFn: () => fetchThemeRanking(12),
    staleTime: 60_000,
    retry: false,
  })
  const risingThemesQuery = useQuery({
    queryKey: ['ai-analysis-rising-themes'],
    queryFn: () =>
      fetchThemes({
        page: 1,
        page_size: 12,
        sort_by: 'rise_fall_pct',
        sort_order: 'desc',
      }),
    staleTime: 60_000,
    retry: false,
  })
  const newsQuery = useQuery({
    queryKey: ['ai-analysis-news'],
    queryFn: () => fetchNews(20),
    staleTime: 60_000,
    retry: false,
  })
  const stockQuery = useQuery({
    queryKey: ['ai-analysis-stock', activeCode],
    queryFn: () => fetchStockDetail(activeCode!),
    enabled: Boolean(activeCode),
    retry: false,
  })

  const cachedReportQuery = useQuery({
    queryKey: ['stock-ai-report', activeCode],
    queryFn: () => fetchStockAiReport(activeCode!),
    enabled: Boolean(token && activeCode),
    retry: false,
  })

  const generateMutation = useMutation({
    mutationFn: ({ code, force }: { code: string; force: boolean }) =>
      generateStockAiReport(code, { force }),
    onSuccess: (data) => {
      setActionError(null)
      setNeedsModelSetup(false)
      queryClient.setQueryData(['stock-ai-report', data.code], data)
    },
    onError: (error) => {
      const status = getApiStatus(error)
      setNeedsModelSetup(status === 409)
      setActionError(getApiErrorMessage(error, '生成 AI 研判失败'))
    },
  })

  const isGenerating =
    generateMutation.isPending && generateMutation.variables?.code === activeCode
  const { elapsedLabel: generateElapsed } = useRefreshTimer(isGenerating)

  const contextReport = useMemo(
    () =>
      buildAiAnalysisReport({
        overview: overviewQuery.data ?? null,
        hotThemes: hotThemesQuery.data?.items ?? [],
        risingThemes: risingThemesQuery.data?.items ?? [],
        news: newsQuery.data?.items ?? [],
        boardCandidates: null,
        stock: stockQuery.data ?? null,
      }),
    [
      overviewQuery.data,
      hotThemesQuery.data,
      risingThemesQuery.data,
      newsQuery.data,
      stockQuery.data,
    ]
  )

  const aiReport =
    (generateMutation.data?.code === activeCode ? generateMutation.data : null) ??
    (cachedReportQuery.data?.code === activeCode ? cachedReportQuery.data : null)

  const hasCoreContext = Boolean(
    overviewQuery.data ||
      hotThemesQuery.data ||
      risingThemesQuery.data ||
      newsQuery.data
  )
  const isContextLoading =
    !hasCoreContext &&
    (overviewQuery.isLoading ||
      hotThemesQuery.isLoading ||
      risingThemesQuery.isLoading ||
      newsQuery.isLoading)

  const runGenerate = (code: string, force: boolean) => {
    setActionError(null)
    setNeedsModelSetup(false)
    generateMutation.mutate({ code, force })
  }

  const loadOrGenerate = (code: string, force: boolean) => {
    setActionError(null)
    setNeedsModelSetup(false)
    setActiveCode(code)

    if (force) {
      runGenerate(code, true)
      return
    }

    void queryClient
      .fetchQuery({
        queryKey: ['stock-ai-report', code],
        queryFn: () => fetchStockAiReport(code),
        retry: false,
      })
      .then((cached) => {
        queryClient.setQueryData(['stock-ai-report', code], cached)
      })
      .catch((error: unknown) => {
        if (getApiStatus(error) === 404) {
          runGenerate(code, false)
          return
        }
        if (getApiStatus(error) === 409) {
          setNeedsModelSetup(true)
        }
        setActionError(getApiErrorMessage(error, '读取研判缓存失败'))
      })
  }

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (!token) {
      setCodeError('请先登录后再生成 AI 研判。')
      return
    }
    const normalized = normalizeStockCode(codeInput)
    if (normalized.length !== 6) {
      setCodeError('请输入 6 位股票代码后再生成研判。')
      return
    }
    setCodeError(null)
    setCodeInput(normalized)
    // 已有当前代码报告时，主按钮表示「重新生成」；否则先读缓存再生成
    const hasCurrent =
      (generateMutation.data?.code === normalized ||
        queryClient.getQueryData<StockAiReport>(['stock-ai-report', normalized])?.code ===
          normalized) &&
      normalized === activeCode
    loadOrGenerate(normalized, hasCurrent)
  }

  const refreshContext = async () => {
    if (isRefreshingContext) return
    setContextRefreshStatus({ kind: 'running' })
    const startedAt = Date.now()
    try {
      const tasks = [
        overviewQuery.refetch(),
        hotThemesQuery.refetch(),
        risingThemesQuery.refetch(),
        newsQuery.refetch(),
      ]
      if (activeCode) tasks.push(stockQuery.refetch())
      // 分源结算：任一超时/失败不拖死整次刷新
      const results = await Promise.allSettled(tasks)
      const elapsedMs = Date.now() - startedAt
      const rejected = results.filter((r) => r.status === 'rejected')
      const fulfilledErrors = results.filter(
        (r) => r.status === 'fulfilled' && r.value.isError
      )
      const okCount = results.filter(
        (r) => r.status === 'fulfilled' && !r.value.isError
      ).length

      if (okCount === 0) {
        const firstError =
          (fulfilledErrors[0]?.status === 'fulfilled' && fulfilledErrors[0].value.error) ||
          (rejected[0]?.status === 'rejected' && rejected[0].reason) ||
          null
        setContextRefreshStatus({
          kind: 'error',
          message: getApiErrorMessage(
            firstError,
            '市场上下文刷新失败：后端无响应（可能正被其他慢请求占满，请稍后重试或重启后端）'
          ),
          elapsedMs,
        })
        return
      }

      if (rejected.length > 0 || fulfilledErrors.length > 0) {
        setContextRefreshStatus({
          kind: 'success',
          refreshedAt: Date.now(),
          elapsedMs,
        })
        // 部分成功也算刷新完成，细节写在成功文案由 banner 展示耗时即可
        return
      }

      setContextRefreshStatus({
        kind: 'success',
        refreshedAt: Date.now(),
        elapsedMs,
      })
    } catch (error) {
      setContextRefreshStatus({
        kind: 'error',
        message: getApiErrorMessage(error, '市场上下文刷新失败'),
        elapsedMs: Date.now() - startedAt,
      })
    }
  }

  const refreshStatusText =
    contextRefreshStatus.kind === 'running'
      ? `刷新中 · 已耗时 ${contextRefreshElapsed}`
      : contextRefreshStatus.kind === 'success'
        ? `已更新 · ${new Date(contextRefreshStatus.refreshedAt).toLocaleString('zh-CN', {
            hour12: false,
          })} · 耗时 ${formatRefreshDurationMs(contextRefreshStatus.elapsedMs)}`
        : contextRefreshStatus.kind === 'error'
          ? `失败 · ${contextRefreshStatus.message} · 耗时 ${formatRefreshDurationMs(contextRefreshStatus.elapsedMs)}`
          : null

  return (
    <div className="min-h-screen">
      <AppCardNav />
      <main className="mx-auto w-full max-w-none space-y-6 px-3 py-6 sm:px-4 lg:px-5 xl:px-6">
        <GlowCard>
          <section className="space-y-4 p-6 sm:p-8">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <Sparkles className="h-5 w-5" />
                </div>
                <div>
                  <h1 className="text-2xl font-semibold tracking-tight">AI 个股分析</h1>
                  <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
                    左侧为市场上下文，右侧结合上下文生成买入/持有研判；输入框在右栏底部。
                  </p>
                </div>
              </div>
              <div className="flex min-w-[16rem] flex-col items-stretch gap-2 sm:items-end">
                <button
                  type="button"
                  onClick={() => void refreshContext()}
                  disabled={isRefreshingContext}
                  className="inline-flex items-center justify-center gap-2 rounded-xl border border-border px-3 py-2 text-sm hover:bg-accent disabled:opacity-70"
                >
                  <RefreshCw
                    className={`h-4 w-4 ${isRefreshingContext ? 'animate-spin' : ''}`}
                  />
                  {isRefreshingContext
                    ? `刷新中（已耗时 ${contextRefreshElapsed}）`
                    : '刷新市场上下文'}
                </button>
                {refreshStatusText && (
                  <p
                    role="status"
                    className={`max-w-md text-xs sm:text-right ${
                      contextRefreshStatus.kind === 'error'
                        ? 'text-destructive'
                        : 'text-muted-foreground'
                    }`}
                  >
                    {refreshStatusText}
                  </p>
                )}
              </div>
            </div>

            {isRefreshingContext && (
              <p role="status" className="rounded-xl border border-primary/25 bg-primary/5 px-4 py-3 text-sm">
                正在刷新市场上下文（短线概览、题材、新闻），已耗时 {contextRefreshElapsed}…
              </p>
            )}
            {contextRefreshStatus.kind === 'success' && (
              <p role="status" className="rounded-xl border border-primary/25 bg-primary/5 px-4 py-3 text-sm">
                市场上下文已刷新，更新于{' '}
                {new Date(contextRefreshStatus.refreshedAt).toLocaleString('zh-CN', {
                  hour12: false,
                })}
                ，耗时 {formatRefreshDurationMs(contextRefreshStatus.elapsedMs)}
              </p>
            )}
            {contextRefreshStatus.kind === 'error' && (
              <p
                role="alert"
                className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive"
              >
                {contextRefreshStatus.message}，耗时{' '}
                {formatRefreshDurationMs(contextRefreshStatus.elapsedMs)}
              </p>
            )}

            {!token && (
              <p className="rounded-xl border border-dashed border-border/80 bg-muted/30 px-4 py-3 text-sm text-muted-foreground">
                请先{' '}
                <Link to="/login" className="text-primary underline underline-offset-2">
                  登录
                </Link>
                ，并配置默认模型后在右栏底部生成 AI 研判；左侧市场上下文可直接浏览。
              </p>
            )}
          </section>
        </GlowCard>

        <div className="grid gap-6 lg:grid-cols-2 lg:items-start">
          <section aria-label="市场上下文" className="min-w-0">
            <MarketContextPanel report={contextReport} isLoading={isContextLoading} />
            {(overviewQuery.isError ||
              hotThemesQuery.isError ||
              risingThemesQuery.isError ||
              newsQuery.isError) && (
              <p className="mt-3 text-xs text-destructive">
                部分数据源超时或失败。若持续无数据，请检查后端是否被慢请求占满后重试。
              </p>
            )}
          </section>

          <section aria-label="AI 研判" className="flex min-w-0 flex-col gap-4">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-base font-semibold tracking-tight">AI 研判</h2>
              <span className="text-xs text-muted-foreground">结合左侧上下文生成</span>
            </div>

            {isGenerating && (
              <p
                role="status"
                className="rounded-xl border border-primary/25 bg-primary/5 px-4 py-3 text-sm"
              >
                正在调用模型，结合左侧市场上下文与个股信息生成研判，已耗时 {generateElapsed}…
              </p>
            )}

            {!token && (
              <GlowCard>
                <section className="space-y-2 p-5 text-sm text-muted-foreground">
                  <p>登录并配置模型后，这里会显示 AI 结论卡与完整报告。</p>
                </section>
              </GlowCard>
            )}

            {token && !activeCode && !isGenerating && (
              <GlowCard>
                <section className="space-y-2 p-5 text-sm text-muted-foreground">
                  <p>在下方输入股票代码并生成研判。若该股已有缓存，将先展示历史研判。</p>
                </section>
              </GlowCard>
            )}

            {token && activeCode && !aiReport && !isGenerating && !actionError && (
              <GlowCard>
                <section className="space-y-2 p-5 text-sm text-muted-foreground">
                  <p>
                    {cachedReportQuery.isFetching
                      ? `正在读取 ${activeCode} 的历史研判…`
                      : `尚未生成 ${activeCode} 的 AI 研判，请在下方点击生成。`}
                  </p>
                </section>
              </GlowCard>
            )}

            {aiReport && (
              <>
                <AiVerdictCard report={aiReport} />
                <AiFullReport report={aiReport} />
              </>
            )}

            <GlowCard className="mt-auto">
              <section className="space-y-3 p-4 sm:p-5">
                <h3 className="text-sm font-semibold tracking-tight">生成个股研判</h3>
                <form className="flex flex-col gap-3 sm:flex-row" onSubmit={handleSubmit}>
                  <label className="sr-only" htmlFor="ai-stock-code">
                    股票代码
                  </label>
                  <input
                    id="ai-stock-code"
                    value={codeInput}
                    onChange={(event) => {
                      setCodeInput(event.target.value)
                      if (codeError) setCodeError(null)
                    }}
                    placeholder="输入 6 位股票代码，如 600519"
                    maxLength={6}
                    inputMode="numeric"
                    autoComplete="off"
                    className="h-11 flex-1 rounded-xl border border-border bg-background px-3 text-sm outline-none ring-primary focus:ring-2"
                  />
                  <button
                    type="submit"
                    disabled={isGenerating}
                    className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-primary px-4 text-sm font-medium text-primary-foreground disabled:opacity-70"
                  >
                    {isGenerating ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Sparkles className="h-4 w-4" />
                    )}
                    {aiReport && activeCode === aiReport.code
                      ? '重新生成 AI 研判'
                      : '生成 AI 研判'}
                  </button>
                </form>
                {codeError && <p className="text-sm text-destructive">{codeError}</p>}
                {actionError && (
                  <p className="text-sm text-destructive">
                    {actionError}
                    {needsModelSetup && (
                      <>
                        {' '}
                        <Link to="/settings/models" className="underline underline-offset-2">
                          前往模型设置
                        </Link>
                      </>
                    )}
                  </p>
                )}
                {stockQuery.isError && activeCode && (
                  <p className="text-sm text-destructive">
                    个股 {activeCode} 查询失败，请确认代码是否正确。
                  </p>
                )}
              </section>
            </GlowCard>
          </section>
        </div>

        <p className="text-center text-xs text-muted-foreground">
          本页 AI 报告仅供参考，不构成投资建议。左侧为规则汇总，不代表模型结论。
        </p>
      </main>
    </div>
  )
}
