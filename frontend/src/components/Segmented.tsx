import { useId } from "react";

export interface SegmentedItem<T extends string> {
  value: T;
  label: string;
  disabled?: boolean;
  /** Shown on hover/focus when the item is disabled (explains why). */
  tooltip?: string;
}

interface SegmentedProps<T extends string> {
  items: SegmentedItem<T>[];
  value: T;
  onChange: (value: T) => void;
  ariaLabel: string;
}

export function Segmented<T extends string>({
  items,
  value,
  onChange,
  ariaLabel,
}: SegmentedProps<T>) {
  const groupId = useId();

  return (
    <div className="seg" role="group" aria-label={ariaLabel}>
      {items.map((item) => {
        const tipId = `${groupId}-${item.value}-tip`;
        const hasTip = Boolean(item.disabled && item.tooltip);
        return (
          <div className="seg-cell" key={item.value}>
            <button
              type="button"
              className={item.value === value ? "on" : undefined}
              aria-pressed={item.value === value}
              aria-disabled={item.disabled || undefined}
              aria-describedby={hasTip ? tipId : undefined}
              onClick={() => {
                if (!item.disabled) onChange(item.value);
              }}
            >
              {item.label}
            </button>
            {hasTip && (
              <span role="tooltip" id={tipId} className="tip">
                {item.tooltip}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}