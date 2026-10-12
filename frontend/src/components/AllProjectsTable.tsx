import { useMemo, useState } from "react";
import { Download } from "lucide-react";
import type { CurrencyInfo, TableResult } from "../types/dataset";
import type { RegionColumn } from "../utils/analysisModel";
import { currencyCaption, formatMoney, toNumber } from "../utils/formatting";

interface AllProjectsTableProps {
  table: TableResult;
  projectColumn: string;
  currency: CurrencyInfo;
  regionColumn: RegionColumn | null;
  exporting: boolean;
  exportError: string | null;
  onExport: () => void;
}

const MAX_RENDERED_ROWS = 500;

export function AllProjectsTable({
  table,
  projectColumn,
  currency,
  regionColumn,
  exporting,
  exportError,
  onExport,
}: AllProjectsTableProps) {
  const [query, setQuery] = useState("");

  const matches = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return needle
      ? table.rows.filter((row) =>
          String(row[projectColumn] ?? "").toLowerCase().includes(needle),
        )
      : table.rows;
  }, [projectColumn, query, table.rows]);

  const shown = matches.slice(0, MAX_RENDERED_ROWS);

  return (
    <div className="card table-card">
      <div className="table-head">
        <span className="muted">
          All projects · {matches.length.toLocaleString("en-US")} projects ·{" "}
          {currencyCaption(currency)}
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

      <input
        className="table-search"
        type="search"
        placeholder="Search projects"
        aria-label="Search projects"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
      />

      <div className="table-scroll tall">
        <table className="sticky-first">
          <thead>
            <tr>
              <th>{projectColumn}</th>
              {regionColumn && <th>{regionColumn.name}</th>}
              {table.columns
                .filter((column) => column !== projectColumn)
                .map((column) => (
                  <th key={column}>{column}</th>
                ))}
            </tr>
          </thead>
          <tbody>
            {shown.map((row, index) => (
              <tr key={index}>
                <td>{String(row[projectColumn] ?? "-")}</td>
                {regionColumn && <td>{regionColumn.value}</td>}
                {table.columns
                  .filter((column) => column !== projectColumn)
                  .map((column) => {
                    const value = row[column];
                    return (
                      <td key={column}>
                        {value === null || value === undefined || value === ""
                          ? "-"
                          : formatMoney(toNumber(value), currency)}
                      </td>
                    );
                  })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {matches.length > MAX_RENDERED_ROWS && (
        <p className="muted small">
          Showing the first {MAX_RENDERED_ROWS} projects. Search to narrow the
          list, or export to Excel for everything.
        </p>
      )}
    </div>
  );
}