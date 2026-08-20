import React from 'react';

interface MetricCardProps {
  label: string;
  value: number | string;
  subtext?: string;
  icon: React.ReactNode;
  color?: string;
  highlight?: boolean;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  subtext,
  icon,
  color = 'var(--primary)',
  highlight = false,
}) => {
  return (
    <div
      className="metric-card"
      style={{
        borderColor: highlight ? color : 'var(--border-subtle)',
        boxShadow: highlight ? `0 0 16px ${color}20` : undefined,
      }}
    >
      <div className="metric-header">
        <span>{label}</span>
        <div
          className="metric-icon-box"
          style={{ background: `${color}18`, color: color }}
        >
          {icon}
        </div>
      </div>
      <div className="metric-value">{value}</div>
      {subtext && <div className="metric-footer">{subtext}</div>}
    </div>
  );
};
