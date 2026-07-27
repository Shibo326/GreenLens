import { ButtonHTMLAttributes } from 'react';

interface PrimaryButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
  small?: boolean;
}

export function PrimaryButton({ children, small = false, disabled, ...props }: PrimaryButtonProps) {
  return (
    <button
      className="transition-all"
      disabled={disabled}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '6px',
        background: disabled ? 'var(--graphite)' : 'var(--leaf)',
        color: disabled ? 'var(--ghost)' : 'var(--ink)',
        borderRadius: 'var(--radius-btn)',
        fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
        fontSize: small ? '13px' : '14px',
        fontWeight: 600,
        lineHeight: '20px',
        padding: small ? '8px 14px' : '12px 24px',
        height: small ? '36px' : '44px',
        border: 'none',
        boxShadow: disabled ? 'none' : '0 0 20px rgba(61, 220, 132, 0.2)',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        filter: 'brightness(1)',
        transition: 'all 0.2s ease',
        whiteSpace: 'nowrap',
      }}
      onMouseOver={(e) => {
        if (!disabled) {
          e.currentTarget.style.background = 'var(--leaf)';
          e.currentTarget.style.filter = 'brightness(1.1)';
          e.currentTarget.style.boxShadow = '0 0 32px rgba(61, 220, 132, 0.4), 0 4px 16px rgba(61, 220, 132, 0.15)';
          e.currentTarget.style.transform = 'translateY(-1px)';
        }
      }}
      onMouseOut={(e) => {
        if (!disabled) {
          e.currentTarget.style.background = 'var(--leaf)';
          e.currentTarget.style.filter = 'brightness(1)';
          e.currentTarget.style.boxShadow = '0 0 20px rgba(61, 220, 132, 0.2)';
          e.currentTarget.style.transform = 'translateY(0)';
        }
      }}
      {...props}
    >
      {children}
    </button>
  );
}

interface GhostButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
  small?: boolean;
}

export function GhostButton({ children, small = false, disabled, ...props }: GhostButtonProps) {
  return (
    <button
      className="border transition-all"
      disabled={disabled}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '6px',
        background: 'transparent',
        borderRadius: 'var(--radius-btn)',
        borderColor: 'var(--rule)',
        color: 'var(--ash)',
        fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
        fontSize: small ? '13px' : '14px',
        fontWeight: 500,
        lineHeight: '20px',
        padding: small ? '8px 12px' : '12px 24px',
        height: small ? '36px' : '44px',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        transition: 'all 0.2s ease',
        whiteSpace: 'nowrap',
      }}
      onMouseOver={(e) => {
        if (!disabled) {
          e.currentTarget.style.borderColor = 'var(--leaf-border)';
          e.currentTarget.style.color = 'var(--paper)';
        }
      }}
      onMouseOut={(e) => {
        if (!disabled) {
          e.currentTarget.style.borderColor = 'var(--rule)';
          e.currentTarget.style.color = 'var(--ash)';
        }
      }}
      {...props}
    >
      {children}
    </button>
  );
}
