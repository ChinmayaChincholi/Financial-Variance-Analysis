import { create } from "zustand";

import type {
  ClarificationRequest,
  DatasetSession,
} from "../types/dataset";

interface AnalysisState {
  file: File | null;
  session: DatasetSession | null;
  clarifications: ClarificationRequest[];
  clarificationChoices: Record<string, string>;
  processing: boolean;
  processingStage: string;
  error: string | null;

  setFile: (file: File | null) => void;

  setSession: (session: DatasetSession) => void;

  setClarifications: (
    clarifications: ClarificationRequest[],
  ) => void;

  setClarificationChoice: (
    field: string,
    value: string,
  ) => void;

  setProcessing: (
    processing: boolean,
    stage?: string,
  ) => void;

  setError: (error: string | null) => void;

  reset: () => void;
}

export const useAnalysisStore = create<AnalysisState>((set) => ({
  file: null,
  session: null,
  clarifications: [],
  clarificationChoices: {},
  processing: false,
  processingStage: "",
  error: null,

  setFile: (file) =>
    set({
      file,
      error: null,
    }),

  setSession: (session) =>
    set({
      session,
      clarifications: [],
      clarificationChoices: {},
      error: null,
    }),

  setClarifications: (clarifications) =>
    set({
      clarifications,
    }),

  setClarificationChoice: (field, value) =>
    set((state) => ({
      clarificationChoices: {
        ...state.clarificationChoices,
        [field]: value,
      },
    })),

  setProcessing: (processing, stage = "") =>
    set({
      processing,
      processingStage: stage,
    }),

  setError: (error) =>
    set({
      error,
      processing: false,
    }),

  reset: () =>
    set({
      file: null,
      session: null,
      clarifications: [],
      clarificationChoices: {},
      processing: false,
      processingStage: "",
      error: null,
    }),
}));