import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { SortSelect } from './SortSelect'

describe('SortSelect', () => {
  const defaultProps = {
    sortBy: 'heat_index' as const,
    sortOrder: 'desc' as const,
    onSortChange: vi.fn(),
  }

  it('renders sort dropdown with options', () => {
    render(<SortSelect {...defaultProps} />)
    const select = screen.getByRole('combobox')
    expect(select).toBeInTheDocument()
    expect(screen.getByText('热度指数')).toBeInTheDocument()
    expect(screen.getByText('涨跌幅')).toBeInTheDocument()
    expect(screen.getByText('股票数量')).toBeInTheDocument()
    expect(screen.getByText('名称')).toBeInTheDocument()
  })

  it('displays current sort field', () => {
    render(<SortSelect {...defaultProps} />)
    const select = screen.getByRole('combobox')
    expect(select).toHaveValue('heat_index')
  })

  it('calls onSortChange when selecting new sort field', () => {
    const onSortChange = vi.fn()
    render(<SortSelect {...defaultProps} onSortChange={onSortChange} />)
    const select = screen.getByRole('combobox')
    fireEvent.change(select, { target: { value: 'rise_fall_pct' } })
    expect(onSortChange).toHaveBeenCalledWith('rise_fall_pct', 'desc')
  })

  it('calls onSortChange with asc for name field', () => {
    const onSortChange = vi.fn()
    render(<SortSelect {...defaultProps} onSortChange={onSortChange} />)
    const select = screen.getByRole('combobox')
    fireEvent.change(select, { target: { value: 'name' } })
    expect(onSortChange).toHaveBeenCalledWith('name', 'asc')
  })

  it('toggles sort order when clicking direction button', () => {
    const onSortChange = vi.fn()
    render(<SortSelect {...defaultProps} onSortChange={onSortChange} />)
    const button = screen.getByTitle('降序')
    fireEvent.click(button)
    expect(onSortChange).toHaveBeenCalledWith('heat_index', 'asc')
  })

  it('shows correct direction icon for asc', () => {
    render(<SortSelect {...defaultProps} sortOrder="asc" />)
    expect(screen.getByTitle('升序')).toBeInTheDocument()
  })

  it('shows correct direction icon for desc', () => {
    render(<SortSelect {...defaultProps} sortOrder="desc" />)
    expect(screen.getByTitle('降序')).toBeInTheDocument()
  })
})
