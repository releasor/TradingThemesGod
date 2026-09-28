import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { OptimizePage } from './OptimizePage'
import { optimizePromptStream } from '@/features/prompt-workbench/api/optimize'

vi.mock('@/api/model-provider', () => ({
  fetchModelProviders: async () => [
    { id: 1, name: 'test', enabled: true, is_default: true },
  ],
}))

vi.mock('@/App', () => ({
  useToastContext: () => ({
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  }),
}))

vi.mock('@/features/prompt-workbench/api/optimize', () => ({
  optimizePromptStream: vi.fn(),
  iteratePromptStream: vi.fn(),
}))

vi.mock('@/features/prompt-workbench/api/library', () => ({
  createPromptItem: vi.fn(),
}))

vi.mock('@/features/prompt-workbench/stores/modelSelection', () => ({
  usePromptModelSelection: (sel: (s: { providerId: number }) => unknown) =>
    sel({ providerId: 1 }),
}))

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <OptimizePage />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('OptimizePage UX', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows samples and exposes result actions', async () => {
    const user = userEvent.setup()
    renderPage()

    expect(screen.getByRole('button', { name: '研报摘要助手' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '研报摘要助手' }))
    expect(screen.getByLabelText('原始 Prompt')).toHaveValue(
      '你是一名卖方分析师助理。请用中文总结用户给出的研报要点，输出：核心结论、关键数据、风险点。语气客观，不超过 300 字。'
    )

    expect(screen.getByRole('button', { name: '复制' })).toBeDisabled()
    expect(screen.getByRole('button', { name: '存库' })).toBeDisabled()
    expect(screen.getByRole('button', { name: '用作原文继续' })).toBeDisabled()
  })

  it('shows goal chips in smart mode and framework description when switched', async () => {
    const user = userEvent.setup()
    renderPage()

    expect(screen.getByRole('button', { name: '更短' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '命名框架' }))
    expect(screen.getByText(/适合需要明确角色/)).toBeInTheDocument()
  })

  it('shows result loading animation while waiting for first stream token', async () => {
    const user = userEvent.setup()
    let release!: (value: { result: string; run_id: number | null }) => void
    const gate = new Promise<{ result: string; run_id: number | null }>((resolve) => {
      release = resolve
    })
    vi.mocked(optimizePromptStream).mockImplementation(async (_input, onEvent) => {
      onEvent({ type: 'start' })
      const res = await gate
      onEvent({ type: 'done', result: res.result, run_id: res.run_id })
      return res
    })

    renderPage()
    await user.click(screen.getByRole('button', { name: '研报摘要助手' }))
    await user.click(screen.getByRole('button', { name: '运行优化' }))

    const loading = await screen.findByTestId('optimize-result-loading')
    expect(loading).toBeInTheDocument()
    expect(loading).toHaveTextContent(/等待模型输出|正在连接|思考中|生成中/)

    release({ result: '优化完成的 Prompt', run_id: 9 })
    await waitFor(() => {
      expect(screen.queryByTestId('optimize-result-loading')).not.toBeInTheDocument()
    })
    expect(screen.getByLabelText('优化结果')).toHaveValue('优化完成的 Prompt')
  })
})
