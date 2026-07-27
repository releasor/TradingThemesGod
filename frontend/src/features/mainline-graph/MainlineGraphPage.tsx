/** 主线图谱平台页 */

import { useEffect, useMemo } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import dayjs from 'dayjs'
import { GitBranch, Loader2 } from 'lucide-react'
import { AppCardNav } from '@/components/AppCardNav'
import { GlowCard } from '@/components/GlowCard'
import {
  createMainlineGraphDraft,
  ensureMainlineGraph,
  fetchMainlineGraphVersions,
  fetchMainlineGraphView,
  publishMainlineGraphVersion,
} from '@/api/mainline-graph'
import { resolveTradeDate as resolveTradeDateApi } from '@/api/trading-calendar'
import { ConceptTreeMode } from '@/features/mainline-graph/ConceptTreeMode'
import { MainlineDrawer } from '@/features/mainline-graph/MainlineDrawer'
import { MainlineNarrativeChart } from '@/features/mainline-graph/MainlineNarrativeChart'
import {
  formatRefreshDurationMs,
  useRefreshTimer,
} from '@/hooks/useRefreshTimer'
import { getErrorMessage } from '@/lib/error-messages'
import { useAuthStore } from '@/stores/auth'
import type { MainlineGraphMode } from '@/types/mainline-graph'

/** 本地周末回退，日历 API 未返回前的兜底 */
function resolveTradeDateIso(iso?: string | null): string {
  const now = iso && /^\d{4}-\d{2}-\d{2}$/.test(iso) ? parseLocalDate(iso) : new Date()
  const day = now.getDay()
  if (day === 0) now.setDate(now.getDate() - 2)
  else if (day === 6) now.setDate(now.getDate() - 1)
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

function parseLocalDate(iso: string): Date {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d)
}

function parsePositiveInt(raw: string | null): number | null {
  if (!raw) return null
  const n = Number(raw)
  if (!Number.isFinite(n) || n <= 0 || !Number.isInteger(n)) return null
  return n
}

function parseMode(raw: string | null): MainlineGraphMode {
  return raw === 'concept' ? 'concept' : 'narrative'
}

function isNotFoundError(error: unknown): boolean {
  if (!error || typeof error !== 'object') return false
  const response = (error as { response?: { status?: number } }).response
  return response?.status === 404
}

function formatGeneratedAt(value: string | null | undefined): string {
  if (!value) return dayjs().format('YYYY-MM-DD HH:mm:ss')
  // 后端 naive 时间按本地时间展示，避免再拼 Z 导致 +8 小时错位
  const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value)
  return dayjs(hasTimezone ? value : value).format('YYYY-MM-DD HH:mm:ss')
}

