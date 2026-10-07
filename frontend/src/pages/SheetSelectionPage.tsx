import {
  useNavigate,
} from "react-router-dom";

import {
  PageHeader,
} from "../navigation/PageHeader";

import {
  useAnalysisStore,
} from "../state/analysisStore";

export function SheetSelectionPage() {
  const navigate =
    useNavigate();

  const {
    file,
    sheets,
    selectedSheet,
    setSelectedSheet,
  } = useAnalysisStore();

  if (!file) {
    navigate("/", {
      replace: true,
    });

    return null;
  }

  if (!sheets.length) {
    navigate("/processing", {
      replace: true,
    });

    return null;
  }

  function handleContinue() {
    if (!selectedSheet) {
      return;
    }

    navigate("/processing");
  }

  return (
    <main className="app-shell">
      <div className="page-container">
        <PageHeader
          title="Select Worksheet"
          subtitle="Choose the worksheet that contains the financial dataset."
        />

        <div className="period-list">
          {sheets.map((sheet) => (
            <button
              key={sheet}
              type="button"
              className="period-option"
              onClick={() =>
                setSelectedSheet(sheet)
              }
              style={{
                borderColor:
                  selectedSheet === sheet
                    ? "#3157d5"
                    : undefined,
                background:
                  selectedSheet === sheet
                    ? "#f5f7ff"
                    : undefined,
              }}
            >
              <span>{sheet}</span>

              <span>
                {selectedSheet === sheet
                  ? "Selected"
                  : "Select"}
              </span>
            </button>
          ))}
        </div>

        <div
          style={{
            marginTop: "24px",
          }}
        >
          <button
            type="button"
            className="primary-button"
            disabled={!selectedSheet}
            onClick={handleContinue}
          >
            Continue
          </button>
        </div>
      </div>
    </main>
  );
}