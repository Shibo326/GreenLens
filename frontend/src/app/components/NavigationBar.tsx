import { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router";
import { Zap, Menu, X } from "lucide-react";

function useScrollToHowItWorks() {
  const navigate = useNavigate();
  const location = useLocation();

  return () => {
    const el = document.getElementById("how-it-works");
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    } else if (location.pathname !== "/") {
      // Navigate to landing page first, then scroll after render
      navigate("/");
      setTimeout(() => {
        const target = document.getElementById("how-it-works");
        if (target) {
          target.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      }, 300);
    }
  };
}

interface NavigationBarProps {
  showDemo?: boolean;
}

export function NavigationBar({ showDemo = true }: NavigationBarProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const scrollToHowItWorks = useScrollToHowItWorks();

  return (
    <>
      <nav
        className="w-full flex items-center justify-between safe-top"
        style={{
          background: "rgba(8, 13, 26, 0.72)",
          backdropFilter: "blur(16px) saturate(180%)",
          WebkitBackdropFilter: "blur(16px) saturate(180%)",
          height: "60px",
          paddingLeft: "clamp(16px, 4vw, 40px)",
          paddingRight: "clamp(16px, 4vw, 40px)",
          borderBottom: "1px solid rgba(59, 123, 246, 0.08)",
          position: "sticky",
          top: 0,
          zIndex: 50,
          boxShadow: "0 4px 30px rgba(0, 0, 0, 0.15)",
        }}
      >
        {/* Logo */}
        <div className="flex items-center gap-4">
          <Link to="/" className="flex items-center" style={{ gap: "9px" }}>
            <span
              aria-hidden="true"
              style={{
                width: "14px",
                height: "14px",
                background: "var(--leaf)",
                borderRadius: "2px",
                transform: "rotate(45deg)",
                display: "inline-block",
                flexShrink: 0,
              }}
            />
            <span style={{ display: "inline-flex", marginLeft: "9px" }}>
              <span
                style={{
                  fontFamily: "'Syne', 'DM Sans', sans-serif",
                  fontSize: "clamp(18px, 3vw, 22px)",
                  color: "var(--paper)",
                  fontWeight: 700,
                  letterSpacing: "-0.02em",
                }}
              >
                Green
              </span>
              <span
                style={{
                  fontFamily: "'Syne', 'DM Sans', sans-serif",
                  fontSize: "clamp(18px, 3vw, 22px)",
                  color: "var(--leaf)",
                  fontWeight: 700,
                  letterSpacing: "-0.02em",
                }}
              >
                Lens
              </span>
            </span>
          </Link>

          {/* Nav links (desktop only) */}
          <div className="hidden sm:flex items-center">
            <button
              onClick={scrollToHowItWorks}
              style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: "14px",
                fontWeight: 500,
                color: "var(--ash)",
                background: "none",
                border: "none",
                cursor: "pointer",
                padding: 0,
              }}
              onMouseOver={(e) => {
                e.currentTarget.style.color = "var(--paper)";
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.color = "var(--ash)";
              }}
            >
              How it works
            </button>
          </div>
        </div>

        {/* Desktop buttons */}
        {showDemo && (
          <div className="hidden sm:flex items-center gap-3">
            <AMDBadge />
            <Link to="/demo">
              <button
                className="px-4 py-2 h-9 rounded-lg border transition-all"
                style={{
                  background: "transparent",
                  borderColor: "var(--rule)",
                  color: "var(--ash)",
                  fontFamily: "'Inter', sans-serif",
                  fontSize: "14px",
                  fontWeight: 500,
                  borderRadius: "var(--radius-btn)",
                }}
                onMouseOver={(e) => {
                  e.currentTarget.style.borderColor = "var(--volt-border)";
                  e.currentTarget.style.color = "var(--paper)";
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.borderColor = "var(--rule)";
                  e.currentTarget.style.color = "var(--ash)";
                }}
              >
                Try Demo
              </button>
            </Link>
          </div>
        )}

        {/* Mobile: logo + AMD badge only, plus hamburger */}
        {showDemo && (
          <div className="sm:hidden flex items-center gap-2">
            <AMDBadge />
            <button
              className="flex items-center justify-center"
              onClick={() => setMenuOpen(!menuOpen)}
              style={{
                background: "none",
                border: "none",
                cursor: "pointer",
                color: "var(--paper)",
                padding: "8px",
              }}
              aria-label="Toggle menu"
            >
              {menuOpen ? <X size={22} /> : <Menu size={22} />}
            </button>
          </div>
        )}
      </nav>

      {/* Mobile dropdown menu */}
      {showDemo && menuOpen && (
        <div
          className="sm:hidden animate-slideDown"
          style={{
            position: "fixed",
            top: "60px",
            left: 0,
            right: 0,
            background: "rgba(12, 14, 20, 0.98)",
            borderBottom: "1px solid var(--rule)",
            padding: "16px",
            zIndex: 49,
            display: "flex",
            flexDirection: "column",
            gap: "10px",
          }}
        >
          <button
            onClick={() => { scrollToHowItWorks(); setMenuOpen(false); }}
            className="w-full px-4 py-3 rounded-lg border text-left"
            style={{
              background: "transparent",
              borderColor: "var(--rule)",
              color: "var(--ash)",
              fontFamily: "'Inter', sans-serif",
              fontSize: "15px",
              fontWeight: 500,
              cursor: "pointer",
              borderRadius: "var(--radius-btn)",
            }}
          >
            How it works
          </button>
          <Link to="/demo" onClick={() => setMenuOpen(false)}>
            <button
              className="w-full px-4 py-3 rounded-lg border"
              style={{
                background: "transparent",
                borderColor: "var(--rule)",
                color: "var(--ash)",
                fontFamily: "'Inter', sans-serif",
                fontSize: "15px",
                fontWeight: 500,
                cursor: "pointer",
                borderRadius: "var(--radius-btn)",
              }}
            >
              Try Demo
            </button>
          </Link>
        </div>
      )}
    </>
  );
}

export function AMDBadge() {
  return (
    <div
      className="flex items-center gap-1.5 px-3 py-1.5 rounded-full"
      style={{
        background: "rgba(237, 28, 36, 0.08)",
        border: "1px solid rgba(237, 28, 36, 0.20)",
        height: "26px",
      }}
    >
      <Zap size={12} style={{ color: "var(--amd-signal)" }} />
      <span
        style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: "12px",
          color: "var(--amd-signal)",
          fontWeight: 500,
          lineHeight: "16px",
          whiteSpace: "nowrap",
        }}
      >
        AMD MI300X
      </span>
    </div>
  );
}
