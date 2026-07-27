/** 主线图谱节点详情抽屉 */

import { Link } from 'react-router-dom'
import { X } from 'lucide-react'
import { ThemeLifecycleBadge } from '@/components/ThemeLifecycleBadge'
import type { MainlineGraphEdgeItem, MainlineGraphNodeItem } from '@/types/mainline-graph'
import type { LifecycleStage } from '@/types/short-term'

interface MainlineDrawerProps {
  node: MainlineGraphNodeItem | null
  edges: MainlineGraphEdgeItem[]
  nodesByThemeId: Map<number, MainlineGraphNodeItem>
  onClose: () => void
  onOpenConcept: (themeId: number) => void
}

function edgePeerName(
  edge: MainlineGraphEdgeItem,
  themeId: number,
  nodesByThemeId: Map<number, MainlineGraphNodeItem>
): string {
  const peerId = edge.from_theme_id === themeId ? edge.to_theme_id : edge.from_theme_id
  return nodesByThemeId.get(peerId)?.theme_name ?? `题材 ${peerId}`
}

export function MainlineDrawer({
  node,
  edges,
  nodesByThemeId,
  onClose,
  onOpenConcept,
}: MainlineDrawerProps) {
  if (!node) return null

  const connected = edges.filter(
    (edge) => edge.from_theme_id === node.theme_id || edge.to_theme_id === node.theme_id
  )

  return (
    <aside
      data-testid="mainline-drawer"
      className="flex h-full min-h-[420px] flex-col rounded-xl border border-border bg-card/80 p-4 shadow-sm"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h2 className="truncate text-base font-semibold">{node.theme_name || `题材 ${node.theme_id}`}</h2>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <ThemeLifecycleBadge stage={node.lifecycle_stage as LifecycleStage} />
            <span className="rounded-full border border-border px-2 py-0.5 text-[11px] text-muted-foreground">
              {node.role}
            </span>
          </div>
        </div>
        <button
          type="button"
          aria-label="关闭抽屉"
          onClick={onClose}
          className="rounded-lg border border-border p-1.5 text-muted-foreground hover:bg-accent"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div className="rounded-lg border border-border/70 p-3">
          <dt className="text-xs text-muted-foreground">主线分</dt>
          <dd className="mt-1 text-lg font-semibold tabular-nums">{node.mainline_score}</dd>
        </div>
        <div className="rounded-lg border border-border/70 p-3">
          <dt className="text-xs text-muted-foreground">强度分</dt>
          <dd className="mt-1 text-lg font-semibold tabular-nums">{node.strength_score}</dd>
        </div>
      </dl>

      <div className="mt-4 flex-1 overflow-auto">
        <h3 className="text-sm font-medium">相连边</h3>
        {connected.length === 0 ? (
          <p className="mt-2 text-xs text-muted-foreground">暂无相连边</p>
        ) : (
          <ul className="mt-2 space-y-2" data-testid="mainline-drawer-edges">
            {connected.map((edge) => (
              <li
                key={edge.id}
                className="rounded-lg border border-border/60 px-3 py-2 text-xs"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium">
                    {edgePeerName(edge, node.theme_id, nodesByThemeId)}
                  </span>
                  <span className="tabular-nums text-muted-foreground">
                    {(edge.weight * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="mt-1 flex flex-wrap gap-2 text-muted-foreground">
                  <span>{edge.method}</span>
                  <span>{edge.status}</span>
                </div>
                {edge.rationale ? (
                  <p className="mt-1 text-muted-foreground">{edge.rationale}</p>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="mt-4 flex flex-wrap gap-2 border-t border-border pt-4">
        <button
          type="button"
          onClick={() => onOpenConcept(node.theme_id)}
          className="rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground"
        >
          查看概念树
        </button>
        <Link
          to={`/themes/${node.theme_id}`}
          className="rounded-lg border border-border px-3 py-1.5 text-sm hover:bg-accent"
        >
          题材详情
        </Link>
      </div>
    </aside>
  )
}
