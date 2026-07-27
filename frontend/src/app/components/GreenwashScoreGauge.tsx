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
  const band = isNeutral ? { label: "Awaiting Data", color: "var(--ghost)", dimColor: "rgba(78,97,87,0.08)" } : getBand(score!);

  // Arc progress: 0-100 maps to 0-180 degrees (semicircle)
  const progress = isNeutral ? 0 : Math.min(100, Math.max(0, score!));
  const circumference = Math.PI * 80; // radius 80 semicircle
  const strokeDashoffset = circumference - (progress / 100) * circumference;

  return (
    <div
      className="flex flex-col items-center justify-center rounded-xl p-6"
      style={{
        background: band.dimColor,
        border: `1px solid ${isNeutral ? "var(--rule)" : band.color}`,
        borderColor: isNeutral ? "var(--rule)" : `${band.color}44`,
      }}
    >
      {/* SVG Arc */}
      <div className="relative" style={{ width: "180px", height: "100px", marginBottom: "8px" }}>
        <svg
          viewBox="0 0 180 100"
          width="180"
          height="100"
          style={{ overflow: "visible" }}
        >
          {/* Background arc */}
          <path
            d="M 10 90 A 80 80 0 0 1 170 90"
            fill="none"
            stroke="var(--rule)"
            strokeWidth="8"
            strokeLinecap="round"
          />
          {/* Progress arc */}
          {!isNeutral && (
            <path
              d="M 10 90 A 80 80 0 0 1 170 90"
              fill="none"
              stroke={band.color}
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={`${circumference}`}
              strokeDashoffset={strokeDashoffset}
              style={{ transition: "stroke-dashoffset 1s ease-out" }}
            />
          )}
        </svg>
        {/* Score numeral centered */}
        <div
          style={{
            position: "absolute",
            bottom: "0",
            left: "50%",
            transform: "translateX(-50%)",
            fontFamily: "'Syne', 'DM Sans', sans-serif",
            fontWeight: 800,
            fontSize: "48px",
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
          fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
          fontWeight: 600,
          fontSize: "13px",
          letterSpacing: "0.06em",
          textTransform: "uppercase",
          color: isNeutral ? "var(--ghost)" : band.color,
          marginTop: "4px",
        }}
      >
        {band.label}
      </span>

      {/* Subtitle */}
      <span
        style={{
          fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
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
