/** NotFound 组件测试 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { NotFound } from './NotFound'

const mockNavigate = vi.fn()

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

function renderNotFound() {
  return render(
    <MemoryRouter>
      <NotFound />
    </MemoryRouter>
  )
}

describe('NotFound', () => {
  it('renders 404 text', () => {
    renderNotFound()
    expect(screen.getByText('404')).toBeInTheDocument()
  })

  it('renders title', () => {
    renderNotFound()
    expect(screen.getByText('页面不存在')).toBeInTheDocument()
  })

  it('renders description', () => {
    renderNotFound()
    expect(screen.getByText(/抱歉/)).toBeInTheDocument()
  })

  it('renders three action buttons', () => {
    renderNotFound()
    expect(screen.getByText('返回首页')).toBeInTheDocument()
    expect(screen.getByText('返回上页')).toBeInTheDocument()
    expect(screen.getByText('浏览题材库')).toBeInTheDocument()
  })

  it('navigates to home when return home button is clicked', () => {
    renderNotFound()
    fireEvent.click(screen.getByText('返回首页'))
    expect(mockNavigate).toHaveBeenCalledWith('/')
  })

  it('navigates back when return back button is clicked', () => {
    renderNotFound()
    fireEvent.click(screen.getByText('返回上页'))
    expect(mockNavigate).toHaveBeenCalledWith(-1)
  })

  it('navigates to themes when browse button is clicked', () => {
    renderNotFound()
    fireEvent.click(screen.getByText('浏览题材库'))
    expect(mockNavigate).toHaveBeenCalledWith('/themes')
  })
})
