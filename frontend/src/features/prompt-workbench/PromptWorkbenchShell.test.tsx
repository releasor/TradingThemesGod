import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { PromptWorkbenchShell } from './PromptWorkbenchShell'

vi.mock('@/api/model-provider', () => ({
  fetchModelProviders: async () => [
    {
      id: 1,
      name: 'demo',
      protocol: 'openai_compatible',
      base_url: 'http://x',
      model: 'm',
      api_key: '',
      has_api_key: false,
      custom_headers: {},
      custom_header_names: [],
      timeout_seconds: 60,
      temperature: 0.1,
      max_tokens: 1000,
      enabled: true,
      is_default: true,
      created_at: '',
      updated_at: '',
    },
  ],
}))

vi.mock('@/components/ThemeToggle', () => ({
  ThemeToggle: () => <button type="button">theme</button>,
}))

describe('PromptWorkbenchShell', () => {
  it('renders four module tabs', () => {
    const client = new QueryClient()
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/prompt/optimize']}>
          <Routes>
            <Route path="/prompt" element={<PromptWorkbenchShell />}>
              <Route path="optimize" element={<div>opt</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    )
    expect(screen.getByTestId('prompt-workbench-shell')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '优化' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '设计' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '我的 Prompt' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '自由聊天' })).toBeInTheDocument()
    expect(document.title).toBe('Prompt 工作台')
  })

  it('links model settings with from=prompt', () => {
    const client = new QueryClient()
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/prompt/optimize']}>
          <Routes>
            <Route path="/prompt" element={<PromptWorkbenchShell />}>
              <Route path="optimize" element={<div>opt</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    )
    expect(screen.getByRole('link', { name: '模型设置' })).toHaveAttribute(
      'href',
      '/settings/models?from=prompt'
    )
  })
})
