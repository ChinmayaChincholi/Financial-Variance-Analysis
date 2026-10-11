import type { TableResult } from "../../types/dataset";
import { API_BASE_URL, readErrorMessage } from "./client";

export async function exportAnalysisToExcel(
  table: TableResult,
  filename: string,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/export/excel`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      rows: table.rows,
      columns: table.columns,
      filename,
      sheet_name: "Analysis",
    }),
  });

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(
        response,
        `Export failed with status ${response.status}`,
      ),
    );
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}