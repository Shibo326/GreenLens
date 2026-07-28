import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

const CLAIMS = [
  {
    text: "Our packaging is 100% recycled and carbon neutral.",
    highlights: [
      { word: "100%", color: "var(--flag-red)", label: "Misleading" },
      { word: "recycled", color: "var(--flag-amber)", label: "Vague" },
      { word: "carbon neutral", color: "var(--flag-red)", label: "Unverified" },
    ],
  },
  {
    text: "We've eliminated our carbon footprint entirely by 2025.",
    highlights: [
      { word: "eliminated", color: "var(--flag-red)", label: "Misleading" },
      { word: "carbon footprint", color: "var(--flag-amber)", label: "Scope?" },
      { word: "entirely", color: "var(--flag-red)", label: "No proof" },
    ],
  },
  {
    text: "Made with eco-friendly sustainable natural materials.",
    highlights: [
      { word: "eco-friendly", color: "var(--flag-amber)", label: "Vague" },
      { word: "sustainable", color: "var(--flag-amber)", label: "Undefined" },
      { word: "natural", color: "var(--flag-amber)", label: "Meaningless" },
    ],
  },
];

export function ClaimDissection() {
  const [claimIndex, setClaimIndex] = useState(0);
  const [phase, setPhase] = useState<"typing" | "highlighting" | "done">("typing");
  const [typedChars, setTypedChars] = useState(0);
  const [activeHighlight, setActiveHighlight] = useState(-1);

  const claim = CLAIMS[claimIndex];

  // Auto-cycle through claims
  useEffect(() => {
    setPhase("typing");
    setTypedChars(0);
    setActiveHighlight(-1);
  }, [claimIndex]);

  // Typing animation
  useEffect(() => {
    if (phase !== "typing") return;
    if (typedChars >= claim.text.length) {
      setTimeout(() => setPhase("highlighting"), 400);
      return;
    }
    const timer = setTimeout(() => setTypedChars((c) => c + 1), 30);
    return () => clearTimeout(timer);
  }, [phase, typedChars, claim.text.length]);

  // Highlighting animation
  useEffect(() => {
    if (phase !== "highlighting") return;
    if (activeHighlight >= claim.highlights.length - 1) {
      setTimeout(() => setPhase("done"), 1200);
      return;
    }
    const timer = setTimeout(() => setActiveHighlight((h) => h + 1), 600);
    return () => clearTimeout(timer);
  }, [phase, activeHighlight, claim.highlights.length]);

  // Move to next claim after done
  useEffect(() => {
    if (phase !== "done") return;
    const timer = setTimeout(() => {
      setClaimIndex((i) => (i + 1) % CLAIMS.length);
    }, 2500);
    return () => clearTimeout(timer);
  }, [phase]);

  // Render text with highlights
  const renderText = () => {
    if (phase === "typing") {
      return (
        <span style={{ color: "var(--paper)" }}>
          {claim.text.slice(0, typedChars)}
          <span style={{ display: "inline-block", width: "2px", height: "1.1em", background: "var(--leaf)", marginLeft: "1px", verticalAlign: "text-bottom", animation: "blink 1s step-end infinite" }} />
        </span>
      );
    }

    let result = claim.text;
    const parts: { text: string; highlight?: (typeof claim.highlights)[0]; isHighlighted: boolean }[] = [];
    let lastIndex = 0;

    // Sort highlights by position in text
    const sortedHighlights = [...claim.highlights].sort(
      (a, b) => result.indexOf(a.word) - result.indexOf(b.word)
    );

    for (let i = 0; i < sortedHighlights.length; i++) {
      const h = sortedHighlights[i];
      const idx = result.indexOf(h.word, lastIndex);
      if (idx === -1) continue;

      if (idx > lastIndex) {
        parts.push({ text: result.slice(lastIndex, idx), isHighlighted: false });
      }
      parts.push({ text: h.word, highlight: h, isHighlighted: i <= activeHighlight });
      lastIndex = idx + h.word.length;
    }
    if (lastIndex < result.length) {
      parts.push({ text: result.slice(lastIndex), isHighlighted: false });
    }

    return (
      <>
        {parts.map((part, i) => {
          if (!part.highlight) {
            return <span key={i} style={{ color: "var(--paper)" }}>{part.text}</span>;
          }
          return (
            <span key={i} style={{ position: "relative", display: "inline" }}>
              <span
                style={{
                  color: part.isHighlighted ? part.highlight.color : "var(--paper)",
                  background: part.isHighlighted ? `${part.highlight.color}22` : "transparent",
                  borderBottom: part.isHighlighted ? `2px solid ${part.highlight.color}` : "none",
                  padding: part.isHighlighted ? "1px 3px" : "0",
                  borderRadius: "3px",
                  transition: "all 0.3s ease",
                  fontWeight: part.isHighlighted ? 600 : 400,
                }}
              >
                {part.text}
              </span>
              {part.isHighlighted && (
                <motion.span
                  initial={{ opacity: 0, y: 4, scale: 0.8 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  style={{
                    position: "absolute",
                    top: "100%",
                    left: "50%",
                    transform: "translateX(-50%)",
                    marginTop: "4px",
                    fontSize: "10px",
                    fontWeight: 700,
                    letterSpacing: "0.05em",
                    color: part.highlight.color,
                    whiteSpace: "nowrap",
                    pointerEvents: "none",
                  }}
                >
                  {part.highlight.label}
                </motion.span>
              )}
            </span>
          );
        })}
      </>
    );
  };

  return (
    <div
      className="w-full rounded-xl p-6"
      style={{
        maxWidth: "640px",
        background: "var(--lead)",
        border: "1px solid var(--rule)",
        position: "relative",
        overflow: "hidden",
        minHeight: "140px",
      }}
    >
      {/* Scan line effect during highlighting */}
      {phase === "highlighting" && <div className="scan-line" />}

      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: "var(--leaf)", animation: "voltPulse 2s ease-in-out infinite" }} />
        <span style={{ fontFamily: "'IBM Plex Mono', 'JetBrains Mono', monospace", fontSize: "11px", fontWeight: 600, letterSpacing: "0.08em", color: "var(--leaf)", textTransform: "uppercase" }}>
          {phase === "typing" ? "SCANNING CLAIM..." : phase === "highlighting" ? "FLAGGING ISSUES..." : "ANALYSIS COMPLETE"}
        </span>
        <div style={{ flex: 1 }} />
        {/* Claim counter */}
        <div className="flex items-center gap-1">
          {CLAIMS.map((_, i) => (
            <div
              key={i}
              style={{
                width: "6px",
                height: "6px",
                borderRadius: "50%",
                background: i === claimIndex ? "var(--leaf)" : "var(--rule)",
                transition: "background 0.3s",
              }}
            />
          ))}
        </div>
      </div>

      {/* Claim text */}
      <AnimatePresence mode="wait">
        <motion.div
          key={claimIndex}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.3 }}
          style={{
            fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
            fontSize: "17px",
            lineHeight: 2.2,
            color: "var(--paper)",
            minHeight: "60px",
          }}
        >
          "{renderText()}"
        </motion.div>
      </AnimatePresence>

      {/* Bottom status */}
      <div className="flex items-center gap-3 mt-4">
        {phase === "done" && (
          <motion.div
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center gap-2"
          >
            <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--flag-red)", fontFamily: "'IBM Plex Sans', 'Inter', sans-serif" }}>
              {claim.highlights.length} flags detected
            </span>
          </motion.div>
        )}
      </div>
    </div>
  );
}
