import { Link, useNavigate } from 'react-router-dom'
import { LogIn, LogOut, UserRound } from 'lucide-react'

import { useAuthStore } from '@/stores/auth'
import { cn } from '@/lib/utils'

/** 顶栏右侧：当前账号 / 登录注册 / 退出 */
export function AuthNav({ className = '' }: { className?: string }) {
  const navigate = useNavigate()
  const token = useAuthStore((state) => state.token)
  const user = useAuthStore((state) => state.user)
  const clearAuth = useAuthStore((state) => state.clearAuth)

  if (!token) {
    return (
      <div className={cn('flex items-center gap-1.5', className)} data-testid="auth-nav">
        <Link
          to="/login"
          className="inline-flex h-9 items-center gap-1.5 rounded-xl border border-border/70 bg-background/70 px-2.5 text-xs font-medium backdrop-blur-sm hover:bg-accent sm:text-sm"
        >
          <LogIn className="h-3.5 w-3.5" />
          登录
        </Link>
        <Link
          to="/register"
          className="inline-flex h-9 items-center gap-1.5 rounded-xl border border-border/50 bg-primary px-2.5 text-xs font-medium text-primary-foreground hover:opacity-90 sm:text-sm"
        >
          注册
        </Link>
      </div>
    )
  }

  return (
    <div className={cn('flex items-center gap-1.5', className)} data-testid="auth-nav">
      <span
        className="hidden max-w-[7.5rem] truncate rounded-xl border border-border/70 bg-background/70 px-2.5 py-1.5 text-xs text-muted-foreground backdrop-blur-sm sm:inline-flex sm:items-center sm:gap-1.5 sm:text-sm"
        title={user?.username}
      >
        <UserRound className="h-3.5 w-3.5 shrink-0" />
        <span className="truncate text-foreground">{user?.username}</span>
      </span>
      <button
        type="button"
        onClick={() => {
          clearAuth()
          navigate('/login')
        }}
        className="inline-flex h-9 items-center gap-1.5 rounded-xl border border-border/70 bg-background/70 px-2.5 text-xs font-medium backdrop-blur-sm hover:bg-accent sm:text-sm"
        aria-label="退出登录"
      >
        <LogOut className="h-3.5 w-3.5" />
        <span className="hidden sm:inline">退出</span>
      </button>
    </div>
  )
}
