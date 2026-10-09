import {
  useEffect,
} from "react";

import {
  useNavigate,
} from "react-router-dom";

import {
  LoadingState,
} from "../components/LoadingState";

import {
  processDatasetWithProgress,
} from "../services/api/datasetApi";

import {
  useAnalysisStore,
} from "../state/analysisStore";

import {
  getErrorMessage,
} from "../utils/errors";

export function ProcessingPage() {
  const navigate =
    useNavigate();

  const {
    file,
    selectedSheet,
    processingStage,
    setSheets,
    setSelectedSheet, // ← CHANGED (added)
    setSession,
    setClarifications,
    setProcessing,
    setError,
  } = useAnalysisStore();

  useEffect(() => {
    if (!file) {
      navigate(
        "/",
        {
          replace: true,
        },
      );

      return;
    }

    const selectedFile =
      file;

    const controller =
      new AbortController();

    let cancelled =
      false;

    async function process() {
      try {
        /*
         * The backend now controls the actual stage.
         *
         * This is only an initial state while the request
         * is being established.
         */
        setProcessing(
          true,
          "Importing dataset",
        );

        const response =
          await processDatasetWithProgress(
            selectedFile,
            selectedSheet ??
              undefined,
            (event) => {
              if (cancelled) {
                return;
              }

              setProcessing(
                true,
                event.stage,
              );
            },
            controller.signal,
          );

        if (cancelled) {
          return;
        }

        /*
         * Multiple worksheets were detected.
         *
         * We stop processing here and send the user to the
         * worksheet-selection page.
         */
        if (
          response.status ===
          "needs_sheet_selection"
        ) {
          setSheets(
            response.sheets ??
              [],
          );

          setProcessing(
            false,
          );

          navigate(
            "/sheets",
          );

          return;
        }

        /*
         * Column matching needs user input.
         */
        if (
          response.status ===
          "needs_clarification"
        ) {
          /*
           * Single-sheet workbooks never visit the sheet-selection
           * page, so the store's selectedSheet would stay null and
           * ClarificationPage would render nothing. Persist the
           * sheet the backend actually used.
           */
          if (response.sheet_name) { // ← CHANGED (added block)
            setSelectedSheet(
              response.sheet_name,
            );
          }

          setClarifications(
            response.clarifications ??
              [],
          );

          setProcessing(
            false,
          );

          navigate(
            "/clarification",
          );

          return;
        }

        /*
         * Normal successful processing.
         */
        if (
          !response.session
        ) {
          throw new Error(
            "The backend did not return a completed analysis session.",
          );
        }

        setSession(
          response.session,
        );

        navigate(
          "/scope",
        );

      } catch (error) {
        if (
          cancelled
        ) {
          return;
        }

        /*
         * AbortController errors caused by leaving this page
         * should not be shown to the user.
         */
        if (
          error instanceof DOMException &&
          error.name ===
            "AbortError"
        ) {
          return;
        }

        setError(
          getErrorMessage(
            error,
          ),
        );

        navigate(
          "/",
          {
            replace: true,
          },
        );

      } finally {
        if (
          !cancelled
        ) {
          /*
           * setSession() already clears processing on success.
           *
           * For clarification/sheet-selection, those branches
           * explicitly clear processing before navigating.
           */
        }
      }
    }

    process();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [
    file,
    navigate,
    selectedSheet,
    setClarifications,
    setError,
    setProcessing,
    setSelectedSheet, // ← CHANGED (added)
    setSession,
    setSheets,
  ]);

  return (
    <main className="app-shell">
      <LoadingState
        message={
          processingStage ||
          "Preparing your analysis..."
        }
      />
    </main>
  );
}