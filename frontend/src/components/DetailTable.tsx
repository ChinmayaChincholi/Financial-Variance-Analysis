import { useMemo, useState } from "react";
import { Download } from "lucide-react";
import type { DetailRow } from "../utils/analysisModel";
import {
  formatSignedUnit,
  formatUnit,
  unitCaption,
  type Unit,
} from "../utils/formatting";

interface DetailTableProps {
  rows: DetailRow[];
  startLabel: string;
  endLabel: string;
  unit: Unit;
  exporting: boolean;
  exportError: string | null;
  onExport: () => void;
}

const COLLAPSED_ROWS = 8;

export function DetailTable({
  rows,
  startLabel,
  endLabel,
  unit,
  exporting,
  exportError,
  onExport,
}: DetailTableProps) {
  const [expanded, setExpanded] = useState(false);
  const [query, setQuery] = useState("");

  const visible = useMemo(() => {
    if (expanded) {
      const needle = query.trim().toLowerCase();
      return needle
        ? rows.filter((row) => row.name.toLowerCase().includes(needle))
        : rows;
    }
    // Drivers first (they are what the sentence is about), then the next
    // largest movers by absolute change, up to a short, scannable list.
    const drivers = rows.filter((row) => row.driver);
    const others = rows
      .filter((row) => !row.driver)
      .sort((a, b) => Math.abs(b.change) - Math.abs(a.change))
      .slice(0, Math.max(0, COLLAPSED_ROWS - drivers.length));
    return [...drivers, ...others].sort((a, b) => b.change - a.change);
  }, [expanded, query, rows]);

  return (
    <div className="card table-card">
      <div className="table-head">
        <span className="muted">Project detail · {unitCaption(unit)}</span>
        <button
          type="button"
          className="btn btn-small"
          onClick={onExport}
          disabled={exporting}
        >
          <Download size={15} aria-hidden="true" />
          {exporting ? "Exporting…" : "Export to Excel"}
        </button>
      </div>
      {exportError && (
        <div className="error-message" role="alert">
          {exportError}
        </div>
      )}

      {expanded && (
        <input
          className="table-search"
          type="search"
          placeholder={`Search ${rows.length.toLocaleString("en-IN")} projects`}
          aria-label="Search projects"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      )}

      <div className={`table-scroll ${expanded ? "tall" : ""}`}>
        <table>
          <thead>
            <tr>
              <th>Project</th>
              <th>{startLabel}</th>
              <th>{endLabel}</th>
              <th>Change</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((row) => (
              <tr key={row.name} className={row.driver ? "dr" : undefined}>
                <td>{row.name}</td>
                <td>{formatUnit(row.start, unit)}</td>
                <td>{formatUnit(row.end, unit)}</td>
                <td className={row.change >= 0 ? "up" : "dn"}>
                  {formatSignedUnit(row.change, unit)}
                </td>
              </tr>
            ))}
            {visible.length === 0 && (
              <tr>
                <td colSpan={4} className="empty-cell">
                  No projects match your search.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {rows.length > COLLAPSED_ROWS && (
        <button
          type="button"
          className="link-button"
          onClick={() => {
            setExpanded((current) => !current);
            setQuery("");
          }}
        >
          {expanded
            ? "Show fewer projects"
            : `Show all ${rows.length.toLocaleString("en-IN")} projects`}
        </button>
      )}
    </div>
  );
}