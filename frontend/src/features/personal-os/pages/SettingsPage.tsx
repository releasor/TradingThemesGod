import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { fetchModelProviders } from '@/api/model-provider'
import { useToastContext } from '@/App'
import { downloadOsExport } from '@/features/personal-os/api/export'
import {
  fetchOsProfile,
  updateOsProfile,
  type MemoryPolicy,
  type ModelPrefs,
  type ModuleFlags,
} from '@/features/personal-os/api/profile'
import { cn } from '@/lib/utils'

const panel = 'rounded-xl border border-border bg-card p-3 space-y-3 sm:p-4'
const field =
  'w-full rounded-md border border-input bg-background px-3 py-2 text-base sm:text-sm'
const btnPrimary =
  'inline-flex h-9 items-center justify-center rounded-md bg-primary px-3 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50'
const btnGhost =
  'inline-flex h-9 items-center justify-center rounded-md border border-input px-3 text-sm hover:bg-accent disabled:opacity-50'

export function OsSettingsPage() {
  const toast = useToastContext()
  const queryClient = useQueryClient()
  const { data: profile } = useQuery({
    queryKey: ['os-profile'],
    queryFn: fetchOsProfile,
  })
  const { data: providers = [] } = useQuery({
    queryKey: ['model-providers'],
    queryFn: fetchModelProviders,
  })
  const enabled = providers.filter((p) => p.enabled)

  const [systemPrompt, setSystemPrompt] = useState('')
  const [memoryPolicy, setMemoryPolicy] = useState<MemoryPolicy>({
    inject_profile: true,
    note_top_k: 5,
    recent_turns: 20,
  })
  const [moduleFlags, setModuleFlags] = useState<ModuleFlags>({
    chat: true,
    memory: true,
    journal: true,
    reports: true,
    decisions: true,
  })
  const [modelPrefs, setModelPrefs] = useState<ModelPrefs>({
    default_provider_id: null,
    compare_provider_ids: [],
  })
  const [reportAppendix, setReportAppendix] = useState('')
  const [decisionAppendix, setDecisionAppendix] = useState('')
  const [hydrated, setHydrated] = useState(false)
  const [exporting, setExporting] = useState(false)

  useEffect(() => {
    if (!profile || hydrated) return
    setSystemPrompt(profile.system_prompt)
    setMemoryPolicy(profile.memory_policy)
    setModuleFlags(profile.module_flags)
    setModelPrefs(profile.model_prefs)
    setReportAppendix(profile.report_prompt_appendix ?? '')
    setDecisionAppendix(profile.decision_prompt_appendix ?? '')
    setHydrated(true)
  }, [profile, hydrated])

  const save = useMutation({
    mutationFn: () =>
      updateOsProfile({
        system_prompt: systemPrompt.trim(),
        memory_policy: memoryPolicy,
        module_flags: moduleFlags,
        model_prefs: modelPrefs,
        report_prompt_appendix: reportAppendix.trim() || null,
        decision_prompt_appendix: decisionAppendix.trim() || null,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['os-profile'] })
      toast.success('OS 设置已保存')
    },
    onError: (e: Error) => toast.error(e.message || '保存失败'),
  })

  async function onExport() {
    setExporting(true)
    try {
      await downloadOsExport()
      toast.success('已开始下载 Markdown ZIP')
    } catch (e) {
      toast.error((e as Error).message || '导出失败')
    } finally {
      setExporting(false)
    }
  }

  return (
    <div
      className="mx-auto grid h-full max-w-3xl gap-2 overflow-y-auto overscroll-contain pb-2 sm:gap-3"
      data-testid="os-settings-page"
    >
      <section className={panel}>
        <h2 className="text-sm font-semibold">数据资产导出</h2>
        <p className="text-xs text-muted-foreground">
          导出档案、笔记、日志、日报与决策为 Markdown ZIP。数据可迁移，不绑死单一模型。
        </p>
        <button
          type="button"
          className={btnGhost}
          disabled={exporting}
          onClick={() => void onExport()}
        >
          {exporting ? '打包中…' : '导出 Markdown ZIP'}
        </button>
      </section>

      <section className={panel}>
        <h2 className="text-sm font-semibold">人设 / 系统提示词</h2>
        <textarea
          className={cn(field, 'min-h-[8rem] resize-y')}
          value={systemPrompt}
          onChange={(e) => setSystemPrompt(e.target.value)}
        />
      </section>

      <section className={panel}>
        <h2 className="text-sm font-semibold">记忆策略</h2>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={memoryPolicy.inject_profile}
            onChange={(e) =>
              setMemoryPolicy((p) => ({ ...p, inject_profile: e.target.checked }))
            }
          />
          对话时注入档案摘要
        </label>
        <label className="block space-y-1 text-sm">
          <span className="text-muted-foreground">笔记检索条数</span>
          <input
            type="number"
            min={0}
            max={50}
            className={field}
            value={memoryPolicy.note_top_k}
            onChange={(e) =>
              setMemoryPolicy((p) => ({
                ...p,
                note_top_k: Number(e.target.value) || 0,
              }))
            }
          />
        </label>
        <label className="block space-y-1 text-sm">
          <span className="text-muted-foreground">近期对话轮数</span>
          <input
            type="number"
            min={1}
            max={100}
            className={field}
            value={memoryPolicy.recent_turns}
            onChange={(e) =>
              setMemoryPolicy((p) => ({
                ...p,
                recent_turns: Number(e.target.value) || 1,
              }))
            }
          />
        </label>
      </section>

      <section className={panel}>
        <h2 className="text-sm font-semibold">调参附录（反馈闭环）</h2>
        <p className="text-xs text-muted-foreground">
          日报与决策的事后反馈会写到这里，并注入后续生成。可手动编辑或清空。
        </p>
        <label className="block space-y-1 text-sm">
          <span className="text-muted-foreground">日报调参</span>
          <textarea
            className={cn(field, 'min-h-[5rem] resize-y')}
            value={reportAppendix}
            onChange={(e) => setReportAppendix(e.target.value)}
            placeholder="暂无日报反馈"
          />
        </label>
        <label className="block space-y-1 text-sm">
          <span className="text-muted-foreground">决策调参</span>
          <textarea
            className={cn(field, 'min-h-[5rem] resize-y')}
            value={decisionAppendix}
            onChange={(e) => setDecisionAppendix(e.target.value)}
            placeholder="暂无决策反馈"
          />
        </label>
      </section>

      <section className={panel}>
        <h2 className="text-sm font-semibold">模块开关</h2>
        {(
          [
            ['chat', '对话'],
            ['memory', '记忆'],
            ['journal', '日志'],
            ['reports', '日报'],
            ['decisions', '决策'],
          ] as const
        ).map(([key, label]) => (
          <label key={key} className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={moduleFlags[key]}
              onChange={(e) =>
                setModuleFlags((f) => ({ ...f, [key]: e.target.checked }))
              }
            />
            {label}
          </label>
        ))}
      </section>

      <section className={panel}>
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-sm font-semibold">模型偏好</h2>
          <Link to="/settings/models?from=os" className="text-xs text-primary hover:underline">
            配置 API Key
          </Link>
        </div>
        <p className="text-xs text-muted-foreground">
          系统先跑起来即可：可用免费或按次计费模型起步，不必绑定高价订阅。对比名单建议勾选 2–3
          个，大事再「开图」分析。
        </p>
        <label className="block space-y-1 text-sm">
          <span className="text-muted-foreground">默认模型</span>
          <select
            className={field}
            value={modelPrefs.default_provider_id ?? ''}
            onChange={(e) =>
              setModelPrefs((p) => ({
                ...p,
                default_provider_id: e.target.value ? Number(e.target.value) : null,
              }))
            }
          >
            <option value="">使用全局默认</option>
            {enabled.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.model})
              </option>
            ))}
          </select>
        </label>
        <fieldset className="space-y-1">
          <legend className="text-sm text-muted-foreground">多模型对比名单</legend>
          {enabled.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              请先在模型设置中启用至少一个模型（免费/按次亦可）
            </p>
          ) : (
            enabled.map((p) => {
              const checked = modelPrefs.compare_provider_ids.includes(p.id)
              return (
                <label key={p.id} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={(e) => {
                      setModelPrefs((prev) => {
                        const set = new Set(prev.compare_provider_ids)
                        if (e.target.checked) set.add(p.id)
                        else set.delete(p.id)
                        return {
                          ...prev,
                          compare_provider_ids: Array.from(set),
                        }
                      })
                    }}
                  />
                  {p.name} ({p.model})
                </label>
              )
            })
          )}
        </fieldset>
      </section>

      <button
        type="button"
        className={btnPrimary}
        disabled={save.isPending || !systemPrompt.trim()}
        onClick={() => save.mutate()}
      >
        保存设置
      </button>
    </div>
  )
}
