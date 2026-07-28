import { motion } from "framer-motion";

interface VerdictStampProps {
  score: number;
}

function getVerdict(score: number): { label: string; color: string; borderColor: string; emoji: string } {
  if (score <= 30) return { label: "MISLEADING", color: "var(--flag-red)", borderColor: "rgba(240,68,82,0.6)", emoji: "❌" };
  if (score <= 60) return { label: "VAGUE", color: "var(--flag-amber)", borderColor: "rgba(240,169,55,0.6)", emoji: "⚠️" };
  return { label: "CREDIBLE", color: "var(--leaf)", borderColor: "rgba(61,220,132,0.6)", emoji: "✅" };
}

export function VerdictStamp({ score }: VerdictStampProps) {
  const verdict = getVerdict(score);

  return (
    <motion.div
      initial={{ scale: 0, rotate: -20, opacity: 0 }}
      animate={{ scale: 1, rotate: -12, opacity: 1 }}
      transition={{ type: "spring", stiffness: 200, damping: 15, delay: 0.6 }}
      style={{
        position: "absolute",
        top: "20px",
        right: "clamp(8px, 5%, 60px)",
        zIndex: 10,
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "6px",
          padding: "8px 16px",
          borderRadius: "4px",
          border: `3px solid ${verdict.borderColor}`,
          background: "rgba(10, 18, 14, 0.85)",
          backdropFilter: "blur(4px)",
          boxShadow: `0 0 20px ${verdict.borderColor}, inset 0 0 20px rgba(0,0,0,0.3)`,
          transform: "rotate(-12deg)",
        }}
      >
        <span style={{ fontSize: "16px" }}>{verdict.emoji}</span>
        <span
          style={{
            fontFamily: "'Syne', 'DM Sans', sans-serif",
            fontSize: "clamp(14px, 2.5vw, 18px)",
            fontWeight: 800,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            color: verdict.color,
            textShadow: `0 0 10px ${verdict.borderColor}`,
          }}
        >
          {verdict.label}
        </span>
      </div>
    </motion.div>
  );
}
