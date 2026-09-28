import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import { SettingsSubnav } from './SettingsSubnav'
import { useAuthStore } from '@/stores/auth'

vi.mock('@/components/ThemeToggle', () => ({
  ThemeToggle: () => <div data-testid="theme-toggle" />,
}))

function renderSubnav(initialEntry: string) {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <SettingsSubnav />
    </MemoryRouter>
  )
}

describe('SettingsSubnav', () => {
  beforeEach(() => {
    useAuthStore.setState({ token: null, user: null })
  })

  it('shows all TradingThemesGod settings tabs and returns to home', () => {
    renderSubnav('/settings/models')

    expect(screen.getByTestId('theme-toggle')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '返回' })).toHaveAttribute('href', '/')
    expect(screen.getByRole('link', { name: '模型设置' })).toHaveAttribute(
      'href',
      '/settings/models'
    )
    expect(screen.getByRole('link', { name: '交易日历' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '数据源' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '快捷键' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '账号设置' })).toBeInTheDocument()
  })

  it('from prompt shows model and account settings only, returns to prompt', () => {
    renderSubnav('/settings/models?from=prompt')

    expect(screen.getByTestId('theme-toggle')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '返回' })).toHaveAttribute('href', '/prompt')
    expect(screen.getByRole('link', { name: '模型设置' })).toHaveAttribute(
      'href',
      '/settings/models?from=prompt'
    )
    expect(screen.getByRole('link', { name: '账号设置' })).toHaveAttribute(
      'href',
      '/settings/account?from=prompt'
    )
    expect(screen.queryByRole('link', { name: '交易日历' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: '数据源' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: '快捷键' })).not.toBeInTheDocument()
  })

  it('shows logout on account settings when logged in', () => {
    useAuthStore.setState({
      token: 'tok',
      user: { id: 1, username: 'alice', created_at: '2026-01-01T00:00:00Z' },
    })
    renderSubnav('/settings/account')

    expect(screen.getByTestId('settings-current-user')).toHaveTextContent('alice')
    expect(screen.getByRole('button', { name: '退出登录' })).toBeInTheDocument()
  })

  it('shows logout on prompt-scoped account settings when logged in', () => {
    useAuthStore.setState({
      token: 'tok',
      user: { id: 1, username: 'alice', created_at: '2026-01-01T00:00:00Z' },
    })
    renderSubnav('/settings/account?from=prompt')

    expect(screen.getByRole('button', { name: '退出登录' })).toBeInTheDocument()
  })

  it('hides logout on other settings pages even when logged in', () => {
    useAuthStore.setState({
      token: 'tok',
      user: { id: 1, username: 'alice', created_at: '2026-01-01T00:00:00Z' },
    })
    renderSubnav('/settings/models')

    expect(screen.queryByRole('button', { name: '退出登录' })).not.toBeInTheDocument()
  })
})
