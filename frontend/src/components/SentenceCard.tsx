import type { CurrencyInfo } from "../types/dataset";
import { splitSentence } from "../utils/analysisModel";
import { formatSentenceAmount } from "../utils/formatting";

interface SentenceTextProps {
  sentence: string;
  currency: CurrencyInfo;
}

/**
 * The backend's summary sentence with the headline figure tidied
 * (currency sign, separators, two decimals) and project names in bold.
 */
export function SentenceText({ sentence, currency }: SentenceTextProps) {
  const text = formatSentenceAmount(sentence, currency);
  const parts = splitSentence(text);
  if (!parts) return <>{text}</>;
  return (
    <>
      {parts.lead}
      <strong>{parts.primary}</strong>
      {parts.middle}
      <strong>{parts.secondary}</strong>
    </>
  );
}