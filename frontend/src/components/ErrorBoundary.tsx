import { Component, type ErrorInfo, type ReactNode } from "react";
import { IS_WEB } from "../config/appMode";

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
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("Unhandled interface error", error, info.componentStack);
  }

  render() {
    if (!this.state.error) {
      return this.props.children;
    }

    return (
      <main className="fatal">
        <div className="card fatal-card">
          <h1 className="display">Something went wrong</h1>
          <p className="muted">
            {IS_WEB
              ? "The application hit an unexpected problem. Reloading usually fixes it."
              : "The application hit an unexpected problem. Your saved workspaces are safe on this computer."}
          </p>
          <pre className="fatal-detail">{this.state.error.message}</pre>
          <button
            type="button"
            className="btn"
            onClick={() => window.location.assign("/")}
          >
            Reload Variance Studio
          </button>
        </div>
      </main>
    );
  }
}