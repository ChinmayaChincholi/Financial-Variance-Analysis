import type {
  AnalysisResult,
} from "../../types/dataset";

import {
  API_BASE_URL,
} from "./client";

export async function exportAnalysisToExcel(
  result: AnalysisResult,
  filename: string,
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/export/excel`,
    {
      method: "POST",
      headers: {
        "Content-Type":
          "application/json",
      },
      body: JSON.stringify({
        rows: result.rows,
        columns: result.columns,
        filename,
        sheet_name: "Analysis",
      }),
    },
  );

  if (!response.ok) {
    let message =
      `Export failed with status ${response.status}`;

    try {
      const data = await response.json();

      if (data?.detail) {
        message = data.detail;
      }
    } catch {
      // Keep default message.
    }

    throw new Error(message);
  }

  const blob =
    await response.blob();

  const url =
    URL.createObjectURL(blob);

  const anchor =
    document.createElement("a");

  anchor.href = url;
  anchor.download = filename;

  document.body.appendChild(anchor);

  anchor.click();

  anchor.remove();

  URL.revokeObjectURL(url);
}