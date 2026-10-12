import { useId } from "react";

interface SwitchProps {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  /** Explains why the switch cannot be changed; shown on hover/focus. */
  tooltip?: string;
  ariaLabel: string;
}

export function Switch({
  label,
  checked,
  onChange,
  disabled = false,
  tooltip,
  ariaLabel,
}: SwitchProps) {
  const tipId = useId();
  const hasTip = Boolean(disabled && tooltip);

  return (
    <div className="seg-cell switch-cell">
      <button
        type="button"
        role="switch"
        className="switch"
        aria-label={ariaLabel}
        aria-checked={checked}
        aria-disabled={disabled || undefined}
        aria-describedby={hasTip ? tipId : undefined}
        onClick={() => {
          if (!disabled) onChange(!checked);
        }}
      >
        <span className="switch-track" aria-hidden="true">
          <span className="switch-thumb" />
        </span>
        <span>{label}</span>
      </button>
      {hasTip && (
        <span role="tooltip" id={tipId} className="tip">
          {tooltip}
        </span>
      )}
    </div>
  );
}