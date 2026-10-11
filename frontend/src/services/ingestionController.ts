import {
  processDatasetWithProgress,
  resolveDataset,
} from "./api/datasetApi";
import { useAnalysisStore } from "../state/analysisStore";
import { useWorkspaceStore } from "../state/workspaceStore";
import { getErrorMessage } from "../utils/errors";
import type {
  IngestionResponse,
  WorkspaceMeta,
} from "../types/dataset";

/*
 * Drives the attach -> process -> (questions) -> done flow.
 *
 * It lives outside React so a request keeps running (and can be cancelled)
 * regardless of which component is mounted. Every function resolves to the
 * saved workspace on success, or null when the flow is waiting for the user,
 * was cancelled, or failed (the store then holds the reason).
 */

let controller: AbortController | null = null;

function nextSignal(): AbortSignal {
  controller?.abort();
  controller = new AbortController();
  return controller.signal;
}

function isAbort(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

function handleResponse(response: IngestionResponse): WorkspaceMeta | null {
  const store = useAnalysisStore.getState();

  if (response.status === "needs_sheet_selection") {
    store.needSheet(response.sheets ?? []);
    return null;
  }

  if (response.status === "needs_clarification") {
    store.needClarification(
      response.sheet_name ?? store.selectedSheet ?? "",
      response.clarifications ?? [],
    );
    return null;
  }

  if (!response.workspace) {
    store.fail("The backend did not return a completed analysis.");
    return null;
  }

  const workspaces = useWorkspaceStore.getState();
  workspaces.invalidate(response.workspace.id);
  void workspaces.refresh();
  store.finish();
  return response.workspace;
}

export async function startIngestion(
  file: File,
  sheet?: string,
): Promise<WorkspaceMeta | null> {
  const signal = nextSignal();
  useAnalysisStore.getState().begin(file, sheet);

  try {
    const response = await processDatasetWithProgress(
      file,
      sheet,
      (event) => {
        if (!signal.aborted) {
          useAnalysisStore.getState().progress(event.stage, event.detail);
        }
      },
      signal,
    );
    if (signal.aborted) return null;
    return handleResponse(response);
  } catch (error) {
    if (signal.aborted || isAbort(error)) return null;
    useAnalysisStore.getState().fail(getErrorMessage(error));
    return null;
  }
}

export async function submitClarifications(): Promise<WorkspaceMeta | null> {
  const { file, selectedSheet, choices } = useAnalysisStore.getState();
  if (!file || !selectedSheet) return null;

  const signal = nextSignal();
  useAnalysisStore.getState().resolving();

  try {
    const response = await resolveDataset(
      file,
      choices,
      selectedSheet,
      signal,
    );
    if (signal.aborted) return null;
    return handleResponse(response);
  } catch (error) {
    if (signal.aborted || isAbort(error)) return null;
    useAnalysisStore.getState().fail(getErrorMessage(error));
    return null;
  }
}

export function cancelIngestion(): void {
  controller?.abort();
  controller = null;
  useAnalysisStore.getState().reset();
}