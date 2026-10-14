import { Info } from "lucide-react";
import { useDemoConfig } from "../hooks/useDemoConfig";
import "../styles/web.css";

function describeHours(hours: number): string {
  return hours === 1 ? "1 hour" : `${Number(hours.toFixed(1))} hours`;
}

/** Shown on every page of the web demo, and only there. */
export function DemoBanner() {
  const config = useDemoConfig();

  return (
    <div className="demo-banner" role="note">
      <Info size={14} aria-hidden="true" />
      <span>
        <strong>Web demo.</strong> Please don&apos;t upload confidential data.
        {config &&
          ` Your workspaces are deleted after ${describeHours(config.retention_hours)} of inactivity.`}{" "}
        The desktop edition keeps everything on your own computer.
      </span>
    </div>
  );
}