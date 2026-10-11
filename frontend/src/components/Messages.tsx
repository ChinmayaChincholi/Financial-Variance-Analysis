import type { ReactNode } from "react";
import { Paperclip } from "lucide-react";
import { BrandMark } from "./Brand";
import { formatBytes } from "../utils/formatting";

interface FileChipProps {
  name: string;
  size?: number | null;
}

/** The user's side of the conversation: the file they attached. */
export function FileChip({ name, size }: FileChipProps) {
  const sizeLabel = formatBytes(size);
  return (
    <div className="col chip-row">
      <span className="chip">
        <Paperclip size={15} aria-hidden="true" />
        <span>{name}</span>
        {sizeLabel && <span className="muted">· {sizeLabel}</span>}
      </span>
    </div>
  );
}

interface AssistantRowProps {
  icon?: ReactNode;
  children: ReactNode;
}

/** The app's side of the conversation. */
export function AssistantRow({ icon, children }: AssistantRowProps) {
  return (
    <div className="ai">
      <span className="ai-icon">{icon ?? <BrandMark size={28} />}</span>
      <div className="ai-body">{children}</div>
    </div>
  );
}