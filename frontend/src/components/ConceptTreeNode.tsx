import { ChevronDown, ChevronRight, ExternalLink, ShieldCheck, Star } from 'lucide-react'
import type { ConceptNode } from '@/types/theme'

const levelLabels = { upstream: '上游', midstream: '中游', downstream: '下游' }
const typeLabels: Record<string, string> = { domain: '主题', segment: '分支', product: '产品', component: '部件', technology: '技术', material: '材料', application: '应用' }

interface Props {
  node: ConceptNode
  expanded: Set<number>
  onToggle: (id: number) => void
}

export function ConceptTreeNode({ node, expanded, onToggle }: Props) {
  const isOpen = expanded.has(node.id)
  const hasChildren = node.children.length > 0
  return (
    <div className="border-l border-border pl-3 sm:pl-5">
      <div className="border-b border-border/70 py-3">
        <div className="flex min-w-0 items-start gap-2">
          <button aria-label={isOpen ? `收起${node.name}` : `展开${node.name}`} disabled={!hasChildren} onClick={() => onToggle(node.id)} className="mt-0.5 h-6 w-6 shrink-0 text-muted-foreground disabled:opacity-30">
            {isOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          </button>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-sm font-semibold text-foreground">{node.name}</h3>
              <span className="border border-border px-1.5 py-0.5 text-[11px] text-muted-foreground">{typeLabels[node.node_type] ?? node.node_type}</span>
              {node.chain_level && <span className="bg-muted px-1.5 py-0.5 text-[11px] text-foreground">{levelLabels[node.chain_level]}</span>}
              <span className="inline-flex items-center gap-1 text-[11px] text-emerald-700"><ShieldCheck className="h-3 w-3" />可信度 {Math.round(Number(node.confidence) * 100)}%</span>
            </div>
            {node.description && <p className="mt-1 text-xs leading-5 text-muted-foreground">{node.description}</p>}
            {node.market_logic && <p className="mt-2 text-xs leading-5"><span className="font-medium">市场逻辑：</span>{node.market_logic}</p>}
            {(node.catalysts.length > 0 || node.risks.length > 0) && <div className="mt-2 grid gap-2 text-xs sm:grid-cols-2">
              {node.catalysts.length > 0 && <div><span className="font-medium text-emerald-700">催化：</span>{node.catalysts.join('、')}</div>}
              {node.risks.length > 0 && <div><span className="font-medium text-rose-700">风险：</span>{node.risks.join('、')}</div>}
            </div>}
            {node.stocks.length > 0 && <div className="mt-3 divide-y divide-border border-y border-border">
              {node.stocks.map((stock) => <div key={stock.code} className="py-2 text-xs">
                <div className="flex flex-wrap items-center gap-2"><span className="font-mono text-muted-foreground">{stock.code}</span><strong>{stock.name}</strong>{stock.is_core && <Star className="h-3 w-3 fill-amber-500 text-amber-500" />}<span className="text-muted-foreground">{stock.relation_type}</span><span>相关度 {Math.round(Number(stock.relevance_score) * 100)}%</span></div>
                <p className="mt-1 leading-5 text-muted-foreground">{stock.rationale}</p>
                {stock.sources.map((source) => <a key={source.url} href={source.url} target="_blank" rel="noreferrer" className="mt-1 inline-flex items-center gap-1 text-primary hover:underline">{source.title}<ExternalLink className="h-3 w-3" /></a>)}
              </div>)}
            </div>}
            {node.sources.length > 0 && <div className="mt-2 flex flex-wrap gap-3">{node.sources.map((source) => <a key={source.url} href={source.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-[11px] text-primary hover:underline">{source.publisher ?? source.title}<ExternalLink className="h-3 w-3" /></a>)}</div>}
          </div>
        </div>
      </div>
      {isOpen && node.children.map((child) => <ConceptTreeNode key={child.id} node={child} expanded={expanded} onToggle={onToggle} />)}
    </div>
  )
}
