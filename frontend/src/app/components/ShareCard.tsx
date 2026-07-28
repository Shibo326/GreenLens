import { useState, useRef } from "react";
import { Share2, Check, Leaf } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface ShareCardProps {
  score: number;
  misleadingCount: number;
  vagueCount: number;
  unverifiedCount: number;
  documentNames: string[];
}

function getVerdict(score: number): { label: string; color: string } {
  if (score <= 30) return { label: "HIGH GREENWASH RISK", color: "#F04452" };
  if (score <= 60) return { label: "MIXED SIGNALS", color: "#F0A937" };
  return { label: "CREDIBLE CLAIMS", color: "#3DDC84" };
}

export function ShareCard({ score, misleadingCount, vagueCount, unverifiedCount, documentNames }: ShareCardProps) {
  const [showCard, setShowCard] = useState(false);
  const [copied, setCopied] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);

  const verdict = getVerdict(score);
  const totalFlags = misleadingCount + vagueCount + unverifiedCount;
  const companyHint = documentNames[0]?.replace(/[._-]/g, " ").replace(/\.(pdf|png|jpg|jpeg)$/i, "").slice(0, 30) || "Documents";

  const handleCopyText = () => {
    const text = `🌱 GreenLens Report Card\n\n📊 Greenwash Score: ${score}/100\n🏷️ Verdict: ${verdict.label}\n🚩 ${totalFlags} flags found (${misleadingCount} misleading, ${vagueCount} vague, ${unverifiedCount} unverified)\n📄 Analyzed: ${companyHint}\n\n🔗 Try it: greenlens.app\n#GreenLens #Greenwashing #Sustainability`;
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <>
      <button
        onClick={() => setShowCard(true)}
        className="flex items-center gap-2 px-4 py-2 rounded-lg transition-all"
        style={{
          background: "var(--leaf-dim)",
          border: "1px solid var(--leaf-border)",
          color: "var(--leaf)",
          fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
          fontSize: "13px",
          fontWeight: 600,
          cursor: "pointer",
        }}
        onMouseOver={(e) => { e.currentTarget.style.background = "rgba(61,220,132,0.15)"; }}
        onMouseOut={(e) => { e.currentTarget.style.background = "var(--leaf-dim)"; }}
      >
        <Share2 size={14} />
        Share Report Card
      </button>

      {/* Modal */}
      <AnimatePresence>
        {showCard && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            style={{ background: "rgba(0,0,0,0.75)" }}
            onClick={() => setShowCard(false)}
          >
            <motion.div
              initial={{ scale: 0.85, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.85, opacity: 0 }}
              transition={{ type: "spring", stiffness: 300, damping: 25 }}
              onClick={(e) => e.stopPropagation()}
              className="flex flex-col items-center gap-4"
              style={{ maxWidth: "400px", width: "100%" }}
            >
              {/* The card itself */}
              <div
                ref={cardRef}
                style={{
                  width: "100%",
                  background: "linear-gradient(145deg, #0A120E 0%, #131F19 50%, #0A120E 100%)",
                  borderRadius: "20px",
                  padding: "32px",
                  border: `2px solid ${verdict.color}44`,
                  boxShadow: `0 0 60px ${verdict.color}22, 0 20px 40px rgba(0,0,0,0.5)`,
                  position: "relative",
                  overflow: "hidden",
                }}
              >
                {/* Background decoration */}
                <div style={{ position: "absolute", inset: 0, background: `radial-gradient(circle at 80% 20%, ${verdict.color}08 0%, transparent 50%)`, pointerEvents: "none" }} />

                {/* Logo */}
                <div className="flex items-center gap-2 mb-6" style={{ position: "relative" }}>
                  <Leaf size={16} style={{ color: "#3DDC84" }} />
                  <span style={{ fontFamily: "'Syne', 'DM Sans', sans-serif", fontSize: "16px", fontWeight: 700, color: "#F3F0E6" }}>
                    Green<span style={{ color: "#3DDC84" }}>Lens</span>
                  </span>
                  <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: "10px", color: "#4E6157", marginLeft: "auto" }}>REPORT CARD</span>
                </div>

                {/* Score */}
                <div className="text-center mb-4" style={{ position: "relative" }}>
                  <div style={{ fontFamily: "'Syne', 'DM Sans', sans-serif", fontSize: "72px", fontWeight: 800, color: verdict.color, lineHeight: 1 }}>
                    {score}
                  </div>
                  <div style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "12px", color: "#9BAFA3", marginTop: "4px" }}>
                    CREDIBILITY SCORE
                  </div>
                </div>

                {/* Verdict badge */}
                <div className="flex justify-center mb-5">
                  <div
                    style={{
                      padding: "6px 16px",
                      borderRadius: "100px",
                      background: `${verdict.color}18`,
                      border: `1px solid ${verdict.color}44`,
                      fontFamily: "'IBM Plex Sans', sans-serif",
                      fontSize: "12px",
                      fontWeight: 700,
                      letterSpacing: "0.08em",
                      color: verdict.color,
                    }}
                  >
                    {verdict.label}
                  </div>
                </div>

                {/* Stats */}
                <div className="flex justify-between px-2 mb-5" style={{ borderTop: "1px solid #24352C", paddingTop: "16px" }}>
                  <div className="text-center">
                    <div style={{ fontFamily: "'Syne', 'DM Sans', sans-serif", fontSize: "20px", fontWeight: 700, color: "#F04452" }}>{misleadingCount}</div>
                    <div style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "10px", color: "#4E6157" }}>MISLEADING</div>
                  </div>
                  <div className="text-center">
                    <div style={{ fontFamily: "'Syne', 'DM Sans', sans-serif", fontSize: "20px", fontWeight: 700, color: "#F0A937" }}>{vagueCount}</div>
                    <div style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "10px", color: "#4E6157" }}>VAGUE</div>
                  </div>
                  <div className="text-center">
                    <div style={{ fontFamily: "'Syne', 'DM Sans', sans-serif", fontSize: "20px", fontWeight: 700, color: "#5FA8D3" }}>{unverifiedCount}</div>
                    <div style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "10px", color: "#4E6157" }}>UNVERIFIED</div>
                  </div>
                </div>

                {/* Document name */}
                <div style={{ fontFamily: "'IBM Plex Sans', sans-serif", fontSize: "12px", color: "#9BAFA3", textAlign: "center" }}>
                  📄 {companyHint}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-center gap-1.5 mt-4 pt-4" style={{ borderTop: "1px solid #24352C" }}>
                  <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: "10px", color: "#4E6157" }}>
                    Analyzed by GreenLens AI · AMD MI300X
                  </span>
                </div>
              </div>

              {/* Action buttons */}
              <div className="flex items-center gap-3">
                <button
                  onClick={handleCopyText}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-lg"
                  style={{ background: "var(--leaf)", border: "none", color: "var(--ink)", fontFamily: "'IBM Plex Sans', sans-serif", fontSize: "14px", fontWeight: 600, cursor: "pointer" }}
                >
                  {copied ? <><Check size={14} /> Copied!</> : <><Share2 size={14} /> Copy to Share</>}
                </button>
                <button
                  onClick={() => setShowCard(false)}
                  className="px-5 py-2.5 rounded-lg"
                  style={{ background: "var(--graphite)", border: "1px solid var(--rule)", color: "var(--ash)", fontFamily: "'IBM Plex Sans', sans-serif", fontSize: "14px", fontWeight: 500, cursor: "pointer" }}
                >
                  Close
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
