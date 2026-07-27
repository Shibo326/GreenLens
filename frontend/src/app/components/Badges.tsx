import { AlertCircle, AlertTriangle, Info, FileText } from "lucide-react";

interface RiskBadgeProps {
  variant: 'HIGH' | 'MEDIUM' | 'LOW';
}

export function RiskBadge({ variant }: RiskBadgeProps) {
  const styles = {
    HIGH: {
      background: 'var(--flag-red-dim)',
      border: '1px solid rgba(240, 68, 82, 0.25)',
      color: 'var(--flag-red)',
      label: 'MISLEADING',
    },
    MEDIUM: {
      background: 'var(--flag-amber-dim)',
      border: '1px solid rgba(240, 169, 55, 0.25)',
      color: 'var(--flag-amber)',
      label: 'VAGUE',
    },
    LOW: {
      background: 'var(--flag-blue-dim)',
      border: '1px solid rgba(95, 168, 211, 0.25)',
      color: 'var(--flag-blue)',
      label: 'UNVERIFIED',
    },
  };

  const icons = {
    HIGH: <AlertCircle size={12} style={{ flexShrink: 0 }} />,
    MEDIUM: <AlertTriangle size={12} style={{ flexShrink: 0 }} />,
    LOW: <Info size={12} style={{ flexShrink: 0 }} />,
  };

  const style = styles[variant];

  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded" style={{
      background: style.background,
      border: style.border,
      color: style.color,
      fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
      fontSize: '11px',
      fontWeight: 600,
      lineHeight: '16px',
      letterSpacing: '0.08em',
      textTransform: 'uppercase'
    }}>
      {icons[variant]}
      {style.label}
    </span>
  );
}

interface EvidenceTagProps {
  filename: string;
}

export function EvidenceTag({ filename }: EvidenceTagProps) {
  return (
    <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md" style={{
      background: 'var(--graphite)',
      border: '1px solid var(--rule)',
      height: '28px'
    }}>
      <FileText size={12} style={{ color: 'var(--ghost)', flexShrink: 0 }} />
      <span style={{
        fontFamily: "'IBM Plex Mono', 'JetBrains Mono', monospace",
        fontSize: '11px',
        color: 'var(--ash)',
        lineHeight: '16px',
        maxWidth: '200px',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
        display: 'inline-block',
      }}>
        {filename}
      </span>
    </div>
  );
}

interface EvidenceBoxProps {
  quote: string;
  className?: string;
  style?: React.CSSProperties;
}

export function EvidenceBox({ quote, className = '', style = {} }: EvidenceBoxProps) {
  return (
    <div
      className={className}
      style={{
        background: 'var(--parchment)',
        color: 'var(--lead)',
        fontFamily: "'IBM Plex Mono', 'JetBrains Mono', monospace",
        fontWeight: 400,
        fontSize: '12px',
        lineHeight: '18px',
        borderRadius: '4px',
        padding: '12px',
        ...style
      }}
    >
      &ldquo;{quote}&rdquo;
    </div>
  );
}
