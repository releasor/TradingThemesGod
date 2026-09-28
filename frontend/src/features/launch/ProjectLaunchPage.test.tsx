import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import { ProjectLaunchPage } from './ProjectLaunchPage'
import { DEFAULT_POST_AUTH_PATH, resolvePostAuthPath } from './projectEntries'

describe('resolvePostAuthPath', () => {
  it('defaults to project launch page', () => {
    expect(resolvePostAuthPath(null)).toBe(DEFAULT_POST_AUTH_PATH)
    expect(resolvePostAuthPath(undefined)).toBe('/')
    expect(resolvePostAuthPath('/login')).toBe('/')
    expect(resolvePostAuthPath('/register')).toBe('/')
  })

  it('keeps deep links', () => {
    expect(resolvePostAuthPath('/dashboard')).toBe('/dashboard')
    expect(resolvePostAuthPath('/themes')).toBe('/themes')
  })
})

describe('ProjectLaunchPage', () => {
  it('renders TradingThemesGod link and coming-soon placeholders', () => {
    render(
      <MemoryRouter>
        <ProjectLaunchPage />
      </MemoryRouter>
    )

    expect(screen.getByTestId('project-launch-page')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '项目入口' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '进入 Prompt 工作台' })).toHaveAttribute(
      'href',
      '/prompt'
    )
    expect(screen.getByLabelText('应用 C（即将推出）')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: '题材看板' })).not.toBeInTheDocument()
    expect(screen.queryByTestId('app-card-nav')).not.toBeInTheDocument()
  })
})
