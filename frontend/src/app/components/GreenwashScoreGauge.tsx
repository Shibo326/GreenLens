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

  const [animatedProgress, setAnimatedProgress] = useState(0);

  useEffect(() => {
    const timeout = setTimeout(() => {
      setAnimatedProgress(targetProgress);
    }, 100);
    return () => clearTimeout(timeout);
  }, [targetProgress]);

  // Arc math — semi-circle
  const radius = 90;
  const cx = 150;
  const cy = 110;
  const arcLength = Math.PI * radius;
  const strokeDashoffset = arcLength - (animatedProgress / 100) * arcLength;

  const displayScore = isNeutral ? "—" : score;

  return (
    <div
      className="flex flex-col items-center justify-center"
      style={{
        maxWidth: "340px",
        width: "100%",
        margin: "0 auto",
        padding: "28px 24px 20px",
        background: "var(--lead)",
        border: "1px solid var(--rule)",
        borderRadius: "16px",
        position: "relative",
        overflow: "hidden",
      }}
      role="figure"
      aria-label={`Greenwash credibility score: ${isNeutral ? "awaiting analysis" : `${score} out of 100, ${band.label}`}`}
    >
      {/* Subtle glow behind the gauge */}
      {!isNeutral && (
        <>
          <div
            aria-hidden="true"
            className="morph-blob"
            style={{
              position: "absolute",
              top: "15%",
              left: "50%",
              transform: "translateX(-50%)",
              width: "220px",
              height: "140px",
              background: `radial-gradient(ellipse at center, ${band.color}20 0%, transparent 70%)`,
              filter: "blur(40px)",
              pointerEvents: "none",
            }}
          />
          {/* Outer glow ring */}
          <div
            aria-hidden="true"
            style={{
              position: "absolute",
              top: "50%",
              left: "50%",
              transform: "translate(-50%, -55%)",
              width: "200px",
              height: "200px",
              borderRadius: "50%",
              background: `conic-gradient(from 0deg, transparent, ${band.color}15, transparent, ${band.color}10, transparent)`,
              animation: "conicSpin 6s linear infinite",
              pointerEvents: "none",
              opacity: 0.6,
            }}
          />
        </>
      )}

      {/* SVG Semi-circle Arc */}
      <div className="relative" style={{ width: "300px", height: "160px" }}>
        <svg
          viewBox="0 0 300 160"
          width="300"
          height="160"
          style={{ overflow: "visible" }}
        >
          {/* Background track */}
          <path
            d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`}
            fill="none"
            stroke="var(--graphite)"
            strokeWidth="18"
            strokeLinecap="round"
          />
          {/* Animated fill arc */}
          <path
            d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`}
            fill="none"
            stroke={band.color}
            strokeWidth="18"
            strokeLinecap="round"
            strokeDasharray={`${arcLength}`}
            strokeDashoffset={strokeDashoffset}
            style={{
              transition: "stroke-dashoffset 1.8s cubic-bezier(0.22, 1, 0.36, 1), stroke 0.4s ease",
              filter: isNeutral ? "none" : `drop-shadow(0 0 8px ${band.color}66)`,
            }}
          />
          {/* Tick marks for 0, 50, 100 */}
          <text x={cx - radius - 5} y={cy + 20} textAnchor="middle" fill="var(--ghost)" fontSize="11" fontFamily="'IBM Plex Sans', sans-serif">0</text>
          <text x={cx} y={cy - radius + 5} textAnchor="middle" fill="var(--ghost)" fontSize="11" fontFamily="'IBM Plex Sans', sans-serif">50</text>
          <text x={cx + radius + 5} y={cy + 20} textAnchor="middle" fill="var(--ghost)" fontSize="11" fontFamily="'IBM Plex Sans', sans-serif">100</text>
        </svg>

        {/* Score number centered in the arc */}
        <div
          style={{
            position: "absolute",
            bottom: "8px",
            left: "50%",
            transform: "translateX(-50%)",
            textAlign: "center",
          }}
        >
          <span
            style={{
              fontFamily: "'Syne', 'DM Sans', sans-serif",
              fontWeight: 800,
              fontSize: "64px",
              color: isNeutral ? "var(--ghost)" : "var(--paper)",
              lineHeight: 1,
              letterSpacing: "-0.03em",
              textShadow: isNeutral
                ? "none"
                : `0 0 20px ${band.color}55, 0 4px 12px rgba(0,0,0,0.3)`,
            }}
          >
            {displayScore}
          </span>
          {!isNeutral && (
            <span
              style={{
                fontFamily: "'IBM Plex Sans', sans-serif",
                fontWeight: 400,
                fontSize: "16px",
                color: "var(--ash)",
                marginLeft: "2px",
              }}
            >
              /100
            </span>
          )}
        </div>
      </div>

      {/* Band label */}
      <span
        style={{
          fontFamily: "'IBM Plex Sans', sans-serif",
          fontWeight: 700,
          fontSize: "15px",
          letterSpacing: "0.06em",
          textTransform: "uppercase",
          color: band.color,
          marginTop: "4px",
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
          color: "var(--ghost)",
          marginTop: "6px",
        }}
      >
        Greenwash Credibility Score
      </span>
    </div>
  );
}
