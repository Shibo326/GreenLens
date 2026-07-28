import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("ErrorBoundary caught:", error, info);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div
          style={{
            minHeight: "100vh",
            background: "var(--ink)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "24px",
          }}
        >
          <div
            style={{
              background: "var(--lead)",
              border: "1px solid rgba(239,68,68,0.3)",
              borderRadius: "12px",
              padding: "32px",
              maxWidth: "480px",
              width: "100%",
              textAlign: "center",
            }}
          >
            <div style={{ fontSize: "32px", marginBottom: "16px" }}>⚠️</div>
            <h2
              style={{
                fontFamily: "'Syne', 'DM Sans', sans-serif",
                fontSize: "20px",
                fontWeight: 700,
                color: "var(--paper)",
                marginBottom: "8px",
              }}
            >
              Something went wrong
            </h2>
            <p
              style={{
                fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
                fontSize: "14px",
                color: "var(--ash)",
                marginBottom: "20px",
                lineHeight: 1.6,
              }}
            >
              {this.state.error?.message ?? "An unexpected error occurred."}
            </p>
            <button
              onClick={() => window.location.reload()}
              style={{
                background: "var(--volt)",
                color: "var(--ink)",
                border: "none",
                borderRadius: "var(--radius-btn)",
                padding: "10px 24px",
                fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
                fontSize: "14px",
                fontWeight: 500,
                cursor: "pointer",
              }}
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
