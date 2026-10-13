import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  BookOpen,
  CalendarDays,
  LayoutDashboard,
  MessageSquare,
  Scale,
  StickyNote,
} from 'lucide-react'

import { useToastContext } from '@/App'
import {
  fetchOsDashboard,
  unpinFromOsDashboard,
  type DashboardSourceType,
} from '@/features/personal-os/api/dashboard'
import { PinToDashboardButton } from '@/features/personal-os/components/PinToDashboardButton'
import { cn } from '@/lib/utils'

const panel = 'rounded-xl border border-border bg-card p-3 sm:p-4'
const btnGhost =
  'inline-flex h-9 min-h-9 items-center justify-center rounded-md border border-input px-2.5 text-xs hover:bg-accent active:bg-accent sm:h-8'

const TYPE_LABEL: Record<DashboardSourceType, string> = {
  chat_session: '对话',
  note: '记忆',
  journal: '日志',
  report: '日报',
  decision: '决策',
}

const READINESS_LABEL = {
  empty: '空盘 · 先建档案与第一条日志',
  warmup: '热身期 · 先攒数据再开重大决策',
  ready: '数据就绪 · 可日报复盘与多模型开图',
} as const

export function OsDashboardPage() {
  const toast = useToastContext()
  const queryClient = useQueryClient()
  const { data, isFetching, isError, error } = useQuery({
    queryKey: ['os-dashboard'],
    queryFn: fetchOsDashboard,
  })

  const unpin = useMutation({
    mutationFn: (id: number) => unpinFromOsDashboard(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['os-dashboard'] })
      toast.success('已从仪表盘移除')
    },
    onError: (e: Error) => toast.error(e.message),
  })

  if (isError) {
    return (
      <div className="p-4 text-sm text-destructive" data-testid="os-dashboard-page">
        {(error as Error).message || '仪表盘加载失败'}
      </div>
    )
  }

  if (!data) {
    return (
      <div
        className="flex h-full items-center justify-center text-sm text-muted-foreground"
        data-testid="os-dashboard-page"
      >
        {isFetching ? '加载仪表盘…' : '暂无数据'}
      </div>
    )
  }

  const modules = [
    {
      key: 'chat',
      label: '对话',
      count: data.counts.chat_sessions,
      to: '/os/chat',
      icon: MessageSquare,
      flag: data.module_flags.chat !== false,
    },
    {
      key: 'memory',
      label: '记忆',
      count: data.counts.notes,
      to: '/os/memory',
      icon: StickyNote,
      flag: data.module_flags.memory !== false,
    },
    {
      key: 'journal',
      label: '日志',
      count: data.counts.journal,
      to: '/os/journal',
      icon: CalendarDays,
      flag: data.module_flags.journal !== false,
    },
    {
      key: 'reports',
      label: '日报',
      count: data.counts.reports,
      to: '/os/reports',
      icon: BookOpen,
      flag: data.module_flags.reports !== false,
    },
    {
      key: 'decisions',
      label: '决策',
      count: data.counts.decisions,
      to: '/os/decisions',
      icon: Scale,
      flag: data.module_flags.decisions !== false,
    },
  ]

  return (
    <div
      className="mx-auto grid h-full max-w-6xl gap-2 overflow-y-auto overscroll-contain pb-2 sm:gap-3"
      data-testid="os-dashboard-page"
    >
      <section className={cn(panel, 'space-y-3')}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <LayoutDashboard className="h-5 w-5 text-primary" aria-hidden />
              <h2 className="text-base font-semibold">
                {data.display_name ? `${data.display_name} 的个人 OS` : '个人 AI OS 仪表盘'}
              </h2>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              {READINESS_LABEL[data.data_readiness]}
              {data.has_report_tuning || data.has_decision_tuning
                ? ' · 已有调参反馈写入'
                : ''}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link to="/os/journal" className={btnGhost}>
              记日志
            </Link>
            <Link to="/os/reports" className={btnGhost}>
              出日报
            </Link>
            <Link to="/os/decisions" className={btnGhost}>
              开图决策
            </Link>
            <Link to="/os/settings" className={btnGhost}>
              导出 / 设置
            </Link>
          </div>
        </div>
        {data.goals ? (
          <p className="whitespace-pre-wrap text-sm text-muted-foreground">{data.goals}</p>
        ) : (
          <p className="text-sm text-muted-foreground">
            尚未写目标。先在{' '}
            <Link to="/os/memory" className="text-primary underline">
              记忆
            </Link>{' '}
            填人设与底线，系统才有锚点。
          </p>
        )}
        {Object.keys(data.health_baseline || {}).length > 0 ? (
          <pre className="overflow-x-auto rounded-md bg-muted/50 p-2 text-xs text-muted-foreground">
            {JSON.stringify(data.health_baseline, null, 2)}
          </pre>
        ) : null}
      </section>

      <section className="grid grid-cols-2 gap-2 sm:gap-3 md:grid-cols-3 lg:grid-cols-5">
        {modules.map((m) => (
          <Link
            key={m.key}
            to={m.to}
            className={cn(
              panel,
              'min-h-[4.5rem] transition-colors active:border-primary/40 hover:border-primary/40',
              !m.flag && 'opacity-50'
            )}
          >
            <div className="flex items-center gap-2 text-muted-foreground">
              <m.icon className="h-4 w-4" aria-hidden />
              <span className="text-xs">{m.label}</span>
            </div>
            <p className="mt-1 text-xl font-semibold tabular-nums sm:mt-2 sm:text-2xl">
              {m.count}
            </p>
            {!m.flag ? (
              <p className="mt-1 text-[11px] text-muted-foreground">模块已关闭</p>
            ) : null}
          </Link>
        ))}
      </section>

      <section className={cn(panel, 'space-y-2')}>
        <h3 className="text-sm font-semibold">身体 / 日程仪表（日志分布）</h3>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {(
            [
              ['diet', '饮食'],
              ['training', '训练'],
              ['sleep', '睡眠'],
              ['schedule', '日程'],
            ] as const
          ).map(([key, label]) => (
            <div key={key} className="rounded-lg border border-border px-3 py-2">
              <p className="text-xs text-muted-foreground">{label}</p>
              <p className="text-lg font-semibold tabular-nums">
                {data.journal_by_kind[key]}
              </p>
            </div>
          ))}
        </div>
        <p className="text-[11px] text-muted-foreground">
          可量化指标优先于感觉成功；此处不是医疗诊断。
        </p>
      </section>

      <div className="grid gap-2 sm:gap-3 lg:grid-cols-2">
        <section className={cn(panel, 'space-y-3')}>
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold">钉选看板</h3>
            <span className="text-xs text-muted-foreground">{data.pins.length} 项</span>
          </div>
          {data.pins.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              在对话 / 记忆 / 日志 / 日报 / 决策里点「钉到仪表盘」，重要条目会出现在这里。
            </p>
          ) : (
            <ul className="space-y-2">
              {data.pins.map((pin) => (
                <li
                  key={pin.id}
                  className="flex items-start justify-between gap-2 rounded-lg border border-border p-3"
                >
                  <div className="min-w-0">
                    <p className="text-[11px] text-muted-foreground">
                      {TYPE_LABEL[pin.source_type] ?? pin.source_type}
                    </p>
                    <Link
                      to={pin.href}
                      className="block truncate text-sm font-medium hover:underline"
                    >
                      {pin.title}
                    </Link>
                    {pin.snippet ? (
                      <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                        {pin.snippet}
                      </p>
                    ) : null}
                  </div>
                  <button
                    type="button"
                    className={btnGhost}
                    disabled={unpin.isPending}
                    onClick={() => unpin.mutate(pin.id)}
                  >
                    移除
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className={cn(panel, 'space-y-3')}>
          <h3 className="text-sm font-semibold">如何优化你的个人 AI OS</h3>
          <ul className="space-y-2">
            {data.optimize_tips.map((tip) => (
              <li key={tip.id} className="rounded-lg border border-border p-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-medium">{tip.title}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{tip.body}</p>
                  </div>
                  <span
                    className={cn(
                      'shrink-0 rounded px-1.5 py-0.5 text-[10px]',
                      tip.priority === 'high' && 'bg-destructive/15 text-destructive',
                      tip.priority === 'medium' && 'bg-primary/10 text-primary',
                      tip.priority === 'low' && 'bg-muted text-muted-foreground'
                    )}
                  >
                    {tip.priority === 'high'
                      ? '优先'
                      : tip.priority === 'medium'
                        ? '建议'
                        : '原则'}
                  </span>
                </div>
                {tip.action_href && tip.action_label ? (
                  <Link
                    to={tip.action_href}
                    className="mt-2 inline-flex text-xs text-primary hover:underline"
                  >
                    {tip.action_label} →
                  </Link>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      </div>

      <section className={cn(panel, 'space-y-3')}>
        <h3 className="text-sm font-semibold">最近动态</h3>
        {data.recent.length === 0 ? (
          <p className="text-sm text-muted-foreground">还没有内容。从记一条日志或开一场对话开始。</p>
        ) : (
          <ul className="divide-y divide-border">
            {data.recent.map((item) => (
              <li
                key={`${item.source_type}-${item.id}`}
                className="flex items-center justify-between gap-3 py-2.5"
              >
                <div className="min-w-0">
                  <p className="text-[11px] text-muted-foreground">
                    {TYPE_LABEL[item.source_type]}
                    {item.at
                      ? ` · ${new Date(item.at).toLocaleString()}`
                      : ''}
                  </p>
                  <Link to={item.href} className="truncate text-sm hover:underline">
                    {item.title}
                  </Link>
                </div>
                <PinToDashboardButton
                  sourceType={item.source_type}
                  sourceId={item.id}
                  pinned={item.pinned}
                  compact
                />
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
