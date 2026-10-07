import type { PeriodOption } from "../types/dataset";

interface PeriodSelectorProps {
  options: PeriodOption[];
  onSelect: (option: PeriodOption) => void;
}

export function PeriodSelector({
  options,
  onSelect,
}: PeriodSelectorProps) {
  if (!options.length) {
    return (
      <div className="empty-state">
        No valid comparison periods are available.
      </div>
    );
  }

  return (
    <div className="period-list">
      {options.map((option) => (
        <button
          type="button"
          className="period-option"
          key={option.id}
          onClick={() => onSelect(option)}
        >
          <span>{option.label}</span>
          <span>→</span>
        </button>
      ))}
    </div>
  );
}