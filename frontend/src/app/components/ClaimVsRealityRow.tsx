import type { ComparisonRow } from "../../lib/types";

interface ClaimVsRealityRowProps {
  row: ComparisonRow;
}

export function ClaimVsRealityRow({ row }: ClaimVsRealityRowProps) {
  const columns = Object.keys(row.values);
  const theySayCol = columns[0] ?? "";
  const dataShowsCol = columns[1] ?? columns[0] ?? "";

  const theySayValue = row.values[theySayCol] ?? "—";
  const dataShowsValue = columns.length > 1 ? (row.values[dataShowsCol] ?? "—") : "—";

  return (
    <div className="rounded-lg overflow-hidden" style={{ border: "1px solid var(--rule)" }}>
      {/* Field name header */}
      <div
        className="px-4 py-2"
        style={{
          background: "var(--graphite)",
          borderBottom: "1px solid var(--rule)",
        }}
      >
        <span
          style={{
            fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
            fontSize: "13px",
            fontWeight: 600,
            color: "var(--paper)",
          }}
        >
          {row.field}
        </span>
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 sm:grid-cols-2">
        {/* "They Say" column */}
        <div
          className="px-4 py-3"
          style={{
            background: "var(--paper)",
            borderRight: "1px solid var(--rule)",
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
              marginBottom: "6px",
            }}
          >
            THEY SAY
          </div>
          <div
            style={{
              fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
              fontSize: "14px",
              fontWeight: 500,
              color: "var(--lead)",
              lineHeight: 1.5,
            }}
          >
            {theySayValue}
          </div>
          {columns.length > 0 && (
            <div
              style={{
                fontFamily: "'IBM Plex Mono', 'JetBrains Mono', monospace",
                fontSize: "11px",
                color: "var(--ghost)",
                marginTop: "4px",
              }}
            >
              {theySayCol}
            </div>
          )}
        </div>

        {/* "Data Shows" column */}
        <div
          className="px-4 py-3"
          style={{
            background: "var(--parchment)",
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
              marginBottom: "6px",
            }}
          >
            DATA SHOWS
          </div>
          <div
            style={{
              fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
              fontSize: "14px",
              fontWeight: 500,
              color: "var(--lead)",
              lineHeight: 1.5,
            }}
          >
            {dataShowsValue}
          </div>
          {columns.length > 1 && (
            <div
              style={{
                fontFamily: "'IBM Plex Mono', 'JetBrains Mono', monospace",
                fontSize: "11px",
                color: "var(--ghost)",
                marginTop: "4px",
              }}
            >
              {dataShowsCol}
            </div>
          )}
        </div>
      </div>

      {/* Winner / verdict */}
      {row.winner && (
        <div
          className="px-4 py-2"
          style={{
            background: "var(--graphite)",
            borderTop: "1px solid var(--rule)",
          }}
        >
          <span
            style={{
              fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
              fontSize: "12px",
              fontWeight: 500,
              color: "var(--leaf)",
            }}
          >
            → {row.winner}
          </span>
        </div>
      )}
    </div>
  );
}
