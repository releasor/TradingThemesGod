import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { FilterBar } from './FilterBar'

describe('FilterBar', () => {
  const defaultProps = {
    searchInput: '',
    onSearchChange: vi.fn(),
    categories: ['科技', '医药', '新能源'],
    selectedCategory: undefined,
    onCategoryChange: vi.fn(),
    selectedTags: undefined,
    onTagsChange: vi.fn(),
    activeFilterCount: 0,
    onClearFilters: vi.fn(),
  }

  it('renders search input', () => {
    render(<FilterBar {...defaultProps} />)
    expect(screen.getByPlaceholderText('搜索题材名称或描述...')).toBeInTheDocument()
  })

  it('renders category dropdown with options', () => {
    render(<FilterBar {...defaultProps} />)
    const select = screen.getByRole('combobox')
    expect(select).toBeInTheDocument()
    expect(screen.getByText('全部分类')).toBeInTheDocument()
    expect(screen.getByText('科技')).toBeInTheDocument()
    expect(screen.getByText('医药')).toBeInTheDocument()
    expect(screen.getByText('新能源')).toBeInTheDocument()
  })

  it('calls onSearchChange when typing in search', () => {
    const onSearchChange = vi.fn()
    render(<FilterBar {...defaultProps} onSearchChange={onSearchChange} />)
    const input = screen.getByPlaceholderText('搜索题材名称或描述...')
    fireEvent.change(input, { target: { value: 'test' } })
    expect(onSearchChange).toHaveBeenCalledWith('test')
  })

  it('calls onCategoryChange when selecting category', () => {
    const onCategoryChange = vi.fn()
    render(<FilterBar {...defaultProps} onCategoryChange={onCategoryChange} />)
    const select = screen.getByRole('combobox')
    fireEvent.change(select, { target: { value: '科技' } })
    expect(onCategoryChange).toHaveBeenCalledWith('科技')
  })

  it('renders tag input', () => {
    render(<FilterBar {...defaultProps} />)
    expect(screen.getByPlaceholderText('添加标签...')).toBeInTheDocument()
  })

  it('renders tag chips when tags are selected', () => {
    render(<FilterBar {...defaultProps} selectedTags="AI,芯片" />)
    expect(screen.getByText('AI')).toBeInTheDocument()
    expect(screen.getByText('芯片')).toBeInTheDocument()
  })

  it('renders clear filters button when activeFilterCount > 0', () => {
    render(<FilterBar {...defaultProps} activeFilterCount={2} />)
    expect(screen.getByText(/清除全部筛选/)).toBeInTheDocument()
  })

  it('does not render clear filters button when activeFilterCount is 0', () => {
    render(<FilterBar {...defaultProps} activeFilterCount={0} />)
    expect(screen.queryByText(/清除全部筛选/)).not.toBeInTheDocument()
  })
})
