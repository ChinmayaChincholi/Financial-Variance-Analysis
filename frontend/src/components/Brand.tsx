interface BrandMarkProps {
  size?: number;
}

/** Three-bar chart mark. */
export function BrandMark({ size = 28 }: BrandMarkProps) {
  return (
    <svg
      className="brand-mark"
      width={size}
      height={size}
      viewBox="0 0 28 28"
      aria-hidden="true"
    >
      <rect x="3" y="12" width="6" height="13" rx="2" />
      <rect x="11" y="3" width="6" height="22" rx="2" />
      <rect x="19" y="8" width="6" height="17" rx="2" />
    </svg>
  );
}

interface RingProps {
  size?: number;
}

/** Animated progress ring used while the backend is working. */
export function Ring({ size = 28 }: RingProps) {
  return (
    <svg
      className="ring"
      width={size}
      height={size}
      viewBox="0 0 28 28"
      aria-hidden="true"
    >
      <circle className="ring-track" cx="14" cy="14" r="11" />
      <circle className="ring-arc" cx="14" cy="14" r="11" />
    </svg>
  );
}