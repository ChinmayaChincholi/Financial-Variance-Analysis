import { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  cancelIngestion,
  startIngestion,
  submitClarifications,
} from "../services/ingestionController";
import { useAnalysisStore } from "../state/analysisStore";
import { getCachedDemoConfig } from "./useDemoConfig";
import type { WorkspaceMeta } from "../types/dataset";

export function validateExcelFile(file: File): string | null {
  const extension = file.name.split(".").pop()?.toLowerCase();
  if (extension !== "xlsx" && extension !== "xls") {
    return "Please attach an Excel file (.xlsx or .xls).";
  }

  // Only the web demo has an upload limit (the server enforces it too; this
  // just explains it before a large file is sent).
  const limitMb = getCachedDemoConfig()?.max_upload_mb;
  if (limitMb && file.size > limitMb * 1024 * 1024) {
    const sizeMb = (file.size / (1024 * 1024)).toFixed(1);
    return `That file is ${sizeMb} MB. The web demo accepts files up to ${limitMb} MB; use the desktop application for larger datasets.`;
  }

  return null;
}

/** Actions for the attach -> process -> questions flow, with navigation. */
export function useIngestion() {
  const navigate = useNavigate();

  const goToSummary = useCallback(
    (meta: WorkspaceMeta | null) => {
      // Only jump if the user is still looking at the conversation; if they
      // opened another workspace meanwhile, don't yank them away from it.
      if (meta && window.location.pathname === "/") {
        navigate(`/workspace/${meta.id}/summary`, { replace: true });
      }
    },
    [navigate],
  );

  /** Returns an error message if the file is not acceptable. */
  const attach = useCallback(
    (file: File): string | null => {
      const problem = validateExcelFile(file);
      if (problem) return problem;
      navigate("/");
      void startIngestion(file).then(goToSummary);
      return null;
    },
    [navigate, goToSummary],
  );

  const chooseSheet = useCallback(
    (sheet: string) => {
      const { file } = useAnalysisStore.getState();
      if (!file) return;
      void startIngestion(file, sheet).then(goToSummary);
    },
    [goToSummary],
  );

  const submit = useCallback(() => {
    void submitClarifications().then(goToSummary);
  }, [goToSummary]);

  const retry = useCallback(() => {
    const { file, selectedSheet } = useAnalysisStore.getState();
    if (!file) return;
    void startIngestion(file, selectedSheet ?? undefined).then(goToSummary);
  }, [goToSummary]);

  const cancel = useCallback(() => cancelIngestion(), []);

  return { attach, chooseSheet, submit, retry, cancel };
}