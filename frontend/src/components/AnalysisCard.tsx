import type { ReactNode } from "react";

interface AnalysisCardProps {
  title: string;
  description: string;
  onClick: () => void;
  icon?: ReactNode;
  disabled?: boolean;
}

export function AnalysisCard({
  title,
  description,
  onClick,
  icon,
  disabled = false,
}: AnalysisCardProps) {
  return (
    <button
      type="button"
      className="analysis-card"
      onClick={onClick}
      disabled={disabled}
    >
      {icon && (
        <div className="analysis-card-icon">
          {icon}
        </div>
      )}

      <div className="analysis-card-content">
        <h3>{title}</h3>
        <p>{description}</p>
      </div>

      <span className="analysis-card-arrow">→</span>
    </button>
  );
}