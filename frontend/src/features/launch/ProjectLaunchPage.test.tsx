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
    expect(resolvePostAuthPath('/home')).toBe('/home')
    expect(resolvePostAuthPath('/themes')).toBe('/themes')
  })
})

describe('ProjectLaunchPage', () => {
  it('renders only product entries without TradingThemesGod modules', () => {
    render(
      <MemoryRouter>
        <ProjectLaunchPage />
      </MemoryRouter>
    )

    expect(screen.getByTestId('project-launch-page')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '项目入口' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '进入 TradingThemesGod' })).toHaveAttribute(
      'href',
      '/home'
    )
    expect(screen.getByRole('link', { name: '进入 Studio Footer' })).toHaveAttribute(
      'href',
      '/studio-footer'
    )
    expect(screen.queryByRole('heading', { name: '题材看板' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: '进入题材库' })).not.toBeInTheDocument()
    expect(screen.queryByTestId('app-card-nav')).not.toBeInTheDocument()
  })
})
