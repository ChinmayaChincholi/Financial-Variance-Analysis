import { Download } from "lucide-react";

import type { AnalysisResult } from "../types/dataset";
import { exportAnalysisToExcel } from "../services/api/exportApi";

interface ExportButtonProps {
  result: AnalysisResult;
  filename: string;
}

export function ExportButton({
  result,
  filename,
}: ExportButtonProps) {
  function handleExport() {
    exportAnalysisToExcel(result, filename);
  }

  return (
    <button
      type="button"
      className="secondary-button"
      onClick={handleExport}
    >
      <Download size={17} />
      Export to Excel
    </button>
  );
}