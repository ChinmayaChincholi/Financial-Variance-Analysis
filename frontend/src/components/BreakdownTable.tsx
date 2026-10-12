import { useMemo, useState } from "react";
import { Download } from "lucide-react";
import type { CurrencyInfo } from "../types/dataset";
import type { DetailRow, RegionColumn } from "../utils/analysisModel";
import {
  currencyCaption,
  formatMoney,
  formatSignedMoney,
} from "../utils/formatting";

interface BreakdownTableProps {
  rows: DetailRow[];
  startLabel: string;
  endLabel: string;
  currency: CurrencyInfo;
  /** Present for region-wise analysis: every row shows the chosen region. */
  regionColumn: RegionColumn | null;
  exporting: boolean;
  exportError: string | null;
  onExport: () => void;
}

const COLLAPSED_ROWS = 8;

export function BreakdownTable({
  rows,
  startLabel,
  endLabel,
  currency,
  regionColumn,
  exporting,
  exportError,
  onExport,
}: BreakdownTableProps) {
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

  const columnCount = regionColumn ? 5 : 4;

  return (
    <div className="card table-card">
      <div className="table-head">
        <span className="muted">
          Project breakdown · {currencyCaption(currency)}
        </span>
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
          placeholder={`Search ${rows.length.toLocaleString("en-US")} projects`}
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
              {regionColumn && <th>{regionColumn.name}</th>}
              <th>{startLabel}</th>
              <th>{endLabel}</th>
              <th>Change</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((row) => (
              <tr key={row.name} className={row.driver ? "dr" : undefined}>
                <td>{row.name}</td>
                {regionColumn && <td>{regionColumn.value}</td>}
                <td>{formatMoney(row.start, currency)}</td>
                <td>{formatMoney(row.end, currency)}</td>
                <td className={row.change >= 0 ? "up" : "dn"}>
                  {formatSignedMoney(row.change, currency)}
                </td>
              </tr>
            ))}
            {visible.length === 0 && (
              <tr>
                <td colSpan={columnCount} className="empty-cell">
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
            : `Show all ${rows.length.toLocaleString("en-US")} projects`}
        </button>
      )}
    </div>
  );
}