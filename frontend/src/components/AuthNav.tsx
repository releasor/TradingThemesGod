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
      <Link
        to="/settings/account"
        className="inline-flex h-9 max-w-[9rem] items-center gap-1.5 truncate rounded-xl border border-border/70 bg-background/70 px-2.5 text-xs text-muted-foreground backdrop-blur-sm hover:bg-accent sm:text-sm"
        title={user?.username ? `${user.username} · 账号设置` : '账号设置'}
        aria-label="打开账号设置"
      >
        <UserRound className="h-3.5 w-3.5 shrink-0" />
        <span className="hidden truncate text-foreground sm:inline">{user?.username}</span>
      </Link>
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
