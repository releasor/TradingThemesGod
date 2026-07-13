/** 产业链三列布局组件
 *
 * 显示上游、中游、下游三个列，每列包含对应的链路点卡片。
 */

import { ArrowUp, ArrowDown, ArrowRight } from 'lucide-react'
import { ChainPointCard } from '@/components/ChainPointCard'
import type { IndustryChainBrief } from '@/types/theme'

interface IndustryChainSectionProps {
  chains: {
    upstream: IndustryChainBrief[]
    midstream: IndustryChainBrief[]
    downstream: IndustryChainBrief[]
  }
  themeId: number
}

/** 产业链层级配置 */
const LEVEL_CONFIG = {
  upstream: {
    label: '上游',
    icon: ArrowUp,
    description: '原材料、零部件、基础服务',
    color: 'text-blue-600 bg-blue-50',
  },
  midstream: {
    label: '中游',
    icon: ArrowRight,
    description: '制造、加工、集成',
    color: 'text-orange-600 bg-orange-50',
  },
  downstream: {
    label: '下游',
    icon: ArrowDown,
    description: '应用、销售、服务',
    color: 'text-green-600 bg-green-50',
  },
} as const

export function IndustryChainSection({ chains, themeId }: IndustryChainSectionProps) {
  const levels = ['upstream', 'midstream', 'downstream'] as const

  return (
    <section>
      <h2 className="mb-4 text-lg font-semibold text-foreground">产业链</h2>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {levels.map((level) => {
          const config = LEVEL_CONFIG[level]
          const Icon = config.icon
          const chainPoints = chains[level] ?? []

          return (
            <div key={level} className="space-y-3">
              {/* 列头 */}
              <div className="flex items-center gap-2">
                <div className={`rounded-md p-1.5 ${config.color}`}>
                  <Icon className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="font-medium text-foreground">{config.label}</h3>
                  <p className="text-xs text-muted-foreground">{config.description}</p>
                </div>
              </div>

              {/* 链路点列表 */}
              {chainPoints.length > 0 ? (
                <div className="space-y-2">
                  {chainPoints.map((chainPoint) => (
                    <ChainPointCard
                      key={chainPoint.id}
                      chainPoint={chainPoint}
                      themeId={themeId}
                    />
                  ))}
                </div>
              ) : (
                <div className="rounded-lg border border-dashed border-border p-4 text-center text-sm text-muted-foreground">
                  暂无数据
                </div>
              )}
            </div>
          )
        })}
      </div>
    </section>
  )
}
