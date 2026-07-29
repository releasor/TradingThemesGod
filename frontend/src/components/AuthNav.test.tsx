import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AuthNav } from './AuthNav'
import { useAuthStore } from '@/stores/auth'

describe('AuthNav', () => {
  beforeEach(() => {
    useAuthStore.setState({ token: null, user: null })
  })

  it('shows login/register when logged out', () => {
    render(
      <MemoryRouter>
        <AuthNav />
      </MemoryRouter>
    )
    expect(screen.getByRole('link', { name: /登录/ })).toHaveAttribute('href', '/login')
    expect(screen.getByRole('link', { name: /注册/ })).toHaveAttribute('href', '/register')
  })

  it('links avatar to account settings when logged in', () => {
    useAuthStore.setState({
      token: 'tok',
      user: { id: 1, username: 'alice', created_at: '2026-01-01T00:00:00Z' },
    })
    render(
      <MemoryRouter>
        <AuthNav />
      </MemoryRouter>
    )
    expect(screen.getByRole('link', { name: '打开账号设置' })).toHaveAttribute(
      'href',
      '/settings/account'
    )
    expect(screen.getByRole('button', { name: '退出登录' })).toBeInTheDocument()
  })
})
