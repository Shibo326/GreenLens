import { useState, useRef } from "react";
import type { ComparisonRow } from "../../lib/types";

interface ClaimSliderProps {
  row: ComparisonRow;
}

export function ClaimSlider({ row }: ClaimSliderProps) {
  const [sliderValue, setSliderValue] = useState(50);
  const containerRef = useRef<HTMLDivElement>(null);

  const claimText = row.values["Marketing Claim"] || Object.values(row.values)[0] || "";
  const realityText = row.values["Actual (Report)"] || Object.values(row.values)[1] || "";

  return (
    <div
      ref={containerRef}
      className="rounded-xl overflow-hidden"
      style={{ background: "var(--graphite)", border: "1px solid var(--rule)", position: "relative" }}
    >
      {/* Field name header */}
      <div className="px-4 py-2.5" style={{ borderBottom: "1px solid var(--rule)", background: "rgba(10,18,14,0.5)" }}>
        <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "13px", fontWeight: 600, color: "var(--paper)" }}>
          {row.field}
        </span>
      </div>

      {/* Slider content area */}
      <div style={{ position: "relative", minHeight: "80px" }}>
        {/* Marketing Claim (left side) */}
        <div
          className="absolute inset-0 flex items-center px-4"
          style={{
            clipPath: `inset(0 ${100 - sliderValue}% 0 0)`,
            background: "rgba(240,68,82,0.06)",
            borderRight: "2px solid var(--flag-red)",
          }}
        >
          <div className="w-full">
            <div className="flex items-center gap-1.5 mb-1.5">
              <div style={{ width: "5px", height: "5px", borderRadius: "50%", background: "var(--flag-red)" }} />
              <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: "9px", fontWeight: 600, letterSpacing: "0.1em", color: "var(--flag-red)", textTransform: "uppercase" }}>CLAIM</span>
            </div>
            <p style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "13px", lineHeight: 1.5, color: "var(--paper)", margin: 0, paddingRight: "20px" }}>
              {claimText}
            </p>
          </div>
        </div>

        {/* Reality (right side) */}
        <div
          className="absolute inset-0 flex items-center px-4"
          style={{
            clipPath: `inset(0 0 0 ${sliderValue}%)`,
            background: "rgba(61,220,132,0.04)",
          }}
        >
          <div className="w-full" style={{ paddingLeft: "20px" }}>
            <div className="flex items-center gap-1.5 mb-1.5">
              <div style={{ width: "5px", height: "5px", borderRadius: "50%", background: "var(--leaf)" }} />
              <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: "9px", fontWeight: 600, letterSpacing: "0.1em", color: "var(--leaf)", textTransform: "uppercase" }}>REALITY</span>
            </div>
            <p style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "13px", lineHeight: 1.5, color: "var(--paper)", margin: 0 }}>
              {realityText}
            </p>
          </div>
        </div>

        {/* Invisible spacer for height */}
        <div className="px-4 py-4 invisible">
          <div className="mb-1.5" style={{ height: "14px" }} />
          <p style={{ fontSize: "13px", lineHeight: 1.5, margin: 0 }}>
            {claimText.length > realityText.length ? claimText : realityText}
          </p>
        </div>

        {/* Slider handle */}
        <div
          style={{
            position: "absolute",
            top: 0,
            bottom: 0,
            left: `${sliderValue}%`,
            width: "3px",
            background: "var(--paper)",
            boxShadow: "0 0 8px rgba(255,255,255,0.3)",
            cursor: "ew-resize",
            zIndex: 5,
            transition: "left 0.05s ease-out",
          }}
        >
          {/* Handle grip */}
          <div
            style={{
              position: "absolute",
              top: "50%",
              left: "50%",
              transform: "translate(-50%, -50%)",
              width: "24px",
              height: "24px",
              borderRadius: "50%",
              background: "var(--paper)",
              boxShadow: "0 2px 8px rgba(0,0,0,0.4)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <div style={{ display: "flex", gap: "2px" }}>
              <div style={{ width: "2px", height: "10px", background: "var(--ink)", borderRadius: "1px" }} />
              <div style={{ width: "2px", height: "10px", background: "var(--ink)", borderRadius: "1px" }} />
            </div>
          </div>
        </div>
      </div>

      {/* Range input (invisible, controls the slider) */}
      <input
        type="range"
        min={10}
        max={90}
        value={sliderValue}
        onChange={(e) => setSliderValue(Number(e.target.value))}
        className="absolute inset-0 w-full h-full opacity-0 cursor-ew-resize"
        style={{ position: "absolute", top: "32px", zIndex: 10 }}
        aria-label={`Drag to compare claim vs reality for ${row.field}`}
      />
    </div>
  );
}
