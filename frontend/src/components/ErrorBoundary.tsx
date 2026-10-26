import { Component, type ErrorInfo, type ReactNode } from 'react'

import { Button } from '@/components/ui/button'

interface State {
  error: Error | null
}

/** Ошибка рендера не должна оставлять белый экран: показываем, что случилось, и даём выход. */
export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(error, info.componentStack)
  }

  render() {
    if (!this.state.error) return this.props.children
    return (
      <div className="mx-auto flex min-h-full max-w-md flex-col items-center justify-center gap-3 p-6 text-center">
        <p className="text-4xl">😕</p>
        <h1 className="text-lg font-semibold">Что-то пошло не так</h1>
        <p className="text-sm text-slate-500">{this.state.error.message}</p>
        <Button
          onClick={() => {
            this.setState({ error: null })
            window.location.hash = '#/'
          }}
        >
          На главную
        </Button>
      </div>
    )
  }
}
