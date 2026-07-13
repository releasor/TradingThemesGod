import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

/**
 * 错误边界组件
 *
 * 捕获子组件树中的渲染错误，显示友好的错误回退 UI，
 * 防止整个应用白屏。
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
  }

  handleReset = (): void => {
    this.setState({ hasError: false, error: null })
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-background p-4">
          <div className="mx-auto max-w-md text-center">
            <div className="mb-4 text-6xl">😵</div>
            <h1 className="mb-2 text-2xl font-bold text-foreground">
              页面出错了
            </h1>
            <p className="mb-6 text-muted-foreground">
              抱歉，页面渲染时发生了错误。请尝试刷新页面。
            </p>
            {this.state.error && (
              <details className="mb-6 rounded-lg border bg-muted p-4 text-left text-sm">
                <summary className="cursor-pointer font-medium">
                  错误详情
                </summary>
                <pre className="mt-2 whitespace-pre-wrap break-all text-muted-foreground">
                  {this.state.error.message}
                </pre>
              </details>
            )}
            <div className="flex justify-center gap-4">
              <button
                onClick={this.handleReset}
                className="rounded-md bg-primary px-4 py-2 text-primary-foreground hover:bg-primary/90"
              >
                重试
              </button>
              <button
                onClick={() => window.location.reload()}
                className="rounded-md border border-input bg-background px-4 py-2 hover:bg-accent"
              >
                刷新页面
              </button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
