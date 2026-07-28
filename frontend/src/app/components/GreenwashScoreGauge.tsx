import { useEffect, useState } from "react";

interface GreenwashScoreGaugeProps {
  score?: number;
}

function getBand(score: number): { label: string; color: string; dimColor: string } {
  if (score <= 30) return { label: "Mostly Greenwashing", color: "var(--flag-red)", dimColor: "var(--flag-red-dim)" };
  if (score <= 60) return { label: "Vague / Mixed Signals", color: "var(--flag-amber)", dimColor: "var(--flag-amber-dim)" };
  return { label: "Credible", color: "var(--leaf)", dimColor: "var(--leaf-dim)" };
}

export function GreenwashScoreGauge({ score }: GreenwashScoreGaugeProps) {
  const isNeutral = score === undefined || score === null;
  const band = isNeutral
    ? { label: "Awaiting analysis", color: "var(--ghost)", dimColor: "rgba(78,97,87,0.08)" }
    : getBand(score!);

  const targetProgress = isNeutral ? 0 : Math.min(100, Math.max(0, score!));

  // Animate arc fill on mount
  const [animatedProgress, setAnimatedProgress] = useState(0);

  useEffect(() => {
    // Small delay to trigger CSS transition from 0 to target
    const timeout = setTimeout(() => {
      setAnimatedProgress(targetProgress);
    }, 50);
    return () => clearTimeout(timeout);
  }, [targetProgress]);

  // Arc math: semi-circle from left to right (180 degrees)
  // Center at (140, 120), radius 100
  // The arc path goes from (40, 120) to (240, 120) — a 180-degree semi-circle
  const radius = 100;
  const cx = 140;
  const cy = 120;
  const arcLength = Math.PI * radius; // half circumference
  const strokeDashoffset = arcLength - (animatedProgress / 100) * arcLength;

  const displayScore = isNeutral ? "—" : score;

  return (
    <div
      className="flex flex-col items-center justify-center"
      style={{ maxWidth: "280px", margin: "0 auto" }}
      role="figure"
      aria-label={`Greenwash credibility score: ${isNeutral ? "awaiting analysis" : `${score} out of 100, ${band.label}`}`}
    >
      {/* SVG Semi-circle Arc */}
      <div className="relative" style={{ width: "280px", height: "155px" }}>
        <svg
          viewBox="0 0 280 155"
          width="280"
          height="155"
          style={{ overflow: "visible" }}
        >
          {/* Background track */}
          <path
            d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`}
            fill="none"
            stroke="var(--rule)"
            strokeWidth="14"
            strokeLinecap="round"
          />
          {/* Animated fill arc */}
          <path
            d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`}
            fill="none"
            stroke={band.color}
            strokeWidth="14"
            strokeLinecap="round"
            strokeDasharray={`${arcLength}`}
            strokeDashoffset={strokeDashoffset}
            style={{
              transition: "stroke-dashoffset 1.5s ease-out, stroke 0.3s ease",
            }}
          />
        </svg>

        {/* Score number centered below arc */}
        <div
          style={{
            position: "absolute",
            bottom: "0",
            left: "50%",
            transform: "translateX(-50%)",
            textAlign: "center",
          }}
        >
          <span
            style={{
              fontFamily: "'Syne', sans-serif",
              fontWeight: 800,
              fontSize: "52px",
              color: isNeutral ? "var(--ghost)" : "var(--paper)",
              lineHeight: 1,
              textShadow: isNeutral
                ? "none"
                : `0 0 24px ${band.color}44, 0 0 48px ${band.color}22`,
            }}
          >
            {displayScore}
          </span>
        </div>
      </div>

      {/* Band label */}
      <span
        style={{
          fontFamily: "'IBM Plex Sans', sans-serif",
          fontWeight: 600,
          fontSize: "14px",
          letterSpacing: "0.04em",
          textTransform: "uppercase",
          color: band.color,
          marginTop: "8px",
        }}
      >
        {band.label}
      </span>

      {/* Subtitle */}
      <span
        style={{
          fontFamily: "'IBM Plex Sans', sans-serif",
          fontWeight: 400,
          fontSize: "12px",
          color: "var(--ash)",
          marginTop: "4px",
        }}
      >
        Greenwash Credibility Score
      </span>
    </div>
  );
}
