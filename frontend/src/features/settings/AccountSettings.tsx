import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  KeyRound,
  Palette,
  Settings2,
  Sparkles,
  UserRound,
} from 'lucide-react'
import { changePassword, fetchCurrentUser } from '@/api/auth'
import { SettingsSubnav } from '@/components/SettingsSubnav'
import { GlowCard } from '@/components/GlowCard'
import { useTheme } from '@/components/ThemeToggle'
import { useAuthStore } from '@/stores/auth'
import { cn } from '@/lib/utils'

function apiErrorMessage(error: unknown, fallback: string): string {
  const value = error as {
    response?: { data?: { detail?: string | { msg?: string }[]; message?: string } }
    message?: string
  }
  const detail = value.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg
  return value.response?.data?.message || value.message || fallback
}

function formatCreatedAt(value?: string): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

/** 账号设置页：账号信息、改密与界面偏好 */
export function AccountSettings() {
  const [searchParams] = useSearchParams()
  const fromPrompt = searchParams.get('from') === 'prompt'
  const token = useAuthStore((state) => state.token)
  const user = useAuthStore((state) => state.user)
  const setAuth = useAuthStore((state) => state.setAuth)
  const { theme, setTheme } = useTheme()

  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordError, setPasswordError] = useState('')
  const [passwordSuccess, setPasswordSuccess] = useState('')
  const [passwordLoading, setPasswordLoading] = useState(false)

  useEffect(() => {
    if (!token) return
    let cancelled = false
    void fetchCurrentUser()
      .then((fresh) => {
        if (cancelled) return
        setAuth(token, fresh)
      })
      .catch(() => {
        /* 保持本地缓存用户信息 */
      })
    return () => {
      cancelled = true
    }
  }, [token, setAuth])

  const accountHint = useMemo(() => {
    if (token && user?.username) return `已登录：${user.username}`
    return '未登录：可前往登录页登录；登录后可保存个人模型配置'
  }, [token, user?.username])

  async function handleChangePassword(event: React.FormEvent) {
    event.preventDefault()
    setPasswordError('')
    setPasswordSuccess('')

    if (newPassword.length < 6) {
      setPasswordError('新密码至少 6 位')
      return
    }
    if (newPassword !== confirmPassword) {
      setPasswordError('两次输入的新密码不一致')
      return
    }
    if (currentPassword === newPassword) {
      setPasswordError('新密码不能与当前密码相同')
      return
    }

    setPasswordLoading(true)
    try {
      await changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      })
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setPasswordSuccess('密码已更新')
    } catch (error) {
      setPasswordError(apiErrorMessage(error, '修改密码失败'))
    } finally {
      setPasswordLoading(false)
    }
  }

  return (
    <div className="min-h-screen">
      <main className="mx-auto w-full max-w-none space-y-5 px-3 py-6 sm:px-4 lg:px-5 xl:px-6">
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <Settings2 className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-xl font-semibold tracking-tight">账号设置</h1>
              <p className="text-sm text-muted-foreground">登录状态与界面偏好</p>
            </div>
          </div>
          <SettingsSubnav />
        </div>

        <p className="text-xs text-muted-foreground">{accountHint}</p>

        <div className="grid gap-4 lg:grid-cols-2">
          <GlowCard>
            <div className="space-y-4 p-5">
              <div className="flex items-center gap-2">
                <UserRound className="h-4 w-4 text-primary" />
                <h2 className="text-sm font-semibold">账号信息</h2>
              </div>
              {token && user ? (
                <dl className="space-y-3 text-sm">
                  <div className="flex items-center justify-between gap-3 rounded-xl border border-border/70 px-3 py-2.5">
                    <dt className="text-muted-foreground">用户名</dt>
                    <dd className="font-medium text-foreground">{user.username}</dd>
                  </div>
                  <div className="flex items-center justify-between gap-3 rounded-xl border border-border/70 px-3 py-2.5">
                    <dt className="text-muted-foreground">用户 ID</dt>
                    <dd className="font-medium text-foreground">{user.id}</dd>
                  </div>
                  <div className="flex items-center justify-between gap-3 rounded-xl border border-border/70 px-3 py-2.5">
                    <dt className="text-muted-foreground">注册时间</dt>
                    <dd className="font-medium text-foreground">
                      {formatCreatedAt(user.created_at)}
                    </dd>
                  </div>
                </dl>
              ) : (
                <p className="text-sm text-muted-foreground">
                  尚未登录。请先{' '}
                  <Link to="/login" className="text-primary hover:underline">
                    前往登录
                  </Link>
                  。
                </p>
              )}
            </div>
          </GlowCard>

          <GlowCard>
            <div className="space-y-4 p-5">
              <div className="flex items-center gap-2">
                <KeyRound className="h-4 w-4 text-primary" />
                <h2 className="text-sm font-semibold">修改密码</h2>
              </div>
              {token ? (
                <form className="space-y-3" onSubmit={handleChangePassword}>
                  <label className="block space-y-1.5 text-sm">
                    <span className="text-muted-foreground">当前密码</span>
                    <input
                      type="password"
                      autoComplete="current-password"
                      required
                      value={currentPassword}
                      onChange={(e) => setCurrentPassword(e.target.value)}
                      className="w-full rounded-xl border border-border bg-background px-3 py-2"
                    />
                  </label>
                  <label className="block space-y-1.5 text-sm">
                    <span className="text-muted-foreground">新密码</span>
                    <input
                      type="password"
                      autoComplete="new-password"
                      required
                      minLength={6}
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      className="w-full rounded-xl border border-border bg-background px-3 py-2"
                    />
                  </label>
                  <label className="block space-y-1.5 text-sm">
                    <span className="text-muted-foreground">确认新密码</span>
                    <input
                      type="password"
                      autoComplete="new-password"
                      required
                      minLength={6}
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className="w-full rounded-xl border border-border bg-background px-3 py-2"
                    />
                  </label>
                  {passwordError ? (
                    <p className="text-sm text-destructive">{passwordError}</p>
                  ) : null}
                  {passwordSuccess ? (
                    <p className="text-sm text-primary">{passwordSuccess}</p>
                  ) : null}
                  <button
                    type="submit"
                    disabled={passwordLoading}
                    className="inline-flex h-9 items-center rounded-xl bg-primary px-4 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-60"
                  >
                    {passwordLoading ? '保存中…' : '更新密码'}
                  </button>
                </form>
              ) : (
                <p className="text-sm text-muted-foreground">登录后可修改密码。</p>
              )}
            </div>
          </GlowCard>

          <GlowCard>
            <div className="space-y-4 p-5">
              <div className="flex items-center gap-2">
                <Palette className="h-4 w-4 text-primary" />
                <h2 className="text-sm font-semibold">界面主题</h2>
              </div>
              <div className="flex flex-wrap gap-2">
                {(
                  [
                    { value: 'light', label: '亮色' },
                    { value: 'dark', label: '暗色' },
                    { value: 'system', label: '跟随系统' },
                  ] as const
                ).map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => setTheme(option.value)}
                    className={cn(
                      'rounded-xl border px-3 py-2 text-sm transition-colors',
                      theme === option.value
                        ? 'border-primary bg-primary text-primary-foreground'
                        : 'border-border hover:bg-accent'
                    )}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
          </GlowCard>

          <GlowCard>
            <div className="space-y-4 p-5">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-primary" />
                <h2 className="text-sm font-semibold">模型与本地数据</h2>
              </div>
              <p className="text-sm text-muted-foreground">
                AI 模型、API Key 与默认配置请到{' '}
                <Link
                  to={fromPrompt ? '/settings/models?from=prompt' : '/settings/models'}
                  className="text-primary hover:underline"
                >
                  模型设置
                </Link>
                。
              </p>
            </div>
          </GlowCard>
        </div>
      </main>
    </div>
  )
}
