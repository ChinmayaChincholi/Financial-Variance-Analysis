import {
  useState,
} from "react";

import {
  Download,
} from "lucide-react";

import type {
  AnalysisResult,
} from "../types/dataset";

import {
  exportAnalysisToExcel,
} from "../services/api/exportApi";

interface ExportButtonProps {
  result: AnalysisResult;
  filename: string;
}

export function ExportButton({
  result,
  filename,
}: ExportButtonProps) {
  const [exporting, setExporting] =
    useState(false);

  const [error, setError] =
    useState<string | null>(null);

  async function handleExport() {
    try {
      setExporting(true);
      setError(null);

      await exportAnalysisToExcel(
        result,
        filename,
      );
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Could not export the analysis.",
      );
    } finally {
      setExporting(false);
    }
  }

  return (
    <div>
      <button
        type="button"
        className="secondary-button"
        onClick={handleExport}
        disabled={exporting}
      >
        <Download size={17} />

        {exporting
          ? "Exporting..."
          : "Export to Excel"}
      </button>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}
    </div>
  );
}