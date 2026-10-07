interface SummaryBannerProps {
  title?: string;
  text?: string;
  sumToReach?: number;
}

export function SummaryBanner({
  title = "Analysis Summary",
  text,
  sumToReach,
}: SummaryBannerProps) {
  if (!text && sumToReach === undefined) {
    return null;
  }

  return (
    <div className="summary-banner">
      <div>
        <h3>{title}</h3>

        {text && <p>{text}</p>}
      </div>

      {sumToReach !== undefined && (
        <div className="summary-value">
          {sumToReach.toLocaleString("en-IN")}
        </div>
      )}
    </div>
  );
}