/** 主线图谱 · 概念树模式 */

import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronDown, ChevronRight, Loader2, Network } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { fetchMainlineThemeConcept } from '@/api/mainline-graph'
import { refreshConceptGraph } from '@/api/theme'
import { ThemeLifecycleBadge } from '@/components/ThemeLifecycleBadge'
import {
  formatRefreshDurationMs,
  useRefreshTimer,
} from '@/hooks/useRefreshTimer'
import { getErrorMessage } from '@/lib/error-messages'
import { useAuthStore } from '@/stores/auth'
import type { ConceptNode } from '@/types/theme'
import type { LifecycleStage } from '@/types/short-term'

interface ConceptTreeModeProps {
  themeId: number | null
  tradeDate?: string
}

const REFUSAL_MARKERS = [
  '未触及',
  '未提供',
  '无法构建',
  '无法建立',
  '不足以',
  '没有实质',
  '无实质',
  '证据不足',
  '无法从',
  '未能提取',
]

function isRefusalLikeNode(node: ConceptNode): boolean {
  const blob = `${node.name} ${node.description ?? ''} ${node.market_logic ?? ''}`
  return REFUSAL_MARKERS.some((marker) => blob.includes(marker))
}

function hasUsableConceptTree(roots: ConceptNode[], nodeCount: number): boolean {
  if (nodeCount <= 0 || roots.length === 0) return false
  if (roots.length === 1 && (roots[0].children?.length ?? 0) === 0) {
    if (isRefusalLikeNode(roots[0])) return false
    if ((roots[0].stocks?.length ?? 0) === 0) return false
  }
  return true
}

function SimpleConceptNode({
  node,
  depth,
}: {
  node: ConceptNode
  depth: number
}) {
  const [open, setOpen] = useState(depth < 1)
  const children = node.children ?? []
  const hasChildren = children.length > 0

  return (
    <li className="border-l border-border/70 pl-3">
      <div className="flex items-start gap-1 py-1.5">
        <button
          type="button"
          aria-label={open ? `收起${node.name}` : `展开${node.name}`}
          disabled={!hasChildren}
          onClick={() => setOpen((v) => !v)}
          className="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground disabled:opacity-30"
        >
          {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        </button>
        <div className="min-w-0">
          <div className="text-sm font-medium">{node.name}</div>
          {node.description ? (
            <p className="mt-0.5 text-xs text-muted-foreground">{node.description}</p>
          ) : null}
        </div>
      </div>
      {open && hasChildren ? (
        <ul className="space-y-0.5">
          {children.map((child) => (
            <SimpleConceptNode key={child.id} node={child} depth={depth + 1} />
          ))}
        </ul>
      ) : null}
    </li>
  )
}

export function ConceptTreeMode({ themeId, tradeDate }: ConceptTreeModeProps) {
  const queryClient = useQueryClient()
  const token = useAuthStore((s) => s.token)
  const isLoggedIn = Boolean(token)

  const conceptQuery = useQuery({
    queryKey: ['mainline-graph', 'concept', themeId, tradeDate ?? 'latest'],
    queryFn: () =>
      fetchMainlineThemeConcept(themeId!, tradeDate ? { trade_date: tradeDate } : {}),
    enabled: themeId != null,
    retry: 1,
  })

  const refreshMutation = useMutation({
    mutationFn: () => refreshConceptGraph(themeId!),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ['mainline-graph', 'concept', themeId],
      })
    },
  })

  const { elapsedLabel: refreshElapsed } = useRefreshTimer(refreshMutation.isPending)

  const roots = useMemo(
    () => conceptQuery.data?.concept_graph?.roots ?? [],
    [conceptQuery.data]
  )

  if (themeId == null) {
    return (
      <div
        data-testid="mainline-concept-empty"
        className="flex min-h-[360px] flex-col items-center justify-center rounded-xl border border-dashed border-border p-8 text-center"
      >
        <Network className="h-8 w-8 text-muted-foreground" aria-hidden="true" />
        <p className="mt-3 text-sm text-muted-foreground">
          请先在叙事模式选题材，或从抽屉进入概念树
        </p>
      </div>
    )
  }

  if (conceptQuery.isLoading) {
    return (
      <div className="flex min-h-[360px] items-center justify-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
        加载概念树…
      </div>
    )
  }

  if (conceptQuery.isError) {
    const err =
      conceptQuery.error instanceof Error
        ? getErrorMessage(conceptQuery.error)
        : getErrorMessage(0)
    return (
      <div
        data-testid="mainline-concept-error"
        className="space-y-3 rounded-xl border border-destructive/30 bg-destructive/5 p-6 text-sm"
      >
        <p className="font-medium text-destructive">概念树加载失败 · {err.title}</p>
        <p className="text-muted-foreground">{err.description}</p>
        <p className="text-xs text-muted-foreground">
          {err.suggestion}
          {err.title.includes('超时')
            ? ' 若刚点过「生成概念树」，请等生成结束后再打开本页。'
            : ''}
        </p>
        <button
          type="button"
          className="rounded-lg border border-border px-3 py-1.5 hover:bg-accent"
          onClick={() => void conceptQuery.refetch()}
        >
          重试
        </button>
      </div>
    )
  }

  const data = conceptQuery.data!
  const nodeCount = data.concept_graph?.node_count ?? 0
  const usableTree = hasUsableConceptTree(roots, nodeCount)
  const refusalHint =
    !usableTree && roots[0]?.description ? roots[0].description : null

  const refreshErrorMessage = (() => {
    if (!refreshMutation.isError) return null
    const err = refreshMutation.error as {
      response?: { status?: number; data?: { detail?: string } }
      message?: string
    }
    const status = err.response?.status
    const detail =
      typeof err.response?.data?.detail === 'string' ? err.response.data.detail : null
    if (status === 502 || status === 503 || status === 504) {
      return {
        title: status === 502 && detail ? '资料或模型结果不足' : '后端暂时不可达',
        description:
          detail ||
          'Vite 代理连不上 API（常见于后端未启动或刚重启）。请确认后端在 127.0.0.1:8000 运行后重试。',
      }
    }
    if (status === 401) {
      return { title: '未登录', description: '请先登录后再生成概念树。' }
    }
    if (status === 409) {
      return {
        title: '模型未就绪',
        description: detail || '请先在设置页配置并启用默认模型。',
      }
    }
    const mapped =
      refreshMutation.error instanceof Error
        ? getErrorMessage(refreshMutation.error)
        : getErrorMessage(status ?? 0)
    return {
      title: mapped.title,
      description: detail || mapped.description,
    }
  })()

  const refreshLooksSuccessful =
    refreshMutation.isSuccess &&
    refreshMutation.data &&
    !refreshMutation.isPending &&
    usableTree

  const refreshLooksEmptySuccess =
    refreshMutation.isSuccess &&
    refreshMutation.data &&
    !refreshMutation.isPending &&
    !usableTree

  return (
    <div data-testid="mainline-concept-mode" className="space-y-4">
      <div className="rounded-xl border border-border bg-card/60 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="text-base font-semibold">
              {data.theme_name || `题材 ${data.theme_id}`}
            </h2>
            <ThemeLifecycleBadge stage={data.lifecycle_stage as LifecycleStage | null} />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {isLoggedIn ? (
              <button
                type="button"
                onClick={() => refreshMutation.mutate()}
                disabled={refreshMutation.isPending}
                className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground disabled:opacity-60"
              >
                {refreshMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                ) : null}
                {refreshMutation.isPending
                  ? `生成概念树（${refreshElapsed}）`
                  : '生成概念树'}
              </button>
            ) : null}
            <Link
              to={`/themes/${themeId}`}
              className="rounded-lg border border-border px-3 py-1.5 text-sm hover:bg-accent"
            >
              题材详情
            </Link>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap gap-4 text-sm">
          <span className="text-muted-foreground">
            强度{' '}
            <strong className="tabular-nums text-foreground">
              {data.strength_score ?? '—'}
            </strong>
          </span>
          <span className="text-muted-foreground">
            主线{' '}
            <strong className="tabular-nums text-foreground">
              {data.mainline_score ?? '—'}
            </strong>
          </span>
        </div>
      </div>

      {refreshMutation.isPending ? (
        <div
          role="status"
          data-testid="mainline-concept-refresh-progress"
          className="rounded-xl border border-primary/30 bg-primary/5 px-4 py-3 text-sm text-muted-foreground"
        >
          正在用模型生成「{data.theme_name || `题材 ${themeId}`}」概念树（已耗时{' '}
          {refreshElapsed}）…
        </div>
      ) : null}

      {refreshLooksSuccessful ? (
        <div
          role="status"
          data-testid="mainline-concept-refresh-result"
          className="flex flex-wrap gap-x-5 gap-y-1 rounded-xl border border-primary/30 bg-primary/5 px-4 py-3 text-sm"
        >
          <span className="font-medium">概念树已更新</span>
          <span>{refreshMutation.data!.message}</span>
          <span>耗时 {formatRefreshDurationMs(refreshMutation.data!.elapsed_ms)}</span>
          <span>新增 {refreshMutation.data!.added_nodes}</span>
          <span>更新 {refreshMutation.data!.updated_nodes}</span>
        </div>
      ) : null}

      {refreshLooksEmptySuccess ? (
        <div
          role="status"
          data-testid="mainline-concept-refresh-weak"
          className="rounded-xl border border-amber-500/30 bg-amber-500/5 px-4 py-3 text-sm text-amber-800 dark:text-amber-200"
        >
          接口返回了写入结果，但公开资料不足以形成可展开概念树（常见为模型写了「无法构建」说明节点）。请稍后重试或换模型。
        </div>
      ) : null}

      {refreshErrorMessage ? (
        <div
          role="alert"
          className="space-y-1 rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive"
        >
          <p className="font-medium">概念树生成失败 · {refreshErrorMessage.title}</p>
          <p className="text-muted-foreground">{refreshErrorMessage.description}</p>
        </div>
      ) : null}

      {!usableTree ? (
        <div
          data-testid="mainline-concept-graph-empty"
          className="rounded-xl border border-dashed border-border py-12 text-center"
        >
          <Network className="mx-auto h-7 w-7 text-muted-foreground" aria-hidden="true" />
          <p className="mt-2 text-sm text-muted-foreground">该题材尚无可用概念图谱</p>
          {refusalHint ? (
            <p className="mx-auto mt-2 max-w-lg text-xs text-muted-foreground">
              上次结果：{refusalHint}
            </p>
          ) : (
            <p className="mx-auto mt-1 max-w-md text-xs text-muted-foreground">
              顶部「生成叙事图谱」只生成题材之间的<strong>叙事关系</strong>
              ，不会写入单题材概念树。请点击上方「生成概念树」（需登录并配置模型）。
            </p>
          )}
        </div>
      ) : (
        <ul className="space-y-1 rounded-xl border border-border p-4" data-testid="mainline-concept-tree">
          {roots.map((node) => (
            <SimpleConceptNode key={node.id} node={node} depth={0} />
          ))}
        </ul>
      )}
    </div>
  )
}
