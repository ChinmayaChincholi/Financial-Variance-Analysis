import type {
  ChangeEvent,
} from "react";

import {
  FileSpreadsheet,
} from "lucide-react";

import {
  useNavigate,
} from "react-router-dom";

import {
  useAnalysisStore,
} from "../state/analysisStore";

export function HomePage() {
  const navigate =
    useNavigate();

  const {
    setFile,
    error,
  } = useAnalysisStore();

  function handleFileChange(
    event: ChangeEvent<HTMLInputElement>,
  ) {
    const file =
      event.target.files?.[0];

    if (!file) {
      return;
    }

    const extension =
      file.name
        .split(".")
        .pop()
        ?.toLowerCase();

    if (
      extension !== "xlsx" &&
      extension !== "xls"
    ) {
      return;
    }

    setFile(file);

    navigate("/processing");
  }

  return (
    <main className="app-shell">
      <section className="home-page">
        <div className="home-content">
          <div className="brand-mark">
            <FileSpreadsheet
              size={30}
            />
          </div>

          <h1>
            Financial Analysis
          </h1>

          <p className="home-description">
            Analyze revenue and cost
            variations across projects,
            regions, months, quarters
            and years.
          </p>

          <label className="upload-button">
            <FileSpreadsheet
              size={19}
            />

            Upload Excel Dataset

            <input
              type="file"
              accept=".xlsx,.xls"
              onChange={
                handleFileChange
              }
              hidden
            />
          </label>

          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

          <p className="offline-note">
            Your dataset is processed
            locally through the
            application backend.
          </p>
        </div>
      </section>
    </main>
  );
}