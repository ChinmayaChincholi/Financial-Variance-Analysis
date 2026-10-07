import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { LoadingState } from "../components/LoadingState";
import { processDataset } from "../services/api/datasetApi";
import { useAnalysisStore } from "../state/analysisStore";
import { getErrorMessage } from "../utils/errors";

const stages = [
  "Importing dataset",
  "Detecting columns",
  "Computing project-wise analysis",
  "Computing region-wise analysis",
  "Finalizing results",
];

export function ProcessingPage() {
  const navigate = useNavigate();

  const {
    file,
    processingStage,
    setSession,
    setClarifications,
    setProcessing,
    setError,
  } = useAnalysisStore();

  useEffect(() => {
    if (!file) {
      navigate("/", { replace: true });
      return;
    }

    // Capture the narrowed File value.
    // This prevents TypeScript from treating it as File | null
    // inside the nested async function.
    const selectedFile = file;

    let cancelled = false;
    let stageTimer: number | undefined;

    async function process() {
      try {
        setProcessing(true, stages[0]);

        stageTimer = window.setInterval(() => {
          const currentStage = stages.indexOf(
            useAnalysisStore.getState().processingStage,
          );

          if (
            currentStage >= 0 &&
            currentStage < stages.length - 1
          ) {
            setProcessing(
              true,
              stages[currentStage + 1],
            );
          }
        }, 1200);

        const response = await processDataset(selectedFile);

        if (cancelled) {
          return;
        }

        if (response.status === "needs_clarification") {
          setClarifications(
            response.clarifications ?? [],
          );

          setProcessing(false);

          navigate("/clarification");
          return;
        }

        if (!response.session) {
          throw new Error(
            "The backend did not return a completed analysis session.",
          );
        }

        setProcessing(
          true,
          stages[stages.length - 1],
        );

        setSession(response.session);

        window.setTimeout(() => {
          if (!cancelled) {
            setProcessing(false);
            navigate("/scope");
          }
        }, 300);
      } catch (error) {
        if (cancelled) {
          return;
        }

        setError(getErrorMessage(error));
        navigate("/");
      } finally {
        if (stageTimer !== undefined) {
          window.clearInterval(stageTimer);
        }
      }
    }

    process();

    return () => {
      cancelled = true;

      if (stageTimer !== undefined) {
        window.clearInterval(stageTimer);
      }
    };
  }, [
    file,
    navigate,
    setClarifications,
    setError,
    setProcessing,
    setSession,
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