import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Database, Loader2, PlugZap } from 'lucide-react'
import { useEffect, useState } from 'react'
import { AppCardNav } from '@/components/AppCardNav'
import { SettingsSubnav } from '@/components/SettingsSubnav'
import { GlowCard } from '@/components/GlowCard'
import {
  fetchTushareSettings,
  testTushareConnection,
  updateTushareSettings,
} from '@/api/integrations'
import { cn } from '@/lib/utils'

/** 数据源设置：Tushare 启用与 Token */
export function IntegrationsSettings() {
  const queryClient = useQueryClient()
  const settingsQuery = useQuery({
    queryKey: ['integrations', 'tushare'],
    queryFn: fetchTushareSettings,
  })

  const [enabled, setEnabled] = useState(false)
  const [token, setToken] = useState('')
  const [notice, setNotice] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(
    null
  )

  useEffect(() => {
    if (settingsQuery.data) {
      setEnabled(settingsQuery.data.enabled)
    }
  }, [settingsQuery.data])

  const saveMutation = useMutation({
    mutationFn: updateTushareSettings,
    onSuccess: (data) => {
      queryClient.setQueryData(['integrations', 'tushare'], data)
      setToken('')
      setNotice({ type: 'success', text: '已保存 Tushare 配置' })
    },
    onError: (err: Error) => {
      setNotice({ type: 'error', text: err.message || '保存失败' })
    },
  })

  const testMutation = useMutation({
    mutationFn: () => testTushareConnection(token.trim() || undefined),
    onSuccess: (data) => {
      setNotice({
        type: data.success ? 'success' : 'error',
        text: data.message,
      })
    },
    onError: (err: Error) => {
      setNotice({ type: 'error', text: err.message || '测试失败' })
    },
  })

  const busy = saveMutation.isPending || testMutation.isPending
  const hasToken = settingsQuery.data?.has_token ?? false

  return (
    <div className="min-h-screen">
      <AppCardNav />
      <main className="mx-auto w-full max-w-none space-y-5 px-3 py-6 sm:px-4 lg:px-5 xl:px-6">
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <Database className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <h1 className="text-xl font-semibold tracking-tight">数据源</h1>
              <p className="text-sm text-muted-foreground">
                配置行情与题材采集用的第三方数据源（高级参数仍可在服务端环境变量调整）
              </p>
            </div>
          </div>
          <SettingsSubnav />
        </div>

        <GlowCard>
          <div className="space-y-5 p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-sm font-semibold">Tushare Pro</h2>
                <p className="mt-1 text-xs text-muted-foreground">
                  启用后参与看板全量竞速题材兜底。Token 加密存储，接口不会回传明文。
                </p>
              </div>
              <span
                className={cn(
                  'shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium',
                  hasToken
                    ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
                    : 'bg-muted text-muted-foreground'
                )}
              >
                {hasToken ? '已配置 Token' : '未配置 Token'}
              </span>
            </div>

            {settingsQuery.isLoading ? (
              <p className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                加载配置…
              </p>
            ) : settingsQuery.isError ? (
              <p className="text-sm text-destructive">加载 Tushare 配置失败</p>
            ) : (
              <>
                <div className="flex items-center justify-between gap-3 rounded-xl border border-border/70 px-3 py-2.5 text-sm">
                  <span>启用 Tushare</span>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={enabled}
                    aria-label="启用 Tushare"
                    onClick={() => setEnabled((v) => !v)}
                    className={cn(
                      'relative h-5 w-9 shrink-0 rounded-full transition-colors',
                      enabled ? 'bg-sky-500' : 'bg-muted'
                    )}
                  >
                    <span
                      className={cn(
                        'absolute left-0 top-0.5 h-4 w-4 rounded-full bg-background shadow transition-transform',
                        enabled ? 'translate-x-4' : 'translate-x-0.5'
                      )}
                    />
                  </button>
                </div>

                <label className="block space-y-1.5 text-sm">
                  <span className="text-muted-foreground">
                    Token{hasToken ? '（留空则保留已有）' : ''}
                  </span>
                  <input
                    type="password"
                    autoComplete="off"
                    value={token}
                    onChange={(e) => setToken(e.target.value)}
                    placeholder={hasToken ? '••••••••（已保存，可输入新 Token 覆盖）' : '粘贴 Tushare Pro Token'}
                    className="w-full rounded-xl border border-border bg-background px-3 py-2"
                  />
                </label>

                {notice && (
                  <p
                    className={cn(
                      'rounded-xl border px-3 py-2 text-sm',
                      notice.type === 'success' &&
                        'border-primary/30 bg-primary/10 text-primary',
                      notice.type === 'error' &&
                        'border-destructive/30 bg-destructive/10 text-destructive',
                      notice.type === 'info' && 'border-border bg-muted/60 text-foreground'
                    )}
                  >
                    {notice.text}
                  </p>
                )}

                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() =>
                      saveMutation.mutate({
                        enabled,
                        token: token.trim() ? token.trim() : '',
                      })
                    }
                    className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground disabled:opacity-50"
                  >
                    {saveMutation.isPending && (
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                    )}
                    保存配置
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => testMutation.mutate()}
                    className="inline-flex items-center gap-2 rounded-xl border border-border bg-background px-4 py-2.5 text-sm hover:bg-accent disabled:opacity-50"
                  >
                    {testMutation.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                    ) : (
                      <PlugZap className="h-4 w-4" aria-hidden="true" />
                    )}
                    测试连接
                  </button>
                </div>
              </>
            )}
          </div>
        </GlowCard>
      </main>
    </div>
  )
}
