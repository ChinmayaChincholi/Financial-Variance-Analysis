import { formatNumber } from "../utils/formatting";
import type { AnalysisResult } from "../types/dataset";

interface AnalysisTableProps {
  result: AnalysisResult;
}

export function AnalysisTable({
  result,
}: AnalysisTableProps) {
  if (!result.rows.length) {
    return (
      <div className="empty-state">
        No data available for this analysis.
      </div>
    );
  }

  const columns =
    result.columns.length > 0
      ? result.columns
      : Object.keys(result.rows[0]);

  return (
    <div className="table-container">
      <table className="analysis-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>

        <tbody>
          {result.rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {columns.map((column) => {
                const value = row[column];

                return (
                  <td key={`${rowIndex}-${column}`}>
                    {typeof value === "number"
                      ? formatNumber(value)
                      : value ?? "-"}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}