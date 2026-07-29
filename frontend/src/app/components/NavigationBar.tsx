import { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router";
import { Menu, X, Leaf, Zap } from "lucide-react";

function useScrollToHowItWorks() {
  const navigate = useNavigate();
  const location = useLocation();

  return () => {
    const el = document.getElementById("how-it-works");
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    } else if (location.pathname !== "/") {
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
          background: "rgba(10, 18, 14, 0.85)",
          backdropFilter: "blur(16px) saturate(180%)",
          WebkitBackdropFilter: "blur(16px) saturate(180%)",
          height: "52px",
          paddingLeft: "clamp(16px, 4vw, 40px)",
          paddingRight: "clamp(16px, 4vw, 40px)",
          borderBottom: "1px solid rgba(61, 220, 132, 0.08)",
          position: "sticky",
          top: 0,
          zIndex: 50,
          boxShadow: "0 1px 12px rgba(0, 0, 0, 0.2)",
        }}
        role="navigation"
        aria-label="Main navigation"
      >
        {/* Logo */}
        <div className="flex items-center gap-6">
          <Link to="/" className="flex items-center gap-2" aria-label="GreenLens home">
            <Leaf size={18} style={{ color: "var(--leaf)" }} aria-hidden="true" />
            <span
              style={{
                fontFamily: "'Syne', 'DM Sans', sans-serif",
                fontSize: "18px",
                color: "var(--paper)",
                fontWeight: 700,
                letterSpacing: "-0.02em",
              }}
            >
              Green<span style={{ color: "var(--leaf)" }}>Lens</span>
            </span>
          </Link>

          {/* Nav links (desktop only) */}
          <div className="hidden sm:flex items-center gap-5">
            <button
              onClick={scrollToHowItWorks}
              style={{
                fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
                fontSize: "13px",
                fontWeight: 500,
                color: "var(--ash)",
                background: "none",
                border: "none",
                cursor: "pointer",
                padding: "4px 0",
                position: "relative",
                transition: "color 0.15s",
              }}
              onMouseOver={(e) => {
                e.currentTarget.style.color = "var(--paper)";
                e.currentTarget.style.textDecoration = "underline";
                e.currentTarget.style.textUnderlineOffset = "4px";
                e.currentTarget.style.textDecorationColor = "var(--leaf)";
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.color = "var(--ash)";
                e.currentTarget.style.textDecoration = "none";
              }}
            >
              How it works
            </button>
            <Link
              to="/learn"
              style={{
                fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
                fontSize: "13px",
                fontWeight: 500,
                color: "var(--ash)",
                textDecoration: "none",
                padding: "4px 0",
                transition: "color 0.15s",
              }}
              onMouseOver={(e) => {
                e.currentTarget.style.color = "var(--paper)";
                e.currentTarget.style.textDecoration = "underline";
                e.currentTarget.style.textUnderlineOffset = "4px";
                e.currentTarget.style.textDecorationColor = "var(--leaf)";
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.color = "var(--ash)";
                e.currentTarget.style.textDecoration = "none";
              }}
            >
              Learn
            </Link>
          </div>
        </div>

        {/* Desktop buttons */}
        {showDemo && (
          <div className="hidden sm:flex items-center gap-3">
            <Link to="/demo">
              <button
                className="px-4 py-1.5 rounded-lg border transition-all"
                style={{
                  background: "transparent",
                  borderColor: "var(--rule)",
                  color: "var(--ash)",
                  fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
                  fontSize: "13px",
                  fontWeight: 500,
                  borderRadius: "var(--radius-btn)",
                  height: "32px",
                }}
                onMouseOver={(e) => {
                  e.currentTarget.style.borderColor = "var(--leaf-border)";
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

        {/* Mobile hamburger */}
        {showDemo && (
          <div className="sm:hidden flex items-center gap-2">
            <button
              className="flex items-center justify-center"
              onClick={() => setMenuOpen(!menuOpen)}
              style={{
                background: "none",
                border: "none",
                cursor: "pointer",
                color: "var(--paper)",
                padding: "8px",
                minWidth: "44px",
                minHeight: "44px",
              }}
              aria-label={menuOpen ? "Close menu" : "Open menu"}
              aria-expanded={menuOpen}
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
            top: "52px",
            left: 0,
            right: 0,
            background: "rgba(10, 18, 14, 0.98)",
            backdropFilter: "blur(16px)",
            WebkitBackdropFilter: "blur(16px)",
            borderBottom: "1px solid var(--rule)",
            padding: "16px",
            zIndex: 49,
            display: "flex",
            flexDirection: "column",
            gap: "10px",
          }}
          role="menu"
        >
          <button
            onClick={() => { scrollToHowItWorks(); setMenuOpen(false); }}
            className="w-full px-4 py-3 rounded-lg border text-left"
            style={{
              background: "transparent",
              borderColor: "var(--rule)",
              color: "var(--ash)",
              fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
              fontSize: "15px",
              fontWeight: 500,
              cursor: "pointer",
              borderRadius: "var(--radius-btn)",
              minHeight: "44px",
            }}
            role="menuitem"
          >
            How it works
          </button>
          <Link to="/learn" onClick={() => setMenuOpen(false)}>
            <button
              className="w-full px-4 py-3 rounded-lg border"
              style={{
                background: "transparent",
                borderColor: "var(--rule)",
                color: "var(--ash)",
                fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
                fontSize: "15px",
                fontWeight: 500,
                cursor: "pointer",
                borderRadius: "var(--radius-btn)",
                minHeight: "44px",
              }}
              role="menuitem"
            >
              Learn
            </button>
          </Link>
          <Link to="/demo" onClick={() => setMenuOpen(false)}>
            <button
              className="w-full px-4 py-3 rounded-lg border"
              style={{
                background: "transparent",
                borderColor: "var(--rule)",
                color: "var(--ash)",
                fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
                fontSize: "15px",
                fontWeight: 500,
                cursor: "pointer",
                borderRadius: "var(--radius-btn)",
                minHeight: "44px",
              }}
              role="menuitem"
            >
              Try Demo
            </button>
          </Link>
        </div>
      )}
    </>
  );
}

// NOTE: AMDBadge is intentionally NOT rendered in the NavigationBar (AMD branding
// removed from the nav). It remains exported so pages that explicitly want to show
// a subtle "Powered by AMD MI300X" pill can still import and render it themselves.
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
      <Zap size={12} style={{ color: "var(--amd-signal)" }} aria-hidden="true" />
      <span
        style={{
          fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
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
