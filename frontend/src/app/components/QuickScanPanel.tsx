import { useState } from "react";
import { Sparkles, Loader, AlertTriangle, CheckCircle, Info } from "lucide-react";
import { quickScan } from "../../lib/api";
import type { QuickScanResponse } from "../../lib/types";

export function QuickScanPanel() {
  const [claim, setClaim] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<QuickScanResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    const trimmed = claim.trim();
    if (!trimmed || isLoading) return;

    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await quickScan(trimmed);
      setResult(response);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Quick scan failed.";
      if (msg.toLowerCase().includes("fetch") || msg.toLowerCase().includes("network")) {
        setError("Backend not reachable. Start the backend server or check your connection.");
      } else {
        setError(msg);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const getConfidenceStyle = (confidence: string) => {
    switch (confidence) {
      case "HIGH":
        return { color: "var(--leaf)", bg: "var(--leaf-dim)", border: "var(--leaf-border)", icon: <CheckCircle size={14} /> };
      case "MEDIUM":
        return { color: "var(--flag-amber)", bg: "var(--flag-amber-dim)", border: "rgba(240,169,55,0.25)", icon: <AlertTriangle size={14} /> };
      case "LOW":
        return { color: "var(--flag-red)", bg: "var(--flag-red-dim)", border: "rgba(240,68,82,0.25)", icon: <Info size={14} /> };
      default:
        return { color: "var(--ash)", bg: "var(--graphite)", border: "var(--rule)", icon: <Info size={14} /> };
    }
  };

  return (
    <div
      className="rounded-xl p-5"
      style={{
        background: "var(--lead)",
        border: "1px solid var(--rule)",
        maxWidth: "600px",
        width: "100%",
      }}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <div
          style={{
            width: "28px",
            height: "28px",
            borderRadius: "8px",
            background: "var(--leaf-dim)",
            border: "1px solid var(--leaf-border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Sparkles size={14} style={{ color: "var(--leaf)" }} />
        </div>
        <div>
          <h3
            style={{
              fontFamily: "'DM Sans', sans-serif",
              fontSize: "16px",
              fontWeight: 700,
              color: "var(--paper)",
              margin: 0,
            }}
          >
            Quick Scan
          </h3>
          <p
            style={{
              fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
              fontSize: "12px",
              color: "var(--ghost)",
              margin: 0,
            }}
          >
            Paste any sustainability claim for an instant mini-verdict
          </p>
        </div>
      </div>

      {/* Input area */}
      <div className="mb-3">
        <textarea
          value={claim}
          onChange={(e) => setClaim(e.target.value)}
          placeholder={`e.g. "Our packaging is 100% carbon neutral by 2025"`}
          rows={3}
          className="w-full rounded-lg px-4 py-3 placeholder-ghost"
          style={{
            background: "var(--graphite)",
            border: "1px solid var(--rule)",
            color: "var(--paper)",
            fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
            fontSize: "14px",
            lineHeight: 1.5,
            resize: "none",
            outline: "none",
            transition: "border-color 0.2s",
          }}
          onFocus={(e) => { e.currentTarget.style.borderColor = "var(--leaf-border)"; }}
          onBlur={(e) => { e.currentTarget.style.borderColor = "var(--rule)"; }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void handleSubmit();
            }
          }}
          disabled={isLoading}
        />
      </div>

      {/* Submit button */}
      <button
        onClick={() => void handleSubmit()}
        disabled={!claim.trim() || isLoading}
        className="w-full flex items-center justify-center gap-2 rounded-lg"
        style={{
          height: "40px",
          background: !claim.trim() || isLoading ? "var(--graphite)" : "var(--leaf)",
          border: "none",
          color: !claim.trim() || isLoading ? "var(--ghost)" : "var(--ink)",
          fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
          fontSize: "14px",
          fontWeight: 600,
          cursor: !claim.trim() || isLoading ? "not-allowed" : "pointer",
          transition: "background 0.2s, opacity 0.2s",
          opacity: !claim.trim() || isLoading ? 0.6 : 1,
          borderRadius: "var(--radius-btn)",
        }}
      >
        {isLoading ? (
          <>
            <Loader size={14} className="animate-spin-slow" />
            Scanning...
          </>
        ) : (
          <>
            <Sparkles size={14} />
            Scan Claim
          </>
        )}
      </button>

      {/* Error */}
      {error && (
        <div
          className="mt-3 px-4 py-3 rounded-lg"
          style={{
            background: "var(--flag-red-dim)",
            border: "1px solid rgba(240,68,82,0.25)",
            fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
            fontSize: "13px",
            color: "var(--flag-red)",
          }}
        >
          {error}
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="mt-4 space-y-3 animate-slideUp">
          {/* Verdict */}
          <div
            className="rounded-lg p-4"
            style={{
              background: "var(--graphite)",
              border: "1px solid var(--rule)",
            }}
          >
            <div
              style={{
                fontFamily: "'IBM Plex Mono', 'JetBrains Mono', monospace",
                fontSize: "10px",
                fontWeight: 600,
                letterSpacing: "0.1em",
                textTransform: "uppercase",
                color: "var(--ghost)",
                marginBottom: "8px",
              }}
            >
              VERDICT
            </div>
            <p
              style={{
                fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
                fontSize: "14px",
                lineHeight: 1.6,
                color: "var(--paper)",
                margin: 0,
              }}
            >
              {result.verdict}
            </p>
          </div>

          {/* What to look for */}
          {result.whatToLookFor && result.whatToLookFor.length > 0 && (
            <div
              className="rounded-lg p-4"
              style={{
                background: "var(--graphite)",
                border: "1px solid var(--rule)",
              }}
            >
              <div
                style={{
                  fontFamily: "'IBM Plex Mono', 'JetBrains Mono', monospace",
                  fontSize: "10px",
                  fontWeight: 600,
                  letterSpacing: "0.1em",
                  textTransform: "uppercase",
                  color: "var(--ghost)",
                  marginBottom: "8px",
                }}
              >
                WHAT TO LOOK FOR
              </div>
              <ul className="space-y-1.5" style={{ margin: 0, paddingLeft: "16px" }}>
                {result.whatToLookFor.map((item, i) => (
                  <li
                    key={i}
                    style={{
                      fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
                      fontSize: "13px",
                      lineHeight: 1.5,
                      color: "var(--ash)",
                    }}
                  >
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Confidence */}
          {result.confidence && (() => {
            const conf = getConfidenceStyle(result.confidence);
            return (
              <div
                className="inline-flex items-center gap-2 px-3 py-2 rounded-lg"
                style={{
                  background: conf.bg,
                  border: `1px solid ${conf.border}`,
                  color: conf.color,
                  fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
                  fontSize: "12px",
                  fontWeight: 600,
                }}
              >
                {conf.icon}
                Confidence: {result.confidence}
              </div>
            );
          })()}
        </div>
      )}
    </div>
  );
}
