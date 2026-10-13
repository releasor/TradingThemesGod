import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useToastContext } from '@/App'
import {
  chooseOsDecision,
  createOsDecision,
  feedbackOsDecisionOption,
  listOsDecisionTemplates,
  listOsDecisions,
  runOsDecision,
  type OsDecisionThread,
} from '@/features/personal-os/api/decisions'
import { listOsJournal } from '@/features/personal-os/api/journal'
import { fetchOsProfile } from '@/features/personal-os/api/profile'
import { PinToDashboardButton } from '@/features/personal-os/components/PinToDashboardButton'
import { useOsPinnedSet } from '@/features/personal-os/hooks/useOsPinnedSet'
import { cn } from '@/lib/utils'

const panel = 'rounded-xl border border-border bg-card p-4'
const field =
  'w-full rounded-md border border-input bg-background px-3 py-2 text-base sm:text-sm'
const btn =
  'inline-flex h-9 items-center justify-center rounded-md px-3 text-sm transition-colors'
const btnPrimary = cn(btn, 'bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50')
const btnGhost = cn(btn, 'border border-input hover:bg-accent')

const TIER_LABEL: Record<string, string> = {
  upper: '上策',
  mid: '中策',
  lower: '下策',
}

const JOURNAL_WARMUP = 7

export function OsDecisionsPage() {
  const toast = useToastContext()
  const queryClient = useQueryClient()
  const { isPinned } = useOsPinnedSet()
  const [question, setQuestion] = useState('')
  const [constraints, setConstraints] = useState('')
  const [activeId, setActiveId] = useState<number | null>(null)
  const [outcome, setOutcome] = useState('')
  const [feedbackNote, setFeedbackNote] = useState('')
  const [feedbackScore, setFeedbackScore] = useState(8)

  const { data: profile } = useQuery({
    queryKey: ['os-profile'],
    queryFn: fetchOsProfile,
  })

  const { data: threads = [], isFetching } = useQuery({
    queryKey: ['os-decisions'],
    queryFn: listOsDecisions,
  })

  const { data: templates = [] } = useQuery({
    queryKey: ['os-decision-templates'],
    queryFn: listOsDecisionTemplates,
  })

  const { data: journalEntries = [] } = useQuery({
    queryKey: ['os-journal', 'warmup'],
    queryFn: () => listOsJournal({ limit: 50 }),
  })

  const active: OsDecisionThread | null =
    threads.find((t) => t.id === activeId) ?? threads[0] ?? null
  const thinData = journalEntries.length < JOURNAL_WARMUP

  const create = useMutation({
    mutationFn: () =>
      createOsDecision({
        question: question.trim(),
        constraints: constraints.trim() || undefined,
      }),
    onSuccess: async (t) => {
      setQuestion('')
      setConstraints('')
      setActiveId(t.id)
      await queryClient.invalidateQueries({ queryKey: ['os-decisions'] })
      toast.success('决策已创建')
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const run = useMutation({
    mutationFn: () =>
      runOsDecision(active!.id, {
        provider_ids: profile?.model_prefs.compare_provider_ids,
      }),
    onSuccess: async (t) => {
      setActiveId(t.id)
      await queryClient.invalidateQueries({ queryKey: ['os-decisions'] })
      toast.success('多模型分析完成')
    },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <div
      className="grid h-full min-h-0 gap-2 overflow-y-auto overscroll-contain sm:gap-3 lg:grid-cols-[18rem_minmax(0,1fr)] lg:overflow-hidden"
      data-testid="os-decisions-page"
    >
      <section className={cn(panel, 'flex min-h-0 flex-col gap-3 p-3 sm:p-4')}>
        <h2 className="text-sm font-semibold">新决策</h2>
        {thinData ? (
          <div className="rounded-md border border-dashed border-border bg-muted/40 p-2 text-xs text-muted-foreground">
            日志还不多（&lt; {JOURNAL_WARMUP} 条）。建议先{' '}
            <Link to="/os/journal" className="text-primary underline">
              攒生活数据
            </Link>
            ，再对大事跑多模型；开图模板可先填约束与样本。
          </div>
        ) : null}
        {templates.length > 0 ? (
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">开图模板（填入后可改）</p>
            <div className="flex flex-wrap gap-1.5">
              {templates.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  className={cn(btnGhost, 'h-8 text-xs')}
                  title={t.hint}
                  onClick={() => {
                    setQuestion(t.question)
                    setConstraints(t.constraints)
                  }}
                >
                  {t.title}
                </button>
              ))}
            </div>
          </div>
        ) : null}
        <textarea
          className={cn(field, 'min-h-[5rem] resize-y')}
          placeholder="要决策的问题"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <textarea
          className={cn(field, 'min-h-[5rem] resize-y')}
          placeholder="约束 / 开图清单（资源、底线、已看样本、版本）"
          value={constraints}
          onChange={(e) => setConstraints(e.target.value)}
        />
        <button
          type="button"
          className={btnPrimary}
          disabled={!question.trim() || create.isPending}
          onClick={() => create.mutate()}
        >
          创建
        </button>
        <p className="text-[11px] text-muted-foreground">
          AI 只出上中下草案，拍板与后果由你负责；不构成投资或人生建议。
        </p>
        <ul className="min-h-0 flex-1 space-y-1 overflow-y-auto border-t border-border pt-3">
          {isFetching ? (
            <li className="text-sm text-muted-foreground">加载中…</li>
          ) : (
            threads.map((t) => (
              <li key={t.id}>
                <button
                  type="button"
                  className={cn(
                    'w-full truncate rounded-md px-2 py-1.5 text-left text-sm',
                    active?.id === t.id ? 'bg-primary/15' : 'hover:bg-accent'
                  )}
                  onClick={() => setActiveId(t.id)}
                >
                  {t.question}
                </button>
              </li>
            ))
          )}
        </ul>
      </section>

      <section
        className={cn(panel, 'flex min-h-0 flex-col gap-3 overflow-y-auto overscroll-contain p-3 sm:p-4')}
      >
        {!active ? (
          <p className="text-sm text-muted-foreground">
            用开图模板填清资源与样本后创建决策，再按设置中的对比模型给出上中下策。
          </p>
        ) : (
          <>
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <h2 className="text-base font-semibold">{active.question}</h2>
                {active.constraints ? (
                  <p className="mt-1 whitespace-pre-wrap text-sm text-muted-foreground">
                    约束：{active.constraints}
                  </p>
                ) : null}
                <p className="mt-1 text-xs text-muted-foreground">状态：{active.status}</p>
              </div>
              <PinToDashboardButton
                sourceType="decision"
                sourceId={active.id}
                pinned={isPinned('decision', active.id)}
              />
            </div>
            <button
              type="button"
              className={btnPrimary}
              disabled={run.isPending}
              onClick={() => run.mutate()}
            >
              {run.isPending ? '分析中…' : '运行多模型分析'}
            </button>
            {active.latest_run ? (
              <div className="space-y-3">
                {active.latest_run.summary ? (
                  <p className="whitespace-pre-wrap text-sm">{active.latest_run.summary}</p>
                ) : null}
                <div className="grid gap-2 sm:gap-3 md:grid-cols-3">
                  {active.latest_run.options.map((opt) => (
                    <div
                      key={opt.id}
                      className={cn(
                        'rounded-lg border p-3',
                        opt.selected ? 'border-primary bg-primary/10' : 'border-border'
                      )}
                    >
                      <h3 className="text-sm font-semibold">
                        {TIER_LABEL[opt.tier] ?? opt.tier} · {opt.title}
                      </h3>
                      <p className="mt-2 whitespace-pre-wrap text-xs">{opt.content}</p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        <button
                          type="button"
                          className={btnGhost}
                          onClick={async () => {
                            await chooseOsDecision(active.id, {
                              option_id: opt.id,
                              outcome_note: outcome.trim() || undefined,
                            })
                            await queryClient.invalidateQueries({
                              queryKey: ['os-decisions'],
                            })
                            toast.success('已选择该策（仍由你执行与复盘）')
                          }}
                        >
                          选这个
                        </button>
                        <button
                          type="button"
                          className={btnGhost}
                          onClick={async () => {
                            await feedbackOsDecisionOption(opt.id, {
                              score: feedbackScore,
                              note:
                                feedbackNote.trim() ||
                                `事后复盘：评分 ${feedbackScore}`,
                              apply_to_prompt: true,
                            })
                            await queryClient.invalidateQueries({
                              queryKey: ['os-decisions'],
                            })
                            await queryClient.invalidateQueries({
                              queryKey: ['os-profile'],
                            })
                            setFeedbackNote('')
                            toast.success('反馈已写入决策调参')
                          }}
                        >
                          写入调参
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <label className="block space-y-1 text-sm">
                    <span className="text-muted-foreground">选择备注</span>
                    <textarea
                      className={cn(field, 'min-h-[3rem] resize-y text-base sm:text-sm')}
                      placeholder="为什么选这一策"
                      value={outcome}
                      onChange={(e) => setOutcome(e.target.value)}
                    />
                  </label>
                  <label className="block space-y-1 text-sm">
                    <span className="text-muted-foreground">
                      事后反馈（写入调参 · 评分 {feedbackScore}）
                    </span>
                    <input
                      type="range"
                      min={0}
                      max={10}
                      step={1}
                      className="w-full"
                      value={feedbackScore}
                      onChange={(e) => setFeedbackScore(Number(e.target.value))}
                    />
                    <textarea
                      className={cn(field, 'min-h-[3rem] resize-y text-base sm:text-sm')}
                      placeholder="执行结果如何？下次希望模型怎么调"
                      value={feedbackNote}
                      onChange={(e) => setFeedbackNote(e.target.value)}
                    />
                  </label>
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">尚未运行分析</p>
            )}
          </>
        )}
      </section>
    </div>
  )
}
