/** 空状态组件

提供友好的空状态展示和引导。
*/

import { cn } from '@/lib/utils'
import { Inbox, Search, AlertCircle, FileText, BarChart3 } from 'lucide-react'

/** 空状态类型 */
export type EmptyStateType = 'no-data' | 'no-results' | 'error' | 'no-content' | 'custom'

/** 空状态配置 */
interface EmptyStateConfig {
  icon: typeof Inbox
  title: string
  description: string
}

/** 空状态类型配置 */
const emptyStateConfigs: Record<EmptyStateType, EmptyStateConfig> = {
  'no-data': {
    icon: Inbox,
    title: '暂无数据',
    description: '还没有任何数据，稍后再来看看吧',
  },
  'no-results': {
    icon: Search,
    title: '未找到结果',
    description: '没有找到匹配的结果，试试其他关键词',
  },
  'error': {
    icon: AlertCircle,
    title: '加载失败',
    description: '数据加载出错了，请稍后重试',
  },
  'no-content': {
    icon: FileText,
    title: '内容为空',
    description: '这里还没有内容',
  },
  'custom': {
    icon: BarChart3,
    title: '',
    description: '',
  },
}

/** 空状态组件属性 */
interface EmptyStateProps {
  /** 空状态类型 */
  type?: EmptyStateType
  /** 自定义标题 */
  title?: string
  /** 自定义描述 */
  description?: string
  /** 自定义图标 */
  icon?: typeof Inbox
  /** 自定义操作 */
  action?: React.ReactNode
  /** 自定义类名 */
  className?: string
}

/**
 * 空状态组件
 *
 * @example
 * ```tsx
 * // 基本用法
 * <EmptyState type="no-data" />
 *
 * // 自定义内容
 * <EmptyState
 *   title="暂无题材"
 *   description="请先运行爬虫采集数据"
 *   action={<Button onClick={runScraper}>开始采集</Button>}
 * />
 * ```
 */
export function EmptyState({
  type = 'no-data',
  title,
  description,
  icon: CustomIcon,
  action,
  className,
}: EmptyStateProps) {
  const config = emptyStateConfigs[type]
  const Icon = CustomIcon || config.icon
  const displayTitle = title || config.title
  const displayDescription = description || config.description

  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center px-6 py-12 text-center',
        className
      )}
    >
      <div className="rounded-full bg-muted p-4">
        <Icon className="h-10 w-10 text-muted-foreground" />
      </div>
      <h3 className="mt-4 text-lg font-semibold text-foreground">
        {displayTitle}
      </h3>
      <p className="mt-2 text-sm text-muted-foreground max-w-sm">
        {displayDescription}
      </p>
      {action && <div className="mt-6">{action}</div>}
    </div>
  )
}
