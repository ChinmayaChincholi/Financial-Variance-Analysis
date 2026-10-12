import type { CurrencyInfo } from "../types/dataset";

/** Used when a workspace has no detected currency: dollars are assumed. */
export const DEFAULT_CURRENCY: CurrencyInfo = {
  code: "USD",
  symbol: "$",
  name: "US Dollar",
  detected: false,
  mixed: false,
  found: [],
  source: "assumed",
};

const MINUS = "\u2212";

const money = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const plain = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 });

/** "$", "€", or "CHF " for code-only currencies; empty when mixed. */
function prefix(currency: CurrencyInfo): string {
  const symbol = currency.symbol;
  if (!symbol) return "";
  return /^[A-Za-z]+$/.test(symbol) ? `${symbol} ` : symbol;
}

/** Rounds to cents so values like -0.004 never print as "-$0.00". */
function cents(value: number): number {
  return Math.round(Math.abs(value) * 100) / 100;
}

/** Exact amount: "$1,234.50" or "−$1,234.50". */
export function formatMoney(value: number, currency: CurrencyInfo): string {
  const magnitude = cents(value);
  const sign = value < 0 && magnitude > 0 ? MINUS : "";
  return `${sign}${prefix(currency)}${money.format(magnitude)}`;
}

/** Exact amount with an explicit sign: "+$1,234.50" / "−$1,234.50". */
export function formatSignedMoney(
  value: number,
  currency: CurrencyInfo,
): string {
  const magnitude = cents(value);
  const sign = value < 0 && magnitude > 0 ? MINUS : "+";
  return `${sign}${prefix(currency)}${money.format(magnitude)}`;
}

/**
 * Compact amount for chart labels: "$350.50K", "$4.82M", "$1.20B".
 * Charts only — tables and the sentence always show exact values.
 */
export function formatCompactMoney(
  value: number,
  currency: CurrencyInfo,
  signed = false,
): string {
  const abs = Math.abs(value);
  let body: string;
  if (abs >= 1e9) body = `${prefix(currency)}${(abs / 1e9).toFixed(2)}B`;
  else if (abs >= 1e6) body = `${prefix(currency)}${(abs / 1e6).toFixed(2)}M`;
  else if (abs >= 1e3) body = `${prefix(currency)}${(abs / 1e3).toFixed(2)}K`;
  else body = `${prefix(currency)}${money.format(cents(abs))}`;

  const negative = value < 0 && abs >= 0.005;
  if (negative) return `${MINUS}${body}`;
  return signed ? `+${body}` : body;
}

/** Caption stating what the amounts and compact suffixes mean. */
export function scaleCaption(currency: CurrencyInfo): string {
  if (currency.mixed) {
    return "mixed currencies, not converted · K = thousand, M = million";
  }
  return `amounts in ${currency.name} (${currency.symbol}) · K = thousand, M = million`;
}

/** Short currency description for table captions. */
export function currencyCaption(currency: CurrencyInfo): string {
  return currency.mixed
    ? "mixed currencies, not converted"
    : `${currency.name} (${currency.symbol})`;
}

const SENTENCE_AMOUNT =
  /(net (?:increase|decrease) of )([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)( amount)/;

/**
 * Tidy only the headline figure in the backend's summary sentence:
 * currency sign, thousands separators, two decimals, and no minus sign
 * (the words "increase" / "decrease" already carry the direction).
 * Everything else in the sentence is left untouched.
 */
export function formatSentenceAmount(
  sentence: string,
  currency: CurrencyInfo,
): string {
  return sentence.replace(
    SENTENCE_AMOUNT,
    (match, lead: string, raw: string, tail: string) => {
      const amount = Number(raw);
      if (!Number.isFinite(amount)) return match;
      return `${lead}${formatMoney(Math.abs(amount), currency)}${tail}`;
    },
  );
}

/** Plain grouped number (no currency), e.g. row counts. */
export function formatNumber(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return String(value);
  }
  return plain.format(numericValue);
}

export function formatBytes(bytes: number | null | undefined): string {
  if (!bytes || bytes < 0) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function toNumber(value: unknown): number {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : 0;
}