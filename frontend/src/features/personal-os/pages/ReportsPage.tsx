import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useToastContext } from '@/App'
import {
  feedbackOsReport,
  generateOsReportStream,
  listOsReports,
} from '@/features/personal-os/api/reports'
import { PinToDashboardButton } from '@/features/personal-os/components/PinToDashboardButton'
import { useOsPinnedSet } from '@/features/personal-os/hooks/useOsPinnedSet'
import { useOsModelSelection } from '@/features/personal-os/stores/modelSelection'
import { cn } from '@/lib/utils'

const panel = 'rounded-xl border border-border bg-card p-3 sm:p-4'
const field =
  'w-full rounded-md border border-input bg-background px-3 py-2 text-base sm:text-sm'
const btnPrimary =
  'inline-flex h-9 items-center justify-center rounded-md bg-primary px-3 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50'

export function OsReportsPage() {
  const toast = useToastContext()
  const queryClient = useQueryClient()
  const providerId = useOsModelSelection((s) => s.providerId)
  const { isPinned } = useOsPinnedSet()
  const [generating, setGenerating] = useState(false)
  const [streamText, setStreamText] = useState('')
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [score, setScore] = useState(4)
  const [feedbackNote, setFeedbackNote] = useState('')

  const { data: reports = [], isFetching } = useQuery({
    queryKey: ['os-reports'],
    queryFn: listOsReports,
  })

  const selected = reports.find((r) => r.id === selectedId) ?? reports[0] ?? null

  async function generate() {
    setGenerating(true)
    setStreamText('')
    try {
      const result = await generateOsReportStream(
        {
          report_date: new Date().toISOString().slice(0, 10),
          provider_id: providerId,
        },
        (event) => {
          if (event.type === 'delta') setStreamText((t) => t + event.text)
          if (event.type === 'done') setStreamText(event.result)
        }
      )
      await queryClient.invalidateQueries({ queryKey: ['os-reports'] })
      if (result.report_id) setSelectedId(result.report_id)
      toast.success('日报已生成')
    } catch (e) {
      toast.error((e as Error).message || '生成失败')
    } finally {
      setGenerating(false)
      setStreamText('')
    }
  }

  const feedback = useMutation({
    mutationFn: () =>
      feedbackOsReport(selected!.id, {
        score,
        note: feedbackNote.trim() || undefined,
        apply_to_prompt: true,
      }),
    onSuccess: async () => {
      setFeedbackNote('')
      await queryClient.invalidateQueries({ queryKey: ['os-reports'] })
      await queryClient.invalidateQueries({ queryKey: ['os-profile'] })
      toast.success('反馈已写入，将影响后续日报')
    },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <div
      className="grid h-full min-h-0 gap-2 overflow-y-auto overscroll-contain sm:gap-3 lg:grid-cols-[16rem_minmax(0,1fr)] lg:overflow-hidden"
      data-testid="os-reports-page"
    >
      <section className={cn(panel, 'flex min-h-0 flex-col gap-3')}>
        <p className="text-xs text-muted-foreground">
          基于当日日志生成复盘；反馈会写入调参附录。非医嘱，仅供个人参考。
        </p>
        <button
          type="button"
          className={btnPrimary}
          disabled={generating}
          onClick={() => void generate()}
        >
          {generating ? '生成中…' : '生成今日日报'}
        </button>
        <ul className="min-h-0 flex-1 space-y-1 overflow-y-auto">
          {isFetching ? (
            <li className="text-sm text-muted-foreground">加载中…</li>
          ) : reports.length === 0 ? (
            <li className="text-sm text-muted-foreground">
              还没有日报。先去记几条日志，再生成会更有用。
            </li>
          ) : (
            reports.map((r) => (
              <li key={r.id}>
                <button
                  type="button"
                  className={cn(
                    'w-full rounded-md px-2 py-1.5 text-left text-sm',
                    (selected?.id ?? null) === r.id
                      ? 'bg-primary/15'
                      : 'hover:bg-accent'
                  )}
                  onClick={() => setSelectedId(r.id)}
                >
                  {r.report_date}
                  {r.feedback_score != null ? ` · ★${r.feedback_score}` : ''}
                </button>
              </li>
            ))
          )}
        </ul>
      </section>

      <section className={cn(panel, 'flex min-h-0 flex-col gap-3 lg:overflow-hidden')}>
        {streamText ? (
          <pre className="min-h-0 flex-1 overflow-y-auto whitespace-pre-wrap text-sm">
            {streamText}
          </pre>
        ) : selected ? (
          <>
            <div className="flex shrink-0 items-center justify-between gap-2">
              <h3 className="text-sm font-semibold">{selected.report_date}</h3>
              <PinToDashboardButton
                sourceType="report"
                sourceId={selected.id}
                pinned={isPinned('report', selected.id)}
              />
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto whitespace-pre-wrap text-sm">
              {selected.content}
            </div>
            <div className="shrink-0 space-y-2 border-t border-border pt-3">
              <h3 className="text-sm font-semibold">反馈调参</h3>
              <label className="block space-y-1 text-sm">
                <span className="text-muted-foreground">评分 1-5</span>
                <input
                  type="number"
                  min={1}
                  max={5}
                  className={field}
                  value={score}
                  onChange={(e) => setScore(Number(e.target.value) || 1)}
                />
              </label>
              <textarea
                className={cn(field, 'min-h-[4rem] resize-y')}
                placeholder="希望日报怎样改进？"
                value={feedbackNote}
                onChange={(e) => setFeedbackNote(e.target.value)}
              />
              <button
                type="button"
                className={btnPrimary}
                disabled={feedback.isPending}
                onClick={() => feedback.mutate()}
              >
                提交反馈
              </button>
            </div>
          </>
        ) : (
          <p className="text-sm text-muted-foreground">生成或选择一份日报</p>
        )}
      </section>
    </div>
  )
}