export function MainlineGraphPage() {
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const token = useAuthStore((s) => s.token)
  const isLoggedIn = Boolean(token)

  const mode = parseMode(searchParams.get('mode'))
  const dateParamRaw = searchParams.get('date')
  const dateParam =
    dateParamRaw && /^\d{4}-\d{2}-\d{2}$/.test(dateParamRaw) ? dateParamRaw : null
  const versionId = parsePositiveInt(searchParams.get('versionId'))
  const themeId = parsePositiveInt(searchParams.get('themeId'))

  const calendarResolveQuery = useQuery({
    queryKey: ['market', 'calendar', 'resolve', dateParam ?? 'today'],
    queryFn: () => resolveTradeDateApi(dateParam ?? undefined),
    staleTime: 5 * 60_000,
  })

  const tradeDate =
    calendarResolveQuery.data?.trade_date ?? resolveTradeDateIso(dateParam)

  const patchParams = (patch: Record<string, string | null>) => {
    const next = new URLSearchParams(searchParams)
    for (const [key, value] of Object.entries(patch)) {
      if (value == null || value === '') next.delete(key)
      else next.set(key, value)
    }
    setSearchParams(next, { replace: true })
  }

  // URL 日期规范化为交易日
  useEffect(() => {
    if (!calendarResolveQuery.data?.trade_date) return
    if (dateParam === calendarResolveQuery.data.trade_date) return
    patchParams({ date: calendarResolveQuery.data.trade_date })
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only sync resolved date
  }, [calendarResolveQuery.data?.trade_date, dateParam])

  const versionsQuery = useQuery({
    queryKey: ['mainline-graph', 'versions', tradeDate],
    queryFn: () => fetchMainlineGraphVersions({ trade_date: tradeDate }),
    enabled: Boolean(tradeDate),
  })

  const versions = versionsQuery.data?.items ?? []
  const versionExists =
    versionId == null || versions.some((version) => version.id === versionId)
  const staleVersionId =
    versionId != null && versionsQuery.isSuccess && !versionExists

  // 残留的旧 versionId（重建图谱后 ID 会变）自动清掉，回退默认视图
  useEffect(() => {
    if (!staleVersionId) return
    patchParams({ versionId: null })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [staleVersionId, versionId])

  const viewQuery = useQuery({
    queryKey: ['mainline-graph', 'view', tradeDate, versionId ?? 'default'],
    queryFn: () =>
      fetchMainlineGraphView({
        trade_date: tradeDate,
        ...(versionId != null ? { version_id: versionId } : {}),
      }),
    // 若 URL 带了 versionId，等版本列表确认存在后再请求，避免连环 404
    enabled:
      Boolean(tradeDate) &&
      (versionId == null || versionsQuery.isSuccess) &&
      !staleVersionId,
    retry: (failureCount, error) => {
      if (isNotFoundError(error)) return false
      return failureCount < 2
    },
  })

  // 仍 404 时清 versionId（例如列表短暂不一致）
  useEffect(() => {
    if (!viewQuery.isError || versionId == null) return
    if (!isNotFoundError(viewQuery.error)) return
    patchParams({ versionId: null })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [viewQuery.isError, viewQuery.error, versionId])

  const ensureMutation = useMutation({
    mutationFn: () =>
      ensureMainlineGraph({
        trade_date: tradeDate,
        use_model: false,
      }),
    onSuccess: (result) => {
      // 生成后回到默认视图（auto）；原地复用 auto id 时也可直接钉住
      patchParams({
        date: result.trade_date,
        versionId: String(result.version_id),
      })
      void queryClient.invalidateQueries({ queryKey: ['mainline-graph'] })
    },
  })

  const { elapsedLabel: ensureElapsed } = useRefreshTimer(ensureMutation.isPending)

  const draftMutation = useMutation({
    mutationFn: () =>
      createMainlineGraphDraft({
        trade_date: tradeDate,
        ...(versionId != null ? { source_version_id: versionId } : {}),
        title: '手工草稿',
      }),
    onSuccess: (version) => {
      patchParams({
        date: version.trade_date,
        versionId: String(version.id),
      })
      void queryClient.invalidateQueries({ queryKey: ['mainline-graph'] })
    },
  })

  const publishMutation = useMutation({
    mutationFn: (id: number) => publishMainlineGraphVersion(id),
    onSuccess: (version) => {
      patchParams({ versionId: String(version.id) })
      void queryClient.invalidateQueries({ queryKey: ['mainline-graph'] })
    },
  })

  const view = viewQuery.data
  const nodes = view?.nodes ?? []
  const edges = view?.edges ?? []
  const nodesByThemeId = useMemo(
    () => new Map(nodes.map((node) => [node.theme_id, node])),
    [nodes]
  )
  const selectedNode = themeId != null ? (nodesByThemeId.get(themeId) ?? null) : null
  const currentVersion = view?.version
  const canPublish =
    isLoggedIn && currentVersion?.kind === 'draft' && currentVersion.status === 'open'

  const displayDate = view?.trade_date ?? tradeDate
  const ensureError =
    ensureMutation.error instanceof Error
      ? getErrorMessage(ensureMutation.error)
      : ensureMutation.isError
        ? getErrorMessage(0)
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
                  <GitBranch className="h-5 w-5" aria-hidden="true" />
                </div>
                <div>
                  <h1 className="text-xl font-semibold tracking-tight">主线图谱</h1>
                  <p className="mt-1 text-sm text-muted-foreground">
                    市场叙事关系图 · 题材概念树 — 版本化主线研究
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => ensureMutation.mutate()}
                  disabled={ensureMutation.isPending}
                  className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground disabled:opacity-60"
                >
                  {ensureMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                  ) : null}
                  {ensureMutation.isPending
                    ? `生成叙事图（${ensureElapsed}）`
                    : '生成叙事图谱'}
                </button>
                {isLoggedIn ? (
                  <>
                    <button
                      type="button"
                      onClick={() => draftMutation.mutate()}
                      disabled={draftMutation.isPending}
                      className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-1.5 text-sm hover:bg-accent disabled:opacity-60"
                    >
                      {draftMutation.isPending ? (
                        <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                      ) : null}
                      新建草稿
                    </button>
                    {canPublish && currentVersion ? (
                      <button
                        type="button"
                        onClick={() => publishMutation.mutate(currentVersion.id)}
                        disabled={publishMutation.isPending}
                        className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-1.5 text-sm hover:bg-accent disabled:opacity-60"
                      >
                        {publishMutation.isPending ? (
                          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                        ) : null}
                        发布版本
                      </button>
                    ) : null}
                  </>
                ) : null}
              </div>
            </div>

            {ensureMutation.isPending ? (
              <div
                role="status"
                data-testid="mainline-ensure-progress"
                className="rounded-xl border border-primary/30 bg-primary/5 px-4 py-3 text-sm text-muted-foreground"
              >
                正在按规则生成<strong className="text-foreground">叙事关系图</strong>
                （题材↔题材，已耗时 {ensureElapsed}）… 与下方概念树无关。
              </div>
            ) : null}

            {ensureMutation.isSuccess && ensureMutation.data && !ensureMutation.isPending ? (
              <div
                role="status"
                data-testid="mainline-ensure-result"
                className="space-y-1 rounded-xl border border-primary/30 bg-primary/5 px-4 py-3 text-sm"
              >
                <div className="flex flex-wrap gap-x-5 gap-y-1">
                  <span className="font-medium">叙事图谱生成完成</span>
                  <span>
                    生成时间 {formatGeneratedAt(ensureMutation.data.generated_at)}
                  </span>
                  <span>
                    耗时{' '}
                    {formatRefreshDurationMs(
                      ensureMutation.data.elapsed_ms > 0
                        ? ensureMutation.data.elapsed_ms
                        : 1000
                    )}
                  </span>
                  <span>版本 #{ensureMutation.data.version_id}</span>
                  <span>节点 {ensureMutation.data.node_count}</span>
                  <span>边 {ensureMutation.data.edge_count}</span>
                  {ensureMutation.data.model_queued ? <span>模型补边已排队</span> : null}
                </div>
                <p className="text-xs text-muted-foreground">
                  这是题材之间的主线/支线关系。单题材概念树请切到「概念树模式」后点击「生成概念树」。
                </p>
              </div>
            ) : null}

            {ensureError ? (
              <div
                role="alert"
                data-testid="mainline-ensure-error"
                className="space-y-1 rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive"
              >
                <p className="font-medium">生成失败 · {ensureError.title}</p>
                <p className="text-muted-foreground">{ensureError.description}</p>
              </div>
            ) : null}

            <div className="flex flex-wrap items-end gap-4">
              <div
                role="group"
                aria-label="图谱模式"
                className="inline-flex rounded-lg border border-border p-0.5"
                data-testid="mainline-mode-toggle"
              >
                <button
                  type="button"
                  aria-pressed={mode === 'narrative'}
                  onClick={() => patchParams({ mode: 'narrative' })}
                  className={`rounded-md px-3 py-1.5 text-sm ${
                    mode === 'narrative'
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:bg-accent'
                  }`}
                >
                  叙事模式
                </button>
                <button
                  type="button"
                  aria-pressed={mode === 'concept'}
                  onClick={() => patchParams({ mode: 'concept' })}
                  className={`rounded-md px-3 py-1.5 text-sm ${
                    mode === 'concept'
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:bg-accent'
                  }`}
                >
                  概念树模式
                </button>
              </div>

              <label className="flex flex-wrap items-center gap-2 text-sm">
                <span className="text-muted-foreground">交易日</span>
                <input
                  type="date"
                  value={tradeDate}
                  onChange={(e) =>
                    patchParams({
                      date: e.target.value || null,
                      versionId: null,
                    })
                  }
                  className="rounded-lg border border-border bg-background px-3 py-1.5 tabular-nums"
                />
                {view?.trade_date ? (
                  <span className="text-xs text-muted-foreground">当前 {displayDate}</span>
                ) : null}
              </label>

              <label className="flex flex-wrap items-center gap-2 text-sm">
                <span className="text-muted-foreground">版本</span>
                <select
                  aria-label="选择图谱版本"
                  value={versionExists ? (versionId ?? '') : ''}
                  onChange={(e) =>
                    patchParams({
                      versionId: e.target.value ? e.target.value : null,
                    })
                  }
                  className="rounded-lg border border-border bg-background px-3 py-1.5"
                >
                  <option value="">默认（published / auto）</option>
                  {versions.map((version) => (
                    <option key={version.id} value={version.id}>
                      #{version.id} · {version.kind}
                      {version.title ? ` · ${version.title}` : ''} · {version.status}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </section>
        </GlowCard>

        {mode === 'concept' ? (
          <GlowCard>
            <div className="p-6 sm:p-8">
              <ConceptTreeMode themeId={themeId} tradeDate={tradeDate} />
            </div>
          </GlowCard>
        ) : viewQuery.isLoading || staleVersionId ? (
          <GlowCard>
            <p className="flex items-center gap-2 p-6 text-sm text-muted-foreground sm:p-8">
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              {staleVersionId ? '版本已失效，正在回退默认视图…' : '加载主线图谱…'}
            </p>
          </GlowCard>
        ) : viewQuery.isError ? (
          <GlowCard>
            <div className="space-y-3 p-6 text-sm sm:p-8">
              <p className="text-destructive">主线图谱加载失败</p>
              <button
                type="button"
                className="rounded-lg border border-border px-3 py-1.5 hover:bg-accent"
                onClick={() => {
                  patchParams({ versionId: null })
                  void viewQuery.refetch()
                }}
              >
                清除版本并重试
              </button>
            </div>
          </GlowCard>
        ) : (
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
            <GlowCard>
              <div className="p-4 sm:p-6">
                <MainlineNarrativeChart
                  nodes={nodes}
                  edges={edges}
                  selectedThemeId={themeId}
                  onSelectTheme={(id) => patchParams({ themeId: String(id) })}
                />
              </div>
            </GlowCard>
            {selectedNode ? (
              <MainlineDrawer
                node={selectedNode}
                edges={edges}
                nodesByThemeId={nodesByThemeId}
                onClose={() => patchParams({ themeId: null })}
                onOpenConcept={(id) =>
                  patchParams({ themeId: String(id), mode: 'concept' })
                }
              />
            ) : (
              <GlowCard>
                <p className="p-6 text-sm text-muted-foreground sm:p-8">
                  点击节点查看阶段、强度与相连支线
                </p>
              </GlowCard>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
