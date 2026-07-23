import { useState } from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'

import { login } from '@/api/auth'
import { fetchCurrentUser } from '@/api/auth'
import { GlowCard } from '@/components/GlowCard'
import { useAuthStore } from '@/stores/auth'

function errorMessage(error: unknown): string {
  const value = error as {
    response?: { data?: { detail?: string; message?: string } }
    message?: string
  }
  return value.response?.data?.detail || value.response?.data?.message || value.message || '登录失败'
}

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const setAuth = useAuthStore((state) => state.setAuth)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const fromQuery = searchParams.get('from')
  const from =
    (location.state as { from?: string } | null)?.from ||
    (fromQuery?.startsWith('/') ? fromQuery : null) ||
    '/settings/models'

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      const tokenResponse = await login({ username, password })
      useAuthStore.setState({ token: tokenResponse.access_token })
      const user = await fetchCurrentUser()
      setAuth(tokenResponse.access_token, user)
      navigate(from, { replace: true })
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-md items-center px-4">
      <GlowCard className="w-full p-6">
        <h1 className="text-2xl font-semibold">登录</h1>
        <p className="mt-2 text-sm text-muted-foreground">登录后可保存你的模型配置</p>
        <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
          <label className="block space-y-1">
            <span className="text-sm">用户名</span>
            <input
              className="w-full rounded-lg border border-border bg-background px-3 py-2"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              autoComplete="username"
              required
            />
          </label>
          <label className="block space-y-1">
            <span className="text-sm">密码</span>
            <input
              type="password"
              className="w-full rounded-lg border border-border bg-background px-3 py-2"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-primary px-4 py-2 text-primary-foreground hover:opacity-90 disabled:opacity-60"
          >
            {loading ? '登录中...' : '登录'}
          </button>
        </form>
        <p className="mt-4 text-sm text-muted-foreground">
          还没有账号？{' '}
          <Link to="/register" className="text-primary hover:underline">
            立即注册
          </Link>
        </p>
      </GlowCard>
    </div>
  )
}
