import { createBrowserRouter, useRouteError, isRouteErrorResponse } from "react-router";
import { lazy, Suspense, useEffect } from "react";
import { motion } from "framer-motion";

// Lazy-loaded page components for code-splitting
const Landing = lazy(() => import("./pages/Landing"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Chat = lazy(() => import("./pages/Chat"));
const Demo = lazy(() => import("./pages/Demo"));

// Professional loading fallback with GreenLens branding
function PageLoader() {
  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--ink)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: "24px",
      }}
    >
      {/* Animated GreenLens logo mark */}
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "16px" }}>
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
          style={{
            width: "36px",
            height: "36px",
            borderRadius: "8px",
            background: "var(--volt)",
            transform: "rotate(45deg)",
            boxShadow: "0 0 20px rgba(59,123,246,0.3)",
          }}
        />
        <span
          style={{
            fontFamily: "'DM Sans', sans-serif",
            fontSize: "18px",
            fontWeight: 700,
            color: "var(--paper)",
            letterSpacing: "-0.02em",
          }}
        >
          GreenLens AI
        </span>
      </div>

      {/* Pulsing dots */}
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <div className="animate-dot-1" style={{ width: "8px", height: "8px", borderRadius: "50%", background: "var(--volt)" }} />
        <div className="animate-dot-2" style={{ width: "8px", height: "8px", borderRadius: "50%", background: "var(--volt)" }} />
        <div className="animate-dot-3" style={{ width: "8px", height: "8px", borderRadius: "50%", background: "var(--volt)" }} />
      </div>

      {/* Shimmer bar */}
      <div style={{ width: "200px", height: "3px", background: "var(--rule)", borderRadius: "2px", overflow: "hidden" }}>
        <div className="shimmer-bar" style={{ height: "100%", borderRadius: "2px", width: "100%" }} />
      </div>
    </div>
  );
}

// Route-level error boundary — handles chunk load failures and 404s cleanly
function RouteErrorBoundary() {
  const error = useRouteError();

  // Auto-reload once on chunk load failure (stale cache after deploy)
  useEffect(() => {
    const message = error instanceof Error ? error.message : String(error);
    const isChunkError =
      message.includes("Failed to fetch dynamically imported module") ||
      message.includes("Loading chunk") ||
      message.includes("Loading CSS chunk") ||
      message.includes("error loading dynamically imported module");

    if (isChunkError) {
      const reloadKey = "greenlens_chunk_reload";
      const alreadyReloaded = sessionStorage.getItem(reloadKey);
      if (!alreadyReloaded) {
        sessionStorage.setItem(reloadKey, "1");
        window.location.reload();
      } else {
        // Already tried reloading — clear the flag so next navigation works
        sessionStorage.removeItem(reloadKey);
      }
    }
  }, [error]);

  const is404 = isRouteErrorResponse(error) && error.status === 404;
  const message = is404
    ? "Page not found."
    : error instanceof Error
    ? error.message
    : "An unexpected error occurred.";

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
            fontFamily: "'DM Sans', sans-serif",
            fontSize: "20px",
            fontWeight: 700,
            color: "var(--paper)",
            marginBottom: "8px",
          }}
        >
          {is404 ? "Page not found" : "Something went wrong"}
        </h2>
        <p
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: "14px",
            color: "var(--ash)",
            marginBottom: "20px",
            lineHeight: 1.6,
          }}
        >
          {message}
        </p>
        <div style={{ display: "flex", gap: "12px", justifyContent: "center" }}>
          <button
            onClick={() => window.location.reload()}
            style={{
              background: "var(--volt)",
              color: "var(--ink)",
              border: "none",
              borderRadius: "var(--radius-btn)",
              padding: "10px 24px",
              fontFamily: "'Inter', sans-serif",
              fontSize: "14px",
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            Reload Page
          </button>
          <button
            onClick={() => (window.location.href = "/")}
            style={{
              background: "transparent",
              color: "var(--ash)",
              border: "1px solid var(--rule)",
              borderRadius: "var(--radius-btn)",
              padding: "10px 24px",
              fontFamily: "'Inter', sans-serif",
              fontSize: "14px",
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            Go Home
          </button>
        </div>
      </div>
    </div>
  );
}

// Wrap lazy components with Suspense
function SuspenseWrapper({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<PageLoader />}>{children}</Suspense>;
}

export const router = createBrowserRouter([
  {
    path: "/",
    element: (
      <SuspenseWrapper>
        <Landing />
      </SuspenseWrapper>
    ),
    errorElement: <RouteErrorBoundary />,
  },
  {
    path: "/dashboard",
    element: (
      <SuspenseWrapper>
        <Dashboard />
      </SuspenseWrapper>
    ),
    errorElement: <RouteErrorBoundary />,
  },
  {
    path: "/chat",
    element: (
      <SuspenseWrapper>
        <Chat />
      </SuspenseWrapper>
    ),
    errorElement: <RouteErrorBoundary />,
  },
  {
    path: "/demo",
    element: (
      <SuspenseWrapper>
        <Demo />
      </SuspenseWrapper>
    ),
    errorElement: <RouteErrorBoundary />,
  },
  {
    path: "*",
    element: (
      <SuspenseWrapper>
        <Landing />
      </SuspenseWrapper>
    ),
    errorElement: <RouteErrorBoundary />,
  },
]);
