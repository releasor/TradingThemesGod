/** Toast 通知组件
 *
 * 提供全局 Toast 通知功能，支持 success/error/warning/info 类型。
 */

import { useState, useCallback, useEffect } from 'react'
import { X, CheckCircle, AlertCircle, AlertTriangle, Info } from 'lucide-react'
import { cn } from '@/lib/utils'

/** Toast 类型 */
export type ToastType = 'success' | 'error' | 'warning' | 'info'

/** Toast 数据结构 */
export interface Toast {
  id: string
  type: ToastType
  message: string
  duration: number
}

/** Toast 容器属性 */
interface ToastContainerProps {
  toasts: Toast[]
  onClose: (id: string) => void
}

/** 类型对应的图标和颜色 */
const TOAST_CONFIG: Record<ToastType, { icon: typeof CheckCircle; className: string }> = {
  success: { icon: CheckCircle, className: 'border-green-500/30 bg-green-500/10 text-green-600' },
  error: { icon: AlertCircle, className: 'border-red-500/30 bg-red-500/10 text-red-600' },
  warning: { icon: AlertTriangle, className: 'border-yellow-500/30 bg-yellow-500/10 text-yellow-600' },
  info: { icon: Info, className: 'border-blue-500/30 bg-blue-500/10 text-blue-600' },
}

/** 单个 Toast 通知 */
function ToastItem({ toast, onClose }: { toast: Toast; onClose: (id: string) => void }) {
  const config = TOAST_CONFIG[toast.type]
  const Icon = config.icon

  useEffect(() => {
    const timer = setTimeout(() => onClose(toast.id), toast.duration)
    return () => clearTimeout(timer)
  }, [toast.id, toast.duration, onClose])

  return (
    <div
      className={cn(
        'flex items-center gap-3 rounded-lg border px-4 py-3 shadow-lg backdrop-blur-sm',
        'animate-in slide-in-from-right-full fade-in duration-300',
        config.className,
      )}
    >
      <Icon className="h-4 w-4 shrink-0" />
      <p className="flex-1 text-sm">{toast.message}</p>
      <button
        onClick={() => onClose(toast.id)}
        className="shrink-0 rounded p-0.5 hover:bg-black/10"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  )
}

/** Toast 容器 */
export function ToastContainer({ toasts, onClose }: ToastContainerProps) {
  if (toasts.length === 0) return null

  return (
    <div className="fixed bottom-4 right-4 z-50 flex w-80 flex-col gap-2">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onClose={onClose} />
      ))}
    </div>
  )
}

/** Toast Hook */
export function useToast() {
  const [toasts, setToasts] = useState<Toast[]>([])

  const addToast = useCallback(
    (type: ToastType, message: string, duration = 4000): string => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
      setToasts((prev) => [...prev, { id, type, message, duration }])
      return id
    },
    [],
  )

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const success = useCallback(
    (message: string, duration?: number) => addToast('success', message, duration),
    [addToast],
  )
  const error = useCallback(
    (message: string, duration?: number) => addToast('error', message, duration),
    [addToast],
  )
  const warning = useCallback(
    (message: string, duration?: number) => addToast('warning', message, duration),
    [addToast],
  )
  const info = useCallback(
    (message: string, duration?: number) => addToast('info', message, duration),
    [addToast],
  )

  return { toasts, addToast, removeToast, success, error, warning, info }
}
