import { cn } from '@/lib/utils'

/** 骨架屏组件

提供加载状态的占位符，支持多种动画效果。
*/

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  /** 动画类型 */
  variant?: 'pulse' | 'wave' | 'shimmer'
}

function Skeleton({
  className,
  variant = 'pulse',
  ...props
}: SkeletonProps) {
  const variantClasses = {
    pulse: 'animate-pulse',
    wave: 'animate-wave',
    shimmer: 'animate-shimmer bg-gradient-to-r from-muted via-muted/50 to-muted bg-[length:200%_100%]',
  }

  return (
    <div
      className={cn(
        'rounded-xl bg-muted',
        variantClasses[variant],
        className
      )}
      {...props}
    />
  )
}

/** 骨架屏文本行 */
function SkeletonText({
  className,
  lines = 3,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { lines?: number }) {
  return (
    <div className={cn('space-y-2', className)} {...props}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={cn(
            'h-4',
            i === lines - 1 ? 'w-3/4' : 'w-full'
          )}
        />
      ))}
    </div>
  )
}

/** 骨架屏圆形 */
function SkeletonCircle({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <Skeleton
      className={cn('rounded-full', className)}
      {...props}
    />
  )
}

export { Skeleton, SkeletonText, SkeletonCircle }
