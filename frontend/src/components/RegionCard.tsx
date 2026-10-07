interface RegionCardProps {
  region: string;
  onClick: () => void;
}

export function RegionCard({
  region,
  onClick,
}: RegionCardProps) {
  return (
    <button
      type="button"
      className="region-card"
      onClick={onClick}
    >
      <span>{region}</span>
      <span>→</span>
    </button>
  );
}