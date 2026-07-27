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
  const displayScore = isNeutral ? "—" : score;
  const band = isNeutral
    ? { label: "Awaiting Data", color: "var(--ghost)", dimColor: "rgba(78,97,87,0.08)" }
    : getBand(score!);

  const progress = isNeutral ? 0 : Math.min(100, Math.max(0, score!));
  const circumference = Math.PI * 80;
  const strokeDashoffset = circumference - (progress / 100) * circumference;

  return (
    <div
      className="flex flex-col items-center justify-center rounded-xl p-8"
      style={{
        background: "rgba(19, 31, 25, 0.7)",
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
        border: `1px solid ${isNeutral ? "var(--rule)" : band.color}44`,
      }}
      role="figure"
      aria-label={`Greenwash credibility score: ${isNeutral ? "awaiting data" : `${score} out of 100, ${band.label}`}`}
    >
      {/* SVG Arc */}
      <div className="relative" style={{ width: "200px", height: "110px", marginBottom: "12px" }}>
        <svg viewBox="0 0 200 110" width="200" height="110" style={{ overflow: "visible" }}>
          <path
            d="M 10 100 A 90 90 0 0 1 190 100"
            fill="none"
            stroke="var(--rule)"
            strokeWidth="10"
            strokeLinecap="round"
          />
          {!isNeutral && (
            <path
              d="M 10 100 A 90 90 0 0 1 190 100"
              fill="none"
              stroke={band.color}
              strokeWidth="10"
              strokeLinecap="round"
              strokeDasharray={`${circumference}`}
              strokeDashoffset={strokeDashoffset}
              style={{ transition: "stroke-dashoffset 1s ease-out" }}
            />
          )}
        </svg>
        <div
          style={{
            position: "absolute",
            bottom: "0",
            left: "50%",
            transform: "translateX(-50%)",
            fontFamily: "'Syne', 'DM Sans', sans-serif",
            fontWeight: 800,
            fontSize: "56px",
            color: isNeutral ? "var(--ghost)" : band.color,
            lineHeight: 1,
          }}
        >
          {displayScore}
        </div>
      </div>

      {/* Band label */}
      <span
        style={{
          fontFamily: "'Inter', sans-serif",
          fontWeight: 600,
          fontSize: "14px",
          letterSpacing: "0.06em",
          textTransform: "uppercase",
          color: isNeutral ? "var(--ghost)" : band.color,
          marginTop: "4px",
        }}
      >
        {band.label}
      </span>

      <span
        style={{
          fontFamily: "'Inter', sans-serif",
          fontWeight: 400,
          fontSize: "12px",
          color: "var(--ash)",
          marginTop: "6px",
        }}
      >
        Greenwash Credibility Score
      </span>
    </div>
  );
}
