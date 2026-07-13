/** 错误展示组件

为不同类型的错误提供友好的展示界面。
*/

import { AlertCircle, RefreshCw, WifiOff, Clock, Server, ShieldQuestion, FileQuestion } from 'lucide-react'
import { cn } from '@/lib/utils'
import { type ErrorType, getErrorMessageByType } from '@/lib/error-messages'

/** 错误图标映射 */
const errorIcons: Record<ErrorType, typeof AlertCircle> = {
  network: WifiOff,
  timeout: Clock,
  server: Server,
  'not-found': FileQuestion,
  unauthorized: ShieldQuestion,
  forbidden: ShieldQuestion,
  validation: AlertCircle,
  unknown: AlertCircle,
}

/** 错误展示组件属性 */
interface ErrorDisplayProps {
  /** 错误类型 */
  errorType: ErrorType
  /** 自定义标题 */
  title?: string
  /** 自定义描述 */
  description?: string
  /** 重试回调 */
  onRetry?: () => void
  /** 自定义类名 */
  className?: string
}

/**
 * 错误展示组件
 *
 * @example
 * ```tsx
 * <ErrorDisplay
 *   errorType="network"
 *   onRetry={() => refetch()}
 * />
 * ```
 */
export function ErrorDisplay({
  errorType,
  title,
  description,
  onRetry,
  className,
}: ErrorDisplayProps) {
  const error = getErrorMessageByType(errorType)
  const Icon = errorIcons[errorType]

  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center px-6 py-12 text-center',
        className
      )}
    >
      <div className="rounded-full bg-destructive/10 p-4">
        <Icon className="h-10 w-10 text-destructive" />
      </div>
      <h3 className="mt-4 text-lg font-semibold text-foreground">
        {title || error.title}
      </h3>
      <p className="mt-2 text-sm text-muted-foreground max-w-sm">
        {description || error.description}
      </p>
      <p className="mt-1 text-xs text-muted-foreground">
        {error.suggestion}
      </p>
      {onRetry && error.retryable && (
        <button
          onClick={onRetry}
          className="mt-6 inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          <RefreshCw className="h-4 w-4" />
          重试
        </button>
      )}
    </div>
  )
}
