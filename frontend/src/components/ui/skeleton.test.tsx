/** Skeleton 组件测试 */

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Skeleton, SkeletonText, SkeletonCircle } from './skeleton'

describe('Skeleton', () => {
  it('renders a div element', () => {
    const { container } = render(<Skeleton />)
    const el = container.firstChild as HTMLElement
    expect(el.tagName).toBe('DIV')
  })

  it('applies base classes', () => {
    const { container } = render(<Skeleton />)
    const el = container.firstChild as HTMLElement
    expect(el).toHaveClass('rounded-xl')
    expect(el).toHaveClass('bg-muted')
  })

  it('defaults to pulse variant', () => {
    const { container } = render(<Skeleton />)
    const el = container.firstChild as HTMLElement
    expect(el).toHaveClass('animate-pulse')
  })

  it('applies pulse variant class', () => {
    const { container } = render(<Skeleton variant="pulse" />)
    const el = container.firstChild as HTMLElement
    expect(el).toHaveClass('animate-pulse')
  })

  it('applies wave variant class', () => {
    const { container } = render(<Skeleton variant="wave" />)
    const el = container.firstChild as HTMLElement
    expect(el).toHaveClass('animate-wave')
  })

  it('applies shimmer variant classes', () => {
    const { container } = render(<Skeleton variant="shimmer" />)
    const el = container.firstChild as HTMLElement
    expect(el).toHaveClass('animate-shimmer')
    expect(el).toHaveClass('bg-gradient-to-r')
    expect(el).toHaveClass('from-muted')
    expect(el).toHaveClass('via-muted/50')
    expect(el).toHaveClass('to-muted')
  })

  it('applies custom className', () => {
    const { container } = render(<Skeleton className="w-full h-8" />)
    const el = container.firstChild as HTMLElement
    expect(el).toHaveClass('w-full')
    expect(el).toHaveClass('h-8')
    // 基础类保略
    expect(el).toHaveClass('rounded-xl')
  })

  it('forwards HTML attributes', () => {
    render(<Skeleton data-testid="my-skeleton" aria-label="加载中" />)
    const el = screen.getByTestId('my-skeleton')
    expect(el).toHaveAttribute('aria-label', '加载中')
  })

  it('forwards style prop', () => {
    const { container } = render(<Skeleton style={{ width: 200 }} />)
    const el = container.firstChild as HTMLElement
    expect(el.style.width).toBe('200px')
  })
})

describe('SkeletonText', () => {
  it('renders default 3 lines', () => {
    const { container } = render(<SkeletonText />)
    // wrapper 内应该有 3 不Skeleton 子元索
    const lines = container.firstChild!.childNodes
    expect(lines.length).toBe(3)
  })

  it('renders custom number of lines', () => {
    const { container } = render(<SkeletonText lines={5} />)
    const lines = container.firstChild!.childNodes
    expect(lines.length).toBe(5)
  })

  it('renders single line', () => {
    const { container } = render(<SkeletonText lines={1} />)
    const lines = container.firstChild!.childNodes
    expect(lines.length).toBe(1)
  })

  it('applies space-y-2 to wrapper', () => {
    const { container } = render(<SkeletonText />)
    const wrapper = container.firstChild as HTMLElement
    expect(wrapper).toHaveClass('space-y-2')
  })

  it('applies custom className to wrapper', () => {
    const { container } = render(<SkeletonText className="my-wrapper" />)
    const wrapper = container.firstChild as HTMLElement
    expect(wrapper).toHaveClass('my-wrapper')
    expect(wrapper).toHaveClass('space-y-2')
  })

  it('all lines have h-4 class', () => {
    const { container } = render(<SkeletonText lines={4} />)
    const wrapper = container.firstChild as HTMLElement
    wrapper.querySelectorAll(':scope > div').forEach((line) => {
      expect(line).toHaveClass('h-4')
    })
  })

  it('last line has w-3/4 and other lines have w-full', () => {
    const { container } = render(<SkeletonText lines={3} />)
    const wrapper = container.firstChild as HTMLElement
    const lines = Array.from(wrapper.querySelectorAll(':scope > div'))

    // 前两表w-full
    expect(lines[0]).toHaveClass('w-full')
    expect(lines[1]).toHaveClass('w-full')
    // 最后一表w-3/4
    expect(lines[2]).toHaveClass('w-3/4')
    expect(lines[2]).not.toHaveClass('w-full')
  })

  it('forwards HTML attributes to wrapper', () => {
    const { container } = render(<SkeletonText data-testid="text-skeleton" role="status" />)
    const wrapper = container.firstChild as HTMLElement
    expect(wrapper).toHaveAttribute('data-testid', 'text-skeleton')
    expect(wrapper).toHaveAttribute('role', 'status')
  })
})

describe('SkeletonCircle', () => {
  it('renders with rounded-full', () => {
    const { container } = render(<SkeletonCircle />)
    const el = container.firstChild as HTMLElement
    expect(el).toHaveClass('rounded-full')
  })

  it('retains base skeleton classes', () => {
    const { container } = render(<SkeletonCircle />)
    const el = container.firstChild as HTMLElement
    expect(el).toHaveClass('bg-muted')
    expect(el).toHaveClass('animate-pulse')
  })

  it('applies custom className', () => {
    const { container } = render(<SkeletonCircle className="w-12 h-12" />)
    const el = container.firstChild as HTMLElement
    expect(el).toHaveClass('w-12')
    expect(el).toHaveClass('h-12')
    expect(el).toHaveClass('rounded-full')
  })

  it('forwards HTML attributes', () => {
    render(<SkeletonCircle data-testid="circle-skeleton" aria-hidden="true" />)
    const el = screen.getByTestId('circle-skeleton')
    expect(el).toHaveAttribute('aria-hidden', 'true')
  })

  it('can use a different variant', () => {
    const { container } = render(<SkeletonCircle variant="shimmer" />)
    const el = container.firstChild as HTMLElement
    expect(el).toHaveClass('animate-shimmer')
    expect(el).toHaveClass('rounded-full')
  })
})
