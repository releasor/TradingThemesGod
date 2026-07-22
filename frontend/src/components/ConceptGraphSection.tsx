import { useMemo, useState } from 'react'
import { ChevronsDownUp, ChevronsUpDown, Search, Network } from 'lucide-react'
import { ConceptTreeNode } from './ConceptTreeNode'
import type { ConceptGraph, ConceptNode } from '@/types/theme'

function walk(nodes: ConceptNode[], output: ConceptNode[] = []) {
  for (const node of nodes) { output.push(node); walk(node.children, output) }
  return output
}

function filterNodes(nodes: ConceptNode[], query: string): ConceptNode[] {
  if (!query) return nodes
  const keyword = query.toLowerCase()
  return nodes.flatMap((node) => {
    const children = filterNodes(node.children, query)
    const text = [node.name, node.description, node.market_logic, ...node.stocks.flatMap((stock) => [stock.code, stock.name, stock.rationale])].filter(Boolean).join(' ').toLowerCase()
    return text.includes(keyword) || children.length ? [{ ...node, children }] : []
  })
}

export function ConceptGraphSection({ graph }: { graph: ConceptGraph }) {
  const allNodes = useMemo(() => walk(graph.roots), [graph.roots])
  const [query, setQuery] = useState('')
  const [expanded, setExpanded] = useState<Set<number>>(() => new Set(allNodes.filter((node) => node.depth < 2).map((node) => node.id)))
  const visible = useMemo(() => filterNodes(graph.roots, query.trim()), [graph.roots, query])
  const effectiveExpanded = query ? new Set(allNodes.map((node) => node.id)) : expanded

  if (graph.node_count === 0) return <section className="border-y border-dashed border-border py-10 text-center"><Network className="mx-auto h-7 w-7 text-muted-foreground" /><p className="mt-2 text-sm text-muted-foreground">该题材尚无经过核验的细分图谱</p></section>

  return <section>
    <div className="flex flex-col gap-3 border-b border-border pb-4 sm:flex-row sm:items-end sm:justify-between">
      <div><h2 className="text-lg font-semibold">概念细分知识图谱</h2><p className="mt-1 text-xs text-muted-foreground">{graph.node_count} 个节点 · {graph.stock_count} 只关联股票 · 最深 {graph.max_depth + 1} 层</p></div>
      <div className="flex flex-wrap items-center gap-2">
        <label className="relative min-w-0 flex-1 sm:w-64"><Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索细分、技术或股票" className="h-9 w-full border border-border bg-background pl-9 pr-3 text-sm outline-none focus:border-primary" /></label>
        <button title="全部展开" aria-label="全部展开" onClick={() => setExpanded(new Set(allNodes.map((node) => node.id)))} className="h-9 w-9 border border-border p-2 hover:bg-accent"><ChevronsUpDown className="h-4 w-4" /></button>
        <button title="全部收起" aria-label="全部收起" onClick={() => setExpanded(new Set())} className="h-9 w-9 border border-border p-2 hover:bg-accent"><ChevronsDownUp className="h-4 w-4" /></button>
      </div>
    </div>
    <div className="pt-2">{visible.map((node) => <ConceptTreeNode key={node.id} node={node} expanded={effectiveExpanded} onToggle={(id) => setExpanded((current) => { const next = new Set(current); next.has(id) ? next.delete(id) : next.add(id); return next })} />)}</div>
    {visible.length === 0 && <p className="py-8 text-center text-sm text-muted-foreground">没有匹配的细分或股票</p>}
  </section>
}
