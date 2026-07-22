import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { SearchInput } from './SearchInput'

// 模拟 useSearchHistory hook
const mockHistory = ['人工智能', '新能源', '芯片']
const mockAddSearch = vi.fn()
const mockClearHistory = vi.fn()
const mockRemoveSearch = vi.fn()

vi.mock('@/hooks/useSearchHistory', () => ({
  useSearchHistory: () => ({
    history: mockHistory,
    addSearch: mockAddSearch,
    clearHistory: mockClearHistory,
    removeSearch: mockRemoveSearch,
  }),
}))

describe('SearchInput', () => {
  const defaultProps = {
    value: '',
    onChange: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders search input with default placeholder', () => {
    render(<SearchInput {...defaultProps} />)
    expect(screen.getByRole('searchbox')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('搜索...')).toBeInTheDocument()
  })

  it('renders with custom placeholder', () => {
    render(<SearchInput {...defaultProps} placeholder="搜索题材..." />)
    expect(screen.getByPlaceholderText('搜索题材...')).toBeInTheDocument()
  })

  it('calls onChange when typing', () => {
    const onChange = vi.fn()
    render(<SearchInput {...defaultProps} onChange={onChange} />)
    const input = screen.getByRole('searchbox')
    fireEvent.change(input, { target: { value: 'test' } })
    expect(onChange).toHaveBeenCalledWith('test')
  })

  it('displays the current value', () => {
    render(<SearchInput {...defaultProps} value="人工智能" />)
    expect(screen.getByRole('searchbox')).toHaveValue('人工智能')
  })

  it('shows clear button when value is not empty', () => {
    render(<SearchInput {...defaultProps} value="test" />)
    expect(screen.getByLabelText('清除搜索')).toBeInTheDocument()
  })

  it('hides clear button when value is empty', () => {
    render(<SearchInput {...defaultProps} value="" />)
    expect(screen.queryByLabelText('清除搜索')).not.toBeInTheDocument()
  })

  it('clears input when clear button is clicked', () => {
    const onChange = vi.fn()
    render(<SearchInput {...defaultProps} value="test" onChange={onChange} />)
    fireEvent.click(screen.getByLabelText('清除搜索'))
    expect(onChange).toHaveBeenCalledWith('')
  })

  it('shows search history dropdown when focused and history exists', () => {
    render(<SearchInput {...defaultProps} />)
    const input = screen.getByRole('searchbox')
    fireEvent.focus(input)
    expect(screen.getByText('搜索历史')).toBeInTheDocument()
    expect(screen.getByText('人工智能')).toBeInTheDocument()
    expect(screen.getByText('新能源')).toBeInTheDocument()
    expect(screen.getByText('芯片')).toBeInTheDocument()
  })

  it('selects history item when clicked', () => {
    const onChange = vi.fn()
    render(<SearchInput {...defaultProps} onChange={onChange} />)
    fireEvent.focus(screen.getByRole('searchbox'))
    fireEvent.click(screen.getByText('人工智能'))
    expect(onChange).toHaveBeenCalledWith('人工智能')
    expect(mockAddSearch).toHaveBeenCalledWith('人工智能')
  })

  it('calls addSearch and onChange on Enter key with valid value', () => {
    const onChange = vi.fn()
    render(<SearchInput {...defaultProps} value="半导体" onChange={onChange} />)
    fireEvent.keyDown(screen.getByRole('searchbox'), { key: 'Enter' })
    expect(mockAddSearch).toHaveBeenCalledWith('半导体')
    expect(onChange).toHaveBeenCalledWith('半导体')
  })

  it('does not submit on Enter with empty value', () => {
    const onChange = vi.fn()
    render(<SearchInput {...defaultProps} value="" onChange={onChange} />)
    fireEvent.keyDown(screen.getByRole('searchbox'), { key: 'Enter' })
    expect(mockAddSearch).not.toHaveBeenCalled()
    expect(onChange).not.toHaveBeenCalled()
  })

  it('does not submit on Enter with whitespace-only value', () => {
    const onChange = vi.fn()
    render(<SearchInput {...defaultProps} value="   " onChange={onChange} />)
    fireEvent.keyDown(screen.getByRole('searchbox'), { key: 'Enter' })
    expect(mockAddSearch).not.toHaveBeenCalled()
  })

  it('has correct ARIA attributes', () => {
    render(<SearchInput {...defaultProps} />)
    const input = screen.getByRole('searchbox')
    expect(input).toHaveAttribute('aria-autocomplete', 'list')
    expect(input).toHaveAttribute('aria-expanded', 'false')
  })

  it('sets aria-expanded to true when dropdown is shown', () => {
    render(<SearchInput {...defaultProps} />)
    fireEvent.focus(screen.getByRole('searchbox'))
    const input = screen.getByRole('searchbox')
    expect(input).toHaveAttribute('aria-expanded', 'true')
  })

  it('renders dropdown with listbox role', () => {
    render(<SearchInput {...defaultProps} />)
    fireEvent.focus(screen.getByRole('searchbox'))
    expect(screen.getByRole('listbox')).toBeInTheDocument()
  })

  it('renders history items with option role', () => {
    render(<SearchInput {...defaultProps} />)
    fireEvent.focus(screen.getByRole('searchbox'))
    const options = screen.getAllByRole('option')
    expect(options).toHaveLength(3)
  })

  it('calls clearHistory when clear history button is clicked', () => {
    render(<SearchInput {...defaultProps} />)
    fireEvent.focus(screen.getByRole('searchbox'))
    fireEvent.click(screen.getByLabelText('清除搜索历史'))
    expect(mockClearHistory).toHaveBeenCalled()
  })

  it('calls removeSearch when individual history item delete is clicked', () => {
    render(<SearchInput {...defaultProps} />)
    fireEvent.focus(screen.getByRole('searchbox'))
    fireEvent.click(screen.getByLabelText('删除搜索记录: 人工智能'))
    expect(mockRemoveSearch).toHaveBeenCalledWith('人工智能')
  })

  it('applies custom className', () => {
    const { container } = render(<SearchInput {...defaultProps} className="custom-class" />)
    expect(container.firstChild).toHaveClass('custom-class')
  })
})
