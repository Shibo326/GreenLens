import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Leaf } from "lucide-react";

const STORAGE_KEY = "greenlens_onboarding_seen";

const steps = [
  {
    icon: <Leaf size={48} style={{ color: "var(--leaf)" }} />,
    title: "Hi! I'm GreenLens",
    body: "I detect greenwashing in company documents — catching the gap between what companies CLAIM and what their data SHOWS.",
  },
  {
    icon: <span style={{ fontSize: "42px" }}>📄📸</span>,
    title: "Upload or Snap",
    body: "Upload a sustainability report, ESG document, or marketing material. On mobile, you can photograph a product label directly with your camera.",
  },
  {
    icon: <span style={{ fontSize: "42px" }}>✅🔍</span>,
    title: "Get Your Verdict",
    body: "In under 90 seconds, I'll give you a Greenwash Score (0-100), flag misleading claims, and tell you exactly what's real vs. marketing.",
  },
];

export function OnboardingOverlay() {
  const [visible, setVisible] = useState(false);
  const [step, setStep] = useState(0);

  useEffect(() => {
    const seen = localStorage.getItem(STORAGE_KEY);
    if (seen !== "true") {
      setVisible(true);
    }
  }, []);

  // Lock body scroll when overlay is visible and scroll to top
  useEffect(() => {
    if (visible) {
      document.body.style.overflow = "hidden";
      window.scrollTo(0, 0);
    } else {
      document.body.style.overflow = "";
    }
    return () => { document.body.style.overflow = ""; };
  }, [visible]);

  const dismiss = () => {
    localStorage.setItem(STORAGE_KEY, "true");
    setVisible(false);
  };

  const handleNext = () => {
    if (step < steps.length - 1) {
      setStep(step + 1);
    } else {
      dismiss();
    }
  };

  if (!visible) return null;

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 9999,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "rgba(0,0,0,0.7)",
            padding: "16px",
          }}
          onClick={dismiss}
          role="dialog"
          aria-modal="true"
          aria-label="Welcome to GreenLens onboarding"
        >
          <motion.div
            initial={{ opacity: 0, y: 30, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
            onClick={(e) => e.stopPropagation()}
            style={{
              background: "var(--lead)",
              border: "1px solid var(--leaf-border)",
              borderRadius: "16px",
              maxWidth: "420px",
              width: "100%",
              padding: "32px",
              position: "relative",
            }}
          >
            {/* Close button */}
            <button
              onClick={dismiss}
              aria-label="Close onboarding"
              style={{
                position: "absolute",
                top: "12px",
                right: "12px",
                background: "none",
                border: "none",
                color: "var(--ghost)",
                fontSize: "20px",
                cursor: "pointer",
                padding: "4px 8px",
                lineHeight: 1,
              }}
            >
              ✕
            </button>

            {/* Step content */}
            <AnimatePresence mode="wait">
              <motion.div
                key={step}
                initial={{ opacity: 0, x: 40 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -40 }}
                transition={{ duration: 0.25 }}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  textAlign: "center",
                }}
              >
                {/* Icon */}
                <div style={{ marginBottom: "20px" }}>{steps[step].icon}</div>

                {/* Title */}
                <h2
                  style={{
                    fontFamily: "'Syne', 'DM Sans', sans-serif",
                    fontWeight: 700,
                    fontSize: "22px",
                    color: "var(--paper)",
                    marginBottom: "12px",
                  }}
                >
                  {steps[step].title}
                </h2>

                {/* Body */}
                <p
                  style={{
                    fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
                    fontWeight: 400,
                    fontSize: "15px",
                    lineHeight: 1.6,
                    color: "var(--ash)",
                    marginBottom: "24px",
                    maxWidth: "340px",
                  }}
                >
                  {steps[step].body}
                </p>
              </motion.div>
            </AnimatePresence>

            {/* Dot indicators */}
            <div
              style={{
                display: "flex",
                justifyContent: "center",
                gap: "8px",
                marginBottom: "20px",
              }}
            >
              {steps.map((_, i) => (
                <div
                  key={i}
                  style={{
                    width: i === step ? "24px" : "8px",
                    height: "8px",
                    borderRadius: "100px",
                    background: i === step ? "var(--leaf)" : "var(--rule)",
                    transition: "all 0.3s ease",
                  }}
                />
              ))}
            </div>

            {/* Button */}
            <button
              onClick={handleNext}
              style={{
                width: "100%",
                height: "48px",
                borderRadius: "var(--radius-btn)",
                background: "var(--leaf)",
                color: "var(--ink)",
                border: "none",
                fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
                fontSize: "15px",
                fontWeight: 600,
                cursor: "pointer",
                transition: "all 0.2s ease",
                boxShadow: "0 0 20px rgba(61, 220, 132, 0.25)",
              }}
              onMouseOver={(e) => {
                e.currentTarget.style.filter = "brightness(1.1)";
                e.currentTarget.style.boxShadow =
                  "0 0 32px rgba(61, 220, 132, 0.4)";
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.filter = "brightness(1)";
                e.currentTarget.style.boxShadow =
                  "0 0 20px rgba(61, 220, 132, 0.25)";
              }}
            >
              {step < steps.length - 1 ? "Next →" : "Start Scanning →"}
            </button>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
