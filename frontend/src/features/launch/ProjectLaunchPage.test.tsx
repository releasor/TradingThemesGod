import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import { ProjectLaunchPage } from './ProjectLaunchPage'
import {
  DEFAULT_POST_AUTH_PATH,
  isTradingAppPath,
  resolvePostAuthPath,
} from './projectEntries'

describe('resolvePostAuthPath', () => {
  it('defaults to project launch page', () => {
    expect(resolvePostAuthPath(null)).toBe(DEFAULT_POST_AUTH_PATH)
    expect(resolvePostAuthPath(undefined)).toBe('/')
    expect(resolvePostAuthPath('/login')).toBe('/')
    expect(resolvePostAuthPath('/register')).toBe('/')
  })

  it('keeps prompt deep links and closes personal OS', () => {
    expect(resolvePostAuthPath('/prompt')).toBe('/prompt')
    expect(resolvePostAuthPath('/os')).toBe('/')
    expect(resolvePostAuthPath('/os/dashboard')).toBe('/')
  })

  it('redirects closed trading paths to launch page', () => {
    expect(resolvePostAuthPath('/dashboard')).toBe('/')
    expect(resolvePostAuthPath('/themes')).toBe('/')
    expect(resolvePostAuthPath('/themes/1')).toBe('/')
    expect(resolvePostAuthPath('/settings/calendar')).toBe('/')
  })
})

describe('isTradingAppPath', () => {
  it('matches closed trading and personal OS routes', () => {
    expect(isTradingAppPath('/dashboard')).toBe(true)
    expect(isTradingAppPath('/os')).toBe(true)
    expect(isTradingAppPath('/os/dashboard')).toBe(true)
    expect(isTradingAppPath('/prompt')).toBe(false)
  })
})

describe('ProjectLaunchPage', () => {
  it('renders workspace apps without TradingThemesGod entry', () => {
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
    expect(screen.queryByRole('link', { name: '进入个人 AI OS' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: '进入 TradingThemesGod' })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'TradingThemesGod' })).not.toBeInTheDocument()
    expect(screen.queryByTestId('app-card-nav')).not.toBeInTheDocument()
    const beian = screen.getByTestId('icp-beian-link')
    expect(beian).toHaveTextContent('闽ICP备2026020085号-1')
    expect(beian).toHaveAttribute('href', 'https://beian.miit.gov.cn/')
  })
})
