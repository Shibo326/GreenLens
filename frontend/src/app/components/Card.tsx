import { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  style?: React.CSSProperties;
  hoverable?: boolean;
}

export function Card({ children, className = '', style = {}, hoverable = true }: CardProps) {
  const originalBorder = (style.border as string | undefined) ?? '1px solid var(--rule)';

  return (
    <div
      className={`rounded p-6 ${className}`}
      style={{
        background: 'var(--lead)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        border: originalBorder,
        borderRadius: 'var(--radius-card)',
        transition: hoverable ? 'border-color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease' : undefined,
        ...style,
      }}
      onMouseOver={(e) => {
        if (hoverable) {
          e.currentTarget.style.borderColor = 'var(--leaf-border)';
          e.currentTarget.style.transform = 'translateY(-2px)';
          e.currentTarget.style.boxShadow = '0 8px 32px rgba(61, 220, 132, 0.08)';
        }
      }}
      onMouseOut={(e) => {
        if (hoverable) {
          const match = originalBorder.match(/1px solid (.+)/);
          e.currentTarget.style.borderColor = match ? match[1] : 'var(--rule)';
          e.currentTarget.style.transform = 'translateY(0)';
          e.currentTarget.style.boxShadow = 'none';
        }
      }}
    >
      {children}
    </div>
  );
}
