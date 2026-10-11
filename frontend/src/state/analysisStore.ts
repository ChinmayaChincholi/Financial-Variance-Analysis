import { create } from "zustand";
import type { ClarificationRequest } from "../types/dataset";

/**
 * State of the "conversation" (attach -> processing -> questions) only.
 * Finished analyses live on the backend as workspaces, not in memory.
 */
export type Phase =
  | "idle"
  | "processing"
  | "sheet"
  | "clarify"
  | "resolving"
  | "error";

interface ConversationState {
  phase: Phase;
  file: File | null;
  sheets: string[];
  selectedSheet: string | null;
  clarifications: ClarificationRequest[];
  choices: Record<string, string>;
  /** Index (into the UI step list) of the stage the backend is on. */
  stageIndex: number;
  stageDetails: Record<string, string>;
  startedAt: number | null;
  error: string | null;

  begin: (file: File, sheet?: string) => void;
  progress: (stage: string, detail?: string) => void;
  needSheet: (sheets: string[]) => void;
  needClarification: (
    sheetName: string,
    clarifications: ClarificationRequest[],
  ) => void;
  choose: (field: string, value: string) => void;
  resolving: () => void;
  fail: (message: string) => void;
  finish: () => void;
  reset: () => void;
}

/** Backend stage names, in the order the backend reports them. */
export const BACKEND_STAGES = [
  "Importing dataset",
  "Detecting columns",
  "Computing project-wise analysis",
  "Computing region-wise analysis",
  "Finalizing results",
] as const;

const initial = {
  phase: "idle" as Phase,
  file: null,
  sheets: [] as string[],
  selectedSheet: null,
  clarifications: [] as ClarificationRequest[],
  choices: {} as Record<string, string>,
  stageIndex: 0,
  stageDetails: {} as Record<string, string>,
  startedAt: null,
  error: null,
};

export const useAnalysisStore = create<ConversationState>((set) => ({
  ...initial,

  begin: (file, sheet) =>
    set({
      ...initial,
      phase: "processing",
      file,
      selectedSheet: sheet ?? null,
      startedAt: Date.now(),
    }),

  progress: (stage, detail) =>
    set((state) => {
      const index = BACKEND_STAGES.indexOf(
        stage as (typeof BACKEND_STAGES)[number],
      );
      return {
        stageIndex: index > state.stageIndex ? index : state.stageIndex,
        stageDetails: detail
          ? { ...state.stageDetails, [stage]: detail }
          : state.stageDetails,
      };
    }),

  needSheet: (sheets) => set({ phase: "sheet", sheets, error: null }),

  needClarification: (sheetName, clarifications) =>
    set({
      phase: "clarify",
      selectedSheet: sheetName,
      clarifications,
      choices: {},
      error: null,
    }),

  choose: (field, value) =>
    set((state) => ({ choices: { ...state.choices, [field]: value } })),

  resolving: () => set({ phase: "resolving", startedAt: Date.now() }),

  fail: (message) => set({ phase: "error", error: message }),

  finish: () => set({ ...initial }),

  reset: () => set({ ...initial }),
}));