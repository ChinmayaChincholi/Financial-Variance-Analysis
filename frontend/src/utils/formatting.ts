/**
 * Currency symbol shown next to compact amounts (e.g. "+₹4.82 Cr").
 * Set to "" if the dataset should be shown without a symbol.
 */
export const CURRENCY_SYMBOL = "₹";

const grouped = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 });
const fixed2 = new Intl.NumberFormat("en-IN", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function formatNumber(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return String(value);
  }
  return grouped.format(numericValue);
}

export interface Unit {
  divisor: number;
  label: "" | "L" | "Cr";
}

/** Pick the Indian unit (lakh / crore) that keeps numbers readable. */
export function chooseUnit(maxAbs: number): Unit {
  if (maxAbs >= 1e7) return { divisor: 1e7, label: "Cr" };
  if (maxAbs >= 1e5) return { divisor: 1e5, label: "L" };
  return { divisor: 1, label: "" };
}

/** "₹ Cr", "₹ L" or "₹" — used in chart and table captions. */
export function unitCaption(unit: Unit): string {
  return `${CURRENCY_SYMBOL}${unit.label ? ` ${unit.label}` : ""}`.trim();
}

/** Two-decimal value in the given unit, with Indian digit grouping. */
export function formatUnit(value: number, unit: Unit): string {
  return fixed2.format(value / unit.divisor);
}

const MINUS = "\u2212";

export function formatSignedUnit(value: number, unit: Unit): string {
  const sign = value < 0 ? MINUS : "+";
  return `${sign}${fixed2.format(Math.abs(value) / unit.divisor)}`;
}

/** Headline amount, e.g. "+₹4.82 Cr" or "−₹3.10 Cr". */
export function formatSignedCompact(value: number): string {
  const unit = chooseUnit(Math.abs(value));
  const sign = value < 0 ? MINUS : "+";
  const suffix = unit.label ? ` ${unit.label}` : "";
  return `${sign}${CURRENCY_SYMBOL}${fixed2.format(
    Math.abs(value) / unit.divisor,
  )}${suffix}`;
}

export function formatBytes(bytes: number | null | undefined): string {
  if (!bytes || bytes < 0) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatElapsed(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

export function toNumber(value: unknown): number {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : 0;
}