import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  Eraser,
  KeyRound,
  LayoutDashboard,
  Newspaper,
  Palette,
  Settings2,
  Sparkles,
  UserRound,
} from 'lucide-react'
import { changePassword, fetchCurrentUser } from '@/api/auth'
import { SettingsSubnav } from '@/components/SettingsSubnav'
import { GlowCard } from '@/components/GlowCard'
import { useTheme } from '@/components/ThemeToggle'
import { useDashboardStore } from '@/stores/dashboard'
import { useAuthStore } from '@/stores/auth'
import { cn } from '@/lib/utils'

const NEWS_AUTO_REFRESH_KEY = 'news-auto-refresh'
const SEARCH_HISTORY_KEY = 'search-history'
const LIMIT_OPTIONS = [10, 20, 30, 50] as const

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

/** 账号设置页：账号信息、改密与本地偏好 */
export function AccountSettings() {
  const [searchParams] = useSearchParams()
  const fromPrompt = searchParams.get('from') === 'prompt'
  const token = useAuthStore((state) => state.token)
  const user = useAuthStore((state) => state.user)
  const setAuth = useAuthStore((state) => state.setAuth)
  const { theme, setTheme } = useTheme()
  const limit = useDashboardStore((s) => s.limit)
  const showCharts = useDashboardStore((s) => s.showCharts)
  const showStats = useDashboardStore((s) => s.showStats)
  const setLimit = useDashboardStore((s) => s.setLimit)
  const toggleCharts = useDashboardStore((s) => s.toggleCharts)
  const toggleStats = useDashboardStore((s) => s.toggleStats)

  const [newsAutoRefresh, setNewsAutoRefresh] = useState(
    () => localStorage.getItem(NEWS_AUTO_REFRESH_KEY) === 'true'
  )
  const [historyCount, setHistoryCount] = useState(() => {
    try {
      const raw = localStorage.getItem(SEARCH_HISTORY_KEY)
      return raw ? (JSON.parse(raw) as unknown[]).length : 0
    } catch {
      return 0
    }
  })
  const [clearedHint, setClearedHint] = useState<string | null>(null)

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
              <p className="text-sm text-muted-foreground">
                {fromPrompt ? '登录状态与界面偏好' : '看板、资讯与界面偏好'}
              </p>
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

          {!fromPrompt && (
            <GlowCard>
              <div className="space-y-4 p-5">
                <div className="flex items-center gap-2">
                  <LayoutDashboard className="h-4 w-4 text-primary" />
                  <h2 className="text-sm font-semibold">看板偏好</h2>
                </div>
                <label className="block space-y-1.5 text-sm">
                  <span className="text-muted-foreground">热门题材展示数量</span>
                  <select
                    value={limit}
                    onChange={(e) => setLimit(Number(e.target.value))}
                    className="w-full rounded-xl border border-border bg-background px-3 py-2"
                  >
                    {LIMIT_OPTIONS.map((value) => (
                      <option key={value} value={value}>
                        Top {value}
                      </option>
                    ))}
                  </select>
                </label>
                <ToggleRow
                  label="显示图表"
                  checked={showCharts}
                  onChange={toggleCharts}
                />
                <ToggleRow
                  label="显示快速统计"
                  checked={showStats}
                  onChange={toggleStats}
                />
              </div>
            </GlowCard>
          )}

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

          {!fromPrompt && (
            <GlowCard>
              <div className="space-y-4 p-5">
                <div className="flex items-center gap-2">
                  <Newspaper className="h-4 w-4 text-primary" />
                  <h2 className="text-sm font-semibold">资讯偏好</h2>
                </div>
                <ToggleRow
                  label="进入看板时默认开启资讯自动刷新"
                  checked={newsAutoRefresh}
                  onChange={() => {
                    const next = !newsAutoRefresh
                    setNewsAutoRefresh(next)
                    localStorage.setItem(NEWS_AUTO_REFRESH_KEY, String(next))
                  }}
                />
              </div>
            </GlowCard>
          )}

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
              {!fromPrompt && (
                <>
                  <button
                    type="button"
                    onClick={() => {
                      localStorage.removeItem(SEARCH_HISTORY_KEY)
                      setHistoryCount(0)
                      setClearedHint('已清除题材搜索历史')
                    }}
                    className="inline-flex items-center gap-2 rounded-xl border border-border px-3 py-2 text-sm hover:bg-accent"
                  >
                    <Eraser className="h-4 w-4" />
                    清除搜索历史{historyCount > 0 ? `（${historyCount}）` : ''}
                  </button>
                  {clearedHint && (
                    <p className="text-xs text-primary">{clearedHint}</p>
                  )}
                </>
              )}
            </div>
          </GlowCard>
        </div>
      </main>
    </div>
  )
}

function ToggleRow({
  label,
  checked,
  onChange,
}: {
  label: string
  checked: boolean
  onChange: () => void
}) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-xl border border-border/70 px-3 py-2.5 text-sm">
      <span>{label}</span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        onClick={onChange}
        className={cn(
          'relative h-5 w-9 shrink-0 rounded-full transition-colors',
          checked ? 'bg-sky-500' : 'bg-muted'
        )}
      >
        <span
          className={cn(
            'absolute left-0 top-0.5 h-4 w-4 rounded-full bg-background shadow transition-transform',
            checked ? 'translate-x-4' : 'translate-x-0.5'
          )}
        />
      </button>
    </div>
  )
}
