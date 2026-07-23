import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Check, Loader2, Plus, Save, Settings, Trash2, Wifi } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { AuthNav } from '@/components/AuthNav'
import {
  deleteModelProvider,
  fetchModelProviders,
  fetchProviderModels,
  saveModelProvider,
  testModelProvider,
  type ModelProtocol,
  type ModelProvider,
  type ModelProviderInput,
} from '@/api/model-provider'

const emptyForm: ModelProviderInput = {
  name: '',
  protocol: 'openai_compatible',
  base_url: '',
  api_key: '',
  model: '',
  custom_headers: {},
  timeout_seconds: 120,
  temperature: 0.1,
  max_tokens: 8192,
  enabled: true,
  is_default: true,
}

function errorMessage(error: unknown): string {
  const value = error as {
    response?: { data?: { detail?: string; message?: string } }
    message?: string
  }
  return (
    value.response?.data?.detail || value.response?.data?.message || value.message || '操作失败'
  )
}

function textToHeaders(text: string): Record<string, string> {
  return Object.fromEntries(
    text
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const index = line.indexOf(':')
        if (index < 1) throw new Error(`请求头格式错误：${line}`)
        return [line.slice(0, index).trim(), line.slice(index + 1).trim()]
      })
  )
}

export function ModelSettings() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [editingId, setEditingId] = useState<number | undefined>()
  const [form, setForm] = useState<ModelProviderInput>(emptyForm)
  const [headerText, setHeaderText] = useState('')
  const [notice, setNotice] = useState('')
  const { data: providers = [], isLoading } = useQuery({
    queryKey: ['model-providers'],
    queryFn: fetchModelProviders,
  })

  useEffect(() => {
    if (!editingId && providers.length > 0) selectProvider(providers[0])
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [providers])

  const saveMutation = useMutation({
    mutationFn: () =>
      saveModelProvider({ ...form, custom_headers: textToHeaders(headerText) }, editingId),
    onSuccess: async (provider) => {
      setEditingId(provider.id)
      setNotice('配置已加密保存')
      await queryClient.invalidateQueries({ queryKey: ['model-providers'] })
    },
    onError: (error) => setNotice(errorMessage(error)),
  })

  const testMutation = useMutation({
    mutationFn: () => testModelProvider(editingId!),
    onSuccess: (message) => setNotice(`连接成功：${message}`),
    onError: (error) => setNotice(errorMessage(error)),
  })

  const modelsMutation = useMutation({
    mutationFn: () => fetchProviderModels(editingId!),
    onSuccess: (models) =>
      setNotice(models.length ? `可用模型：${models.join('、')}` : '服务未返回模型列表'),
    onError: (error) => setNotice(errorMessage(error)),
  })

  function selectProvider(provider: ModelProvider) {
    setEditingId(provider.id)
    setForm({
      name: provider.name,
      protocol: provider.protocol,
      base_url: provider.base_url,
      api_key: '',
      model: provider.model,
      custom_headers: {},
      timeout_seconds: provider.timeout_seconds,
      temperature: provider.temperature,
      max_tokens: provider.max_tokens,
      enabled: provider.enabled,
      is_default: provider.is_default,
    })
    setHeaderText('')
    setNotice('')
  }

  const set = <K extends keyof ModelProviderInput>(key: K, value: ModelProviderInput[K]) =>
    setForm((current) => ({ ...current, [key]: value }))

  return (
    <div className="min-h-screen">
      <header className="sticky top-3 z-20 mx-3 mt-3 rounded-xl border border-border/60 bg-background/80 shadow-lg shadow-black/5 backdrop-blur-md sm:mx-4 sm:mt-4">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-4 sm:px-6">
          <div className="flex items-center gap-3">
            <button
              aria-label="返回首页"
              onClick={() => navigate('/')}
              className="rounded-xl p-2 hover:bg-accent"
            >
              <ArrowLeft className="h-5 w-5" />
            </button>
            <Settings className="h-5 w-5 text-primary" />
            <div>
              <h1 className="text-xl font-semibold">模型设置</h1>
              <p className="text-sm text-muted-foreground">配置图谱分析使用的模型服务</p>
            </div>
          </div>
          <AuthNav />
        </div>
      </header>
      <main className="mx-auto grid max-w-6xl gap-6 px-4 py-6 sm:px-6 lg:grid-cols-[260px_1fr]">
        <aside className="border-b border-border pb-5 lg:border-b-0 lg:border-r lg:pr-5">
          <button
            onClick={() => {
              setEditingId(undefined)
              setForm(emptyForm)
              setHeaderText('')
              setNotice('')
            }}
            className="mb-3 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-3 py-2 text-sm font-medium text-primary-foreground"
          >
            <Plus className="h-4 w-4" />
            新增配置
          </button>
          <div className="space-y-2">
            {isLoading && <p className="text-sm text-muted-foreground">正在读取配置...</p>}
            {providers.map((provider) => (
              <button
                key={provider.id}
                onClick={() => selectProvider(provider)}
                className={`w-full rounded-xl border px-3 py-3 text-left ${editingId === provider.id ? 'border-primary bg-accent' : 'border-border'}`}
              >
                <span className="flex items-center justify-between gap-2 text-sm font-medium">
                  <span className="truncate">{provider.name}</span>
                  {provider.is_default && <Check className="h-4 w-4 text-primary" />}
                </span>
                <span className="mt-1 block truncate text-xs text-muted-foreground">
                  {provider.model}
                </span>
              </button>
            ))}
          </div>
        </aside>

        <form
          onSubmit={(event) => {
            event.preventDefault()
            setNotice('')
            saveMutation.mutate()
          }}
          className="min-w-0 space-y-5"
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="space-y-1.5 text-sm">
              配置名称
              <input
                required
                value={form.name}
                onChange={(e) => set('name', e.target.value)}
                className="w-full rounded-xl border border-input bg-background px-3 py-2"
              />
            </label>
            <label className="space-y-1.5 text-sm">
              协议
              <select
                value={form.protocol}
                onChange={(e) => set('protocol', e.target.value as ModelProtocol)}
                className="w-full rounded-xl border border-input bg-background px-3 py-2"
              >
                <option value="openai_compatible">OpenAI 兼容 / 中转端</option>
                <option value="anthropic">Anthropic</option>
                <option value="gemini">Gemini</option>
                <option value="ollama">Ollama</option>
              </select>
            </label>
          </div>
          <label className="block space-y-1.5 text-sm">
            API 地址
            <input
              required
              type="url"
              value={form.base_url}
              onChange={(e) => set('base_url', e.target.value)}
              placeholder="https://api.example.com/v1"
              className="w-full rounded-xl border border-input bg-background px-3 py-2"
            />
          </label>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="space-y-1.5 text-sm">
              模型
              <input
                required
                value={form.model}
                onChange={(e) => set('model', e.target.value)}
                className="w-full rounded-xl border border-input bg-background px-3 py-2"
              />
            </label>
            <label className="space-y-1.5 text-sm">
              API Key
              <input
                type="password"
                value={form.api_key}
                onChange={(e) => set('api_key', e.target.value)}
                placeholder={editingId ? '留空保留现有密钥' : '可选'}
                autoComplete="new-password"
                className="w-full rounded-xl border border-input bg-background px-3 py-2"
              />
            </label>
          </div>
          <label className="block space-y-1.5 text-sm">
            自定义请求头
            <textarea
              value={headerText}
              onChange={(e) => setHeaderText(e.target.value)}
              placeholder={
                editingId
                  ? `留空保留现有请求头${
                      providers.find((item) => item.id === editingId)?.custom_header_names.length
                        ? `（${providers.find((item) => item.id === editingId)?.custom_header_names.join('、')}）`
                        : ''
                    }`
                  : 'X-API-Key: value\nHTTP-Referer: https://example.com'
              }
              rows={3}
              className="w-full resize-y rounded-xl border border-input bg-background px-3 py-2 font-mono text-xs"
            />
          </label>
          <div className="grid gap-4 sm:grid-cols-3">
            <label className="space-y-1.5 text-sm">
              超时（秒）
              <input
                type="number"
                min={5}
                max={300}
                value={form.timeout_seconds}
                onChange={(e) => set('timeout_seconds', Number(e.target.value))}
                className="w-full rounded-xl border border-input bg-background px-3 py-2"
              />
            </label>
            <label className="space-y-1.5 text-sm">
              温度
              <input
                type="number"
                min={0}
                max={2}
                step={0.1}
                value={form.temperature}
                onChange={(e) => set('temperature', Number(e.target.value))}
                className="w-full rounded-xl border border-input bg-background px-3 py-2"
              />
            </label>
            <label className="space-y-1.5 text-sm">
              最大输出
              <input
                type="number"
                min={256}
                value={form.max_tokens}
                onChange={(e) => set('max_tokens', Number(e.target.value))}
                className="w-full rounded-xl border border-input bg-background px-3 py-2"
              />
            </label>
          </div>
          <div className="flex flex-wrap gap-5 text-sm">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.enabled}
                onChange={(e) => set('enabled', e.target.checked)}
              />
              启用
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.is_default}
                onChange={(e) => set('is_default', e.target.checked)}
              />
              设为图谱默认模型
            </label>
          </div>
          {notice && (
            <p role="status" className="rounded-xl border border-border bg-muted px-3 py-2 text-sm">
              {notice}
            </p>
          )}
          <div className="flex flex-wrap gap-2 border-t border-border pt-5">
            <button
              type="submit"
              disabled={saveMutation.isPending}
              className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
            >
              {saveMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Save className="h-4 w-4" />
              )}
              保存配置
            </button>
            <button
              type="button"
              disabled={!editingId || testMutation.isPending}
              onClick={() => testMutation.mutate()}
              className="inline-flex items-center gap-2 rounded-xl border border-border px-4 py-2 text-sm disabled:opacity-50"
            >
              <Wifi className="h-4 w-4" />
              测试连接
            </button>
            <button
              type="button"
              disabled={!editingId || modelsMutation.isPending}
              onClick={() => modelsMutation.mutate()}
              className="rounded-xl border border-border px-4 py-2 text-sm disabled:opacity-50"
            >
              读取模型列表
            </button>
            {editingId && (
              <button
                type="button"
                aria-label="删除配置"
                onClick={async () => {
                  if (!confirm('确认删除此模型配置？')) return
                  await deleteModelProvider(editingId)
                  setEditingId(undefined)
                  setForm(emptyForm)
                  await queryClient.invalidateQueries({ queryKey: ['model-providers'] })
                }}
                className="ml-auto inline-flex items-center gap-2 rounded-xl border border-destructive px-3 py-2 text-sm text-destructive"
              >
                <Trash2 className="h-4 w-4" />
                删除
              </button>
            )}
          </div>
        </form>
      </main>
    </div>
  )
}
