import { useMemo, useState } from "react";
import { Download } from "lucide-react";
import type { TableResult } from "../types/dataset";
import { formatNumber } from "../utils/formatting";

interface TotalsTableProps {
  table: TableResult;
  projectColumn: string;
  exporting: boolean;
  exportError: string | null;
  onExport: () => void;
}

const MAX_RENDERED_ROWS = 500;

export function TotalsTable({
  table,
  projectColumn,
  exporting,
  exportError,
  onExport,
}: TotalsTableProps) {
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
          {matches.length.toLocaleString("en-IN")} projects
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
        <table>
          <thead>
            <tr>
              {table.columns.map((column) => (
                <th key={column}>{column}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {shown.map((row, index) => (
              <tr key={index}>
                {table.columns.map((column) => (
                  <td key={column}>
                    {column === projectColumn
                      ? String(row[column] ?? "-")
                      : formatNumber(row[column])}
                  </td>
                ))}
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