import {
  useMemo,
  useState,
} from "react";

import {
  useNavigate,
} from "react-router-dom";

import {
  PageHeader,
} from "../navigation/PageHeader";

import {
  resolveDataset,
} from "../services/api/datasetApi";

import {
  useAnalysisStore,
} from "../state/analysisStore";

import {
  getErrorMessage,
} from "../utils/errors";

export function ClarificationPage() {
  const navigate =
    useNavigate();

  const {
    file,
    selectedSheet,
    clarifications,
    clarificationChoices,
    setClarificationChoice,
    setClarifications,
    setSession,
    setError,
  } = useAnalysisStore();

  const [submitting, setSubmitting] =
    useState(false);

  if (!file) {
    navigate("/", {
      replace: true,
    });

    return null;
  }

  if (!selectedSheet) {
    navigate("/processing", {
      replace: true,
    });

    return null;
  }

  const allFieldsSelected =
    useMemo(() => {
      return clarifications.every(
        (item) => {
          const choice =
            clarificationChoices[
              item.field
            ];

          if (item.allow_none) {
            return (
              choice !== undefined
            );
          }

          return Boolean(choice);
        },
      );
    }, [
      clarificationChoices,
      clarifications,
    ]);

  async function handleContinue() {
    if (
      !file ||
      !selectedSheet ||
      !allFieldsSelected
    ) {
      return;
    }

    try {
      setSubmitting(true);
      setError(null);

      const response =
        await resolveDataset(
          file,
          clarificationChoices,
          selectedSheet,
        );

      if (
        response.status ===
        "needs_clarification"
      ) {
        setClarifications(
          response.clarifications ?? [],
        );

        setSubmitting(false);

        return;
      }

      if (!response.session) {
        throw new Error(
          "The backend did not return a completed analysis session.",
        );
      }

      setSession(
        response.session,
      );

      navigate("/scope");
    } catch (error) {
      setError(
        getErrorMessage(error),
      );

      setSubmitting(false);
    }
  }

  return (
    <main className="app-shell">
      <div className="page-container">
        <PageHeader
          title="Confirm Detected Columns"
          subtitle="Some dataset fields need your confirmation before analysis can continue."
        />

        <div className="clarification-list">
          {clarifications.map(
            (clarification) => (
              <div
                className="clarification-card"
                key={clarification.field}
              >
                <h3>
                  {clarification.field}
                </h3>

                <p
                  style={{
                    whiteSpace:
                      "pre-line",
                  }}
                >
                  {clarification.message}
                </p>

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
                    Select an option
                  </option>

                  {clarification.candidates.map(
                    (candidate) => (
                      <option
                        key={
                          `${clarification.field}-${candidate.column}`
                        }
                        value={
                          candidate.column
                        }
                      >
                        {candidate.column}
                      </option>
                    ),
                  )}

                  {clarification.allow_none && (
                    <option value="__none__">
                      No Region column
                    </option>
                  )}
                </select>
              </div>
            ),
          )}
        </div>

        <button
          type="button"
          className="primary-button"
          disabled={
            !allFieldsSelected ||
            submitting
          }
          onClick={
            handleContinue
          }
        >
          {submitting
            ? "Processing..."
            : "Confirm and Continue"}
        </button>
      </div>
    </main>
  );
}