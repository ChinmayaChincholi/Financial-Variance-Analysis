import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { BackButton } from "../navigation/BackButton";
import { resolveDataset } from "../services/api/datasetApi";
import { useAnalysisStore } from "../state/analysisStore";
import { getErrorMessage } from "../utils/errors";

export function ClarificationPage() {
  const navigate = useNavigate();

  const {
    file,
    clarifications,
    clarificationChoices,
    setClarificationChoice,
    setSession,
    setError,
  } = useAnalysisStore();

  const [submitting, setSubmitting] =
    useState(false);

  const allFieldsSelected =
    clarifications.length > 0 &&
    clarifications.every(
      (item) =>
        clarificationChoices[item.field],
    );

  async function handleContinue() {
    if (!file || !allFieldsSelected) {
      return;
    }

    try {
      setSubmitting(true);

      const response = await resolveDataset(
        file,
        clarificationChoices,
      );

      if (response.status === "needs_clarification") {
        setError(
          "Some columns still need clarification.",
        );
        setSubmitting(false);
        return;
      }

      if (!response.session) {
        throw new Error(
          "The backend did not return a completed analysis session.",
        );
      }

      setSession(response.session);
      navigate("/scope");
    } catch (error) {
      setError(getErrorMessage(error));
      setSubmitting(false);
    }
  }

  return (
    <main className="app-shell">
      <div className="page-container">
        <div className="simple-topbar">
          <BackButton fallback="/" />
        </div>

        <section className="clarification-page">
          <h1>Confirm Detected Columns</h1>

          <p className="page-description">
            Some columns could not be identified
            confidently. Please confirm the appropriate
            column for each field.
          </p>

          <div className="clarification-list">
            {clarifications.map((clarification) => (
              <div
                className="clarification-card"
                key={clarification.field}
              >
                <h3>{clarification.field}</h3>

                <p>{clarification.message}</p>

                <select
                  value={
                    clarificationChoices[
                      clarification.field
                    ] ?? ""
                  }
                  onChange={(event) =>
                    setClarificationChoice(
                      clarification.field,
                      event.target.value,
                    )
                  }
                >
                  <option value="">
                    Select a column
                  </option>

                  {clarification.candidates.map(
                    (candidate) => (
                      <option
                        key={candidate.column}
                        value={candidate.column}
                      >
                        {candidate.column}
                      </option>
                    ),
                  )}
                </select>
              </div>
            ))}
          </div>

          <button
            type="button"
            className="primary-button"
            disabled={
              !allFieldsSelected || submitting
            }
            onClick={handleContinue}
          >
            {submitting
              ? "Processing..."
              : "Confirm and Continue"}
          </button>
        </section>
      </div>
    </main>
  );
}