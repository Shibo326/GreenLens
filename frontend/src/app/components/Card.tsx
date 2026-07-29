import { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  style?: React.CSSProperties;
  hoverable?: boolean;
}

export function Card({ children, className = '', style = {}, hoverable = true }: CardProps) {
  return (
    <div
      className={`rounded p-6 ${hoverable ? 'premium-card' : ''} ${className}`}
      style={{
        background: 'var(--lead)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        border: '1px solid var(--rule)',
        borderRadius: '16px',
        ...style,
      }}
    >
      {children}
    </div>
  );
}
