import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  message: string
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, message: '' }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error.message }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('UI error:', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <section className="page">
          <div className="card">
            <h2>Something went wrong</h2>
            <p className="widget-error">{this.state.message}</p>
            <button type="button" className="inline-btn" onClick={() => window.location.reload()}>
              Reload app
            </button>
          </div>
        </section>
      )
    }
    return this.props.children
  }
}