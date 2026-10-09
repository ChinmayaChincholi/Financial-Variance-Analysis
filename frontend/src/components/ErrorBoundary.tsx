import { Component } from "react";

import type {
  ErrorInfo,
  ReactNode,
} from "react";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  error: Error | null;
}

export class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = {
    error: null,
  };

  static getDerivedStateFromError(
    error: Error,
  ): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(
    error: Error,
    info: ErrorInfo,
  ) {
    console.error(
      "UI crash:",
      error,
      info.componentStack,
    );
  }

  render() {
    if (this.state.error) {
      return (
        <main className="app-shell">
          <div className="page-container">
            <h2>Something went wrong</h2>

            <p>
              {this.state.error.message}
            </p>

            <button
              type="button"
              className="primary-button"
              onClick={() => {
                window.location.href = "/";
              }}
            >
              Back to start
            </button>
          </div>
        </main>
      );
    }

    return this.props.children;
  }
}