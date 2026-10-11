import { splitSentence } from "../utils/analysisModel";

interface SentenceTextProps {
  sentence: string;
}

/** The backend's summary sentence, unchanged, with project names in bold. */
export function SentenceText({ sentence }: SentenceTextProps) {
  const parts = splitSentence(sentence);
  if (!parts) return <>{sentence}</>;
  return (
    <>
      {parts.lead}
      <strong>{parts.primary}</strong>
      {parts.middle}
      <strong>{parts.secondary}</strong>
    </>
  );
}