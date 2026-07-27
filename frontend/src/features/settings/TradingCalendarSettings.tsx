import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CalendarDays, Loader2 } from 'lucide-react'
import { AppCardNav } from '@/components/AppCardNav'
import { SettingsSubnav } from '@/components/SettingsSubnav'
import { GlowCard } from '@/components/GlowCard'
import { fetchCalendarStatus, syncTradingCalendar } from '@/api/trading-calendar'
import { useAuthStore } from '@/stores/auth'
import { Link } from 'react-router-dom'

/** 交易日历设置：同步状态与一键强制刷新 */
export function TradingCalendarSettings() {
  const token = useAuthStore((s) => s.token)
  const queryClient = useQueryClient()

  const statusQuery = useQuery({
    queryKey: ['market', 'calendar', 'status'],
    queryFn: fetchCalendarStatus,
  })

  const syncMutation = useMutation({
    mutationFn: syncTradingCalendar,
    onSuccess: (data) => {
      queryClient.setQueryData(['market', 'calendar', 'status'], data)
    },
  })

  const status = syncMutation.data ?? statusQuery.data

  return (
    <div className="min-h-screen">
      <AppCardNav />
      <main className="mx-auto w-full max-w-none space-y-5 px-3 py-6 sm:px-4 lg:px-5 xl:px-6">
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <CalendarDays className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <h1 className="text-xl font-semibold tracking-tight">交易日历</h1>
              <p className="text-sm text-muted-foreground">
                从 AKShare 同步 A 股开市日，供复盘与短线解析使用
              </p>
            </div>
          </div>
          <SettingsSubnav />
        </div>

        <GlowCard>
          <div className="space-y-4 p-5">
            {statusQuery.isLoading ? (
              <p className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                加载日历状态…
              </p>
            ) : statusQuery.isError ? (
              <p className="text-sm text-destructive">日历状态加载失败</p>
            ) : status ? (
              <dl className="grid gap-2 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-muted-foreground">数据交易日</dt>
                  <dd className="font-medium tabular-nums">{status.data_trade_date}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">今日是否开市</dt>
                  <dd className="font-medium">{status.today_is_trade_day ? '是' : '否'}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">覆盖区间</dt>
                  <dd className="font-medium tabular-nums">
                    {status.min_date && status.max_date
                      ? `${status.min_date} → ${status.max_date}`
                      : '—'}
                  </dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">开市日条数</dt>
                  <dd className="font-medium tabular-nums">{status.row_count}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">最近同步</dt>
                  <dd className="font-medium">
                    {status.last_synced_at
                      ? new Date(status.last_synced_at).toLocaleString('zh-CN')
                      : '尚未同步'}
                  </dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">状态</dt>
                  <dd className="font-medium">
                    {status.degraded ? '降级（周末兜底）' : '正常'}
                  </dd>
                </div>
              </dl>
            ) : null}

            {status?.last_error ? (
              <p className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-900 dark:text-amber-100">
                最近同步错误：{status.last_error}
              </p>
            ) : null}

            {token ? (
              <button
                type="button"
                disabled={syncMutation.isPending}
                onClick={() => syncMutation.mutate()}
                className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground disabled:opacity-60"
              >
                {syncMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                ) : null}
                同步交易日历
              </button>
            ) : (
              <p className="text-sm text-muted-foreground">
                同步需要登录。请先到{' '}
                <Link to="/login" className="text-primary underline-offset-2 hover:underline">
                  登录
                </Link>
                。
              </p>
            )}

            {syncMutation.isError ? (
              <p className="text-sm text-destructive">同步失败，请稍后重试</p>
            ) : null}
            {syncMutation.isSuccess ? (
              <p className="text-sm text-muted-foreground">同步完成</p>
            ) : null}
          </div>
        </GlowCard>
      </main>
    </div>
  )
}
