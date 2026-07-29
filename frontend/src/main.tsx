import { createRoot } from "react-dom/client";
import App from "./app/App";
import "./styles/index.css";
import { AppProvider } from "./lib/store";
import { ErrorBoundary } from "./app/components/ErrorBoundary";
import { API_BASE_URL } from "./lib/api";

// Warm up the Railway backend on app load so cold starts don't hit during demo.
// Fire-and-forget — never blocks rendering, never shows errors to the user.
fetch(`${API_BASE_URL}/health`, { method: "GET" }).catch(() => {});

createRoot(document.getElementById("root")!).render(
  <ErrorBoundary>
    <AppProvider>
      {/* Subtle film grain texture for premium depth */}
      <div className="noise-overlay" aria-hidden="true" />
      <App />
    </AppProvider>
  </ErrorBoundary>
);
