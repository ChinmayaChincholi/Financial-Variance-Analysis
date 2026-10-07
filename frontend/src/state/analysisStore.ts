import { create } from "zustand";

import type {
  ClarificationRequest,
  DatasetSession,
} from "../types/dataset";

interface AnalysisState {
  file: File | null;

  session: DatasetSession | null;

  sheets: string[];

  selectedSheet: string | null;

  clarifications: ClarificationRequest[];

  clarificationChoices: Record<
    string,
    string
  >;

  processing: boolean;

  processingStage: string;

  error: string | null;

  setFile: (file: File | null) => void;

  setSession: (
    session: DatasetSession,
  ) => void;

  setSheets: (sheets: string[]) => void;

  setSelectedSheet: (
    sheet: string | null,
  ) => void;

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

  setError: (
    error: string | null,
  ) => void;

  reset: () => void;
}

export const useAnalysisStore =
  create<AnalysisState>((set) => ({
    file: null,

    session: null,

    sheets: [],

    selectedSheet: null,

    clarifications: [],

    clarificationChoices: {},

    processing: false,

    processingStage: "",

    error: null,

    setFile: (file) =>
      set({
        file,
        session: null,
        sheets: [],
        selectedSheet: null,
        clarifications: [],
        clarificationChoices: {},
        processing: false,
        processingStage: "",
        error: null,
      }),

    setSession: (session) =>
      set({
        session,
        clarifications: [],
        clarificationChoices: {},
        processing: false,
        processingStage: "",
        error: null,
      }),

    setSheets: (sheets) =>
      set({
        sheets,
      }),

    setSelectedSheet: (selectedSheet) =>
      set({
        selectedSheet,
      }),

    setClarifications: (
      clarifications,
    ) =>
      set({
        clarifications,
      }),

    setClarificationChoice: (
      field,
      value,
    ) =>
      set((state) => ({
        clarificationChoices: {
          ...state.clarificationChoices,
          [field]: value,
        },
      })),

    setProcessing: (
      processing,
      stage = "",
    ) =>
      set({
        processing,
        processingStage: stage,
      }),

    setError: (error) =>
      set({
        error,
        processing: false,
        processingStage: "",
      }),

    reset: () =>
      set({
        file: null,
        session: null,
        sheets: [],
        selectedSheet: null,
        clarifications: [],
        clarificationChoices: {},
        processing: false,
        processingStage: "",
        error: null,
      }),
  }));