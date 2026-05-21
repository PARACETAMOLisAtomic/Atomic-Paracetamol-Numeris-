import { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error caught by ErrorBoundary:', error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div className="error-boundary-container">
            <div className="error-boundary-card">
              <div className="error-icon-wrapper">
                <span className="error-pulse" />
              </div>
              <h2>Critical Core Failure</h2>
              <p>
                An unexpected runtime crash occurred within the Numeris platform interface. Diagnostic logs have been generated.
              </p>
              {this.state.error && (
                <pre className="error-details">
                  {this.state.error.name}: {this.state.error.message}
                </pre>
              )}
              <button onClick={this.handleReset} className="error-retry-btn">
                Re-initialize Interface
              </button>
            </div>
            <style>{`
              .error-boundary-container {
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                padding: 2rem;
                background: #03040a;
                color: #edf7ff;
                font-family: Inter, system-ui, sans-serif;
              }
              .error-boundary-card {
                width: 100%;
                max-width: 480px;
                background: rgba(15, 23, 42, 0.4);
                backdrop-filter: blur(16px);
                border: 1px solid rgba(239, 68, 68, 0.15);
                border-radius: 16px;
                padding: 3rem 2rem;
                text-align: center;
                box-shadow: 
                  0 20px 40px rgba(0, 0, 0, 0.6),
                  0 0 80px rgba(239, 68, 68, 0.03);
                display: flex;
                flex-direction: column;
                align-items: center;
              }
              .error-icon-wrapper {
                width: 48px;
                height: 48px;
                border-radius: 50%;
                background: rgba(239, 68, 68, 0.08);
                border: 1px solid rgba(239, 68, 68, 0.2);
                display: flex;
                align-items: center;
                justify-content: center;
                margin-bottom: 1.5rem;
                position: relative;
              }
              .error-pulse {
                width: 12px;
                height: 12px;
                border-radius: 50%;
                background: #ef4444;
                box-shadow: 0 0 12px #ef4444;
              }
              .error-boundary-card h2 {
                font-family: 'Space Grotesk', sans-serif;
                font-size: 1.4rem;
                font-weight: 600;
                color: #ffffff;
                margin: 0 0 0.75rem;
                letter-spacing: 0.02em;
              }
              .error-boundary-card p {
                font-size: 0.9rem;
                color: #94a3b8;
                line-height: 1.55;
                margin: 0 0 1.75rem;
              }
              .error-details {
                width: 100%;
                background: rgba(0, 0, 0, 0.25);
                padding: 1rem;
                border-radius: 10px;
                border: 1px solid rgba(255, 255, 255, 0.05);
                font-family: monospace;
                font-size: 0.8rem;
                color: #fca5a5;
                text-align: left;
                overflow-x: auto;
                margin: 0 0 2rem;
                white-space: pre-wrap;
                word-break: break-all;
              }
              .error-retry-btn {
                background: linear-gradient(135deg, #ef4444 0%, #b91c1c 100%);
                color: #ffffff;
                border: none;
                border-radius: 10px;
                padding: 0.85rem 1.5rem;
                font-size: 0.9rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.25s ease;
                box-shadow: 0 6px 20px rgba(239, 68, 68, 0.2);
              }
              .error-retry-btn:hover {
                filter: brightness(1.1);
                transform: translateY(-1px);
                box-shadow: 0 6px 24px rgba(239, 68, 68, 0.3);
              }
            `}</style>
          </div>
        )
      );
    }

    return this.props.children;
  }
}
