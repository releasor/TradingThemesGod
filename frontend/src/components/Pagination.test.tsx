/** Pagination 组件测试 */

import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { Pagination, getVisiblePages } from './Pagination'

// Mock lucide-react 图标组件
vi.mock('lucide-react', () => ({
  ChevronLeft: () => <span data-testid="chevron-left" />,
  ChevronRight: () => <span data-testid="chevron-right" />,
  ChevronsLeft: () => <span data-testid="chevrons-left" />,
  ChevronsRight: () => <span data-testid="chevrons-right" />,
}))

describe('getVisiblePages', () => {
  it('返回全部页码当总页数 <= 7', () => {
    expect(getVisiblePages(1, 5)).toEqual([1, 2, 3, 4, 5])
    expect(getVisiblePages(3, 7)).toEqual([1, 2, 3, 4, 5, 6, 7])
    expect(getVisiblePages(1, 1)).toEqual([1])
  })

  it('当前页靠前时省略右侧', () => {
    const result = getVisiblePages(2, 10)
    expect(result).toEqual([1, 2, 3, '...', 10])
  })

  it('当前页靠后时省略左侧', () => {
    const result = getVisiblePages(9, 10)
    expect(result).toEqual([1, '...', 8, 9, 10])
  })

  it('当前页在中间时两侧都省略', () => {
    const result = getVisiblePages(10, 20)
    expect(result).toEqual([1, '...', 9, 10, 11, '...', 20])
  })

  it('当前页为首页时正确显示', () => {
    const result = getVisiblePages(1, 10)
    expect(result).toEqual([1, 2, '...', 10])
  })

  it('当前页为末页时正确显示', () => {
    const result = getVisiblePages(10, 10)
    expect(result).toEqual([1, '...', 9, 10])
  })

  it('当前页接近左边界 (第3页) 无左侧省略', () => {
    const result = getVisiblePages(3, 10)
    expect(result).toEqual([1, 2, 3, 4, '...', 10])
  })

  it('当前页接近右边界 (第8页) 无右侧省略', () => {
    const result = getVisiblePages(8, 10)
    expect(result).toEqual([1, '...', 7, 8, 9, 10])
  })
})

describe('Pagination', () => {
  const defaultProps = {
    page: 1,
    totalPages: 10,
    onPageChange: vi.fn(),
  }

  it('totalPages <= 1 时返回 null', () => {
    const { container } = render(
      <Pagination page={1} totalPages={1} onPageChange={vi.fn()} />
    )
    expect(container.firstChild).toBeNull()
  })

  it('totalPages 为 0 时返回 null', () => {
    const { container } = render(
      <Pagination page={1} totalPages={0} onPageChange={vi.fn()} />
    )
    expect(container.firstChild).toBeNull()
  })

  it('渲染分页导航区域', () => {
    render(<Pagination {...defaultProps} />)
    expect(screen.getByRole('navigation', { name: '分页导航' })).toBeInTheDocument()
  })

  it('渲染页码按钮', () => {
    render(<Pagination {...defaultProps} />)
    expect(screen.getByRole('button', { name: '1' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('button', { name: '2' })).toBeInTheDocument()
  })

  it('active page 有 aria-current 属性', () => {
    render(<Pagination {...defaultProps} page={3} />)
    expect(screen.getByRole('button', { name: '3' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('button', { name: '1' })).not.toHaveAttribute('aria-current')
  })

  it('首页时上一页和首页按钮禁用', () => {
    render(<Pagination {...defaultProps} page={1} />)
    expect(screen.getByTitle('首页')).toBeDisabled()
    expect(screen.getByTitle('上一页')).toBeDisabled()
    expect(screen.getByTitle('下一页')).not.toBeDisabled()
    expect(screen.getByTitle('末页')).not.toBeDisabled()
  })

  it('末页时下一页和末页按钮禁用', () => {
    render(<Pagination {...defaultProps} page={10} />)
    expect(screen.getByTitle('下一页')).toBeDisabled()
    expect(screen.getByTitle('末页')).toBeDisabled()
    expect(screen.getByTitle('首页')).not.toBeDisabled()
    expect(screen.getByTitle('上一页')).not.toBeDisabled()
  })

  it('点击页码按钮调用 onPageChange', () => {
    const onPageChange = vi.fn()
    render(<Pagination page={5} totalPages={10} onPageChange={onPageChange} />)
    fireEvent.click(screen.getByRole('button', { name: '4' }))
    expect(onPageChange).toHaveBeenCalledWith(4)
  })

  it('点击上一页调用 onPageChange', () => {
    const onPageChange = vi.fn()
    render(<Pagination {...defaultProps} page={5} onPageChange={onPageChange} />)
    fireEvent.click(screen.getByTitle('上一页'))
    expect(onPageChange).toHaveBeenCalledWith(4)
  })

  it('点击下一页调用 onPageChange', () => {
    const onPageChange = vi.fn()
    render(<Pagination {...defaultProps} page={5} onPageChange={onPageChange} />)
    fireEvent.click(screen.getByTitle('下一页'))
    expect(onPageChange).toHaveBeenCalledWith(6)
  })

  it('点击首页调用 onPageChange', () => {
    const onPageChange = vi.fn()
    render(<Pagination {...defaultProps} page={5} onPageChange={onPageChange} />)
    fireEvent.click(screen.getByTitle('首页'))
    expect(onPageChange).toHaveBeenCalledWith(1)
  })

  it('点击末页调用 onPageChange', () => {
    const onPageChange = vi.fn()
    render(<Pagination {...defaultProps} page={5} onPageChange={onPageChange} />)
    fireEvent.click(screen.getByTitle('末页'))
    expect(onPageChange).toHaveBeenCalledWith(10)
  })

  it('多页时显示省略号', () => {
    render(<Pagination {...defaultProps} page={5} totalPages={20} />)
    expect(screen.getAllByText('…').length).toBeGreaterThanOrEqual(1)
  })

  describe('每页显示数量选择器', () => {
    it('showPageSizeSelector 为 false 时不渲染', () => {
      render(<Pagination {...defaultProps} />)
      expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
    })

    it('showPageSizeSelector 为 true 时渲染选择器', () => {
      render(
        <Pagination
          {...defaultProps}
          showPageSizeSelector
          onPageSizeChange={vi.fn()}
          pageSize={20}
        />
      )
      const select = screen.getByRole('combobox')
      expect(select).toBeInTheDocument()
      expect(select).toHaveValue('20')
    })

    it('切换每页数量时调用 onPageSizeChange', () => {
      const onPageSizeChange = vi.fn()
      render(
        <Pagination
          {...defaultProps}
          showPageSizeSelector
          onPageSizeChange={onPageSizeChange}
          pageSize={20}
        />
      )
      fireEvent.change(screen.getByRole('combobox'), { target: { value: '50' } })
      expect(onPageSizeChange).toHaveBeenCalledWith(50)
    })

    it('自定义 pageSizeOptions 生效', () => {
      render(
        <Pagination
          {...defaultProps}
          showPageSizeSelector
          onPageSizeChange={vi.fn()}
          pageSize={5}
          pageSizeOptions={[5, 15, 30]}
        />
      )
      const options = screen.getByRole('combobox').querySelectorAll('option')
      expect(options).toHaveLength(3)
      expect(options[0]).toHaveValue('5')
      expect(options[1]).toHaveValue('15')
      expect(options[2]).toHaveValue('30')
    })
  })

  describe('跳转到指定页', () => {
    it('showJumpToPage 为 false 时不渲染', () => {
      render(<Pagination {...defaultProps} />)
      expect(screen.queryByRole('spinbutton')).not.toBeInTheDocument()
    })

    it('showJumpToPage 为 true 时渲染输入框和按钮', () => {
      render(<Pagination {...defaultProps} showJumpToPage />)
      expect(screen.getByRole('spinbutton', { name: '跳转到页码' })).toBeInTheDocument()
      expect(screen.getByText('确定')).toBeInTheDocument()
    })

    it('输入页码后点击确定跳转', () => {
      const onPageChange = vi.fn()
      render(<Pagination {...defaultProps} onPageChange={onPageChange} showJumpToPage />)
      const input = screen.getByRole('spinbutton', { name: '跳转到页码' })
      fireEvent.change(input, { target: { value: '7' } })
      fireEvent.click(screen.getByText('确定'))
      expect(onPageChange).toHaveBeenCalledWith(7)
    })

    it('输入页码后按 Enter 跳转', () => {
      const onPageChange = vi.fn()
      render(<Pagination {...defaultProps} onPageChange={onPageChange} showJumpToPage />)
      const input = screen.getByRole('spinbutton', { name: '跳转到页码' })
      fireEvent.change(input, { target: { value: '3' } })
      fireEvent.keyDown(input, { key: 'Enter' })
      expect(onPageChange).toHaveBeenCalledWith(3)
    })

    it('不跳转超出范围的页码', () => {
      const onPageChange = vi.fn()
      render(
        <Pagination
          {...defaultProps}
          totalPages={5}
          onPageChange={onPageChange}
          showJumpToPage
        />
      )
      const input = screen.getByRole('spinbutton', { name: '跳转到页码' })
      fireEvent.change(input, { target: { value: '99' } })
      fireEvent.click(screen.getByText('确定'))
      expect(onPageChange).not.toHaveBeenCalled()
    })

    it('不跳转无效页码 (0)', () => {
      const onPageChange = vi.fn()
      render(
        <Pagination
          {...defaultProps}
          onPageChange={onPageChange}
          showJumpToPage
        />
      )
      const input = screen.getByRole('spinbutton', { name: '跳转到页码' })
      fireEvent.change(input, { target: { value: '0' } })
      fireEvent.click(screen.getByText('确定'))
      expect(onPageChange).not.toHaveBeenCalled()
    })
  })

  it('导航区域有正确的 aria-label', () => {
    render(<Pagination {...defaultProps} />)
    expect(screen.getByLabelText('分页导航')).toBeInTheDocument()
  })
})
