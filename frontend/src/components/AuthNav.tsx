import { Link, useNavigate } from 'react-router-dom'
import { LogIn, LogOut, UserPlus } from 'lucide-react'

import { useAuthStore } from '@/stores/auth'

export function AuthNav() {
  const navigate = useNavigate()
  const token = useAuthStore((state) => state.token)
  const user = useAuthStore((state) => state.user)
  const clearAuth = useAuthStore((state) => state.clearAuth)

  if (!token) {
    return (
      <div className="flex items-center gap-2">
        <Link
          to="/login"
          className="inline-flex items-center gap-1 rounded-lg border border-border/60 px-3 py-1.5 text-sm hover:bg-muted/50"
        >
          <LogIn className="h-4 w-4" />
          登录
        </Link>
        <Link
          to="/register"
          className="inline-flex items-center gap-1 rounded-lg bg-primary px-3 py-1.5 text-sm text-primary-foreground hover:opacity-90"
        >
          <UserPlus className="h-4 w-4" />
          注册
        </Link>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-3">
      <span className="text-sm text-muted-foreground">{user?.username}</span>
      <button
        type="button"
        onClick={() => {
          clearAuth()
          navigate('/login')
        }}
        className="inline-flex items-center gap-1 rounded-lg border border-border/60 px-3 py-1.5 text-sm hover:bg-muted/50"
      >
        <LogOut className="h-4 w-4" />
        退出
      </button>
    </div>
  )
}
