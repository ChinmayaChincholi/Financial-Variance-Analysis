import { create } from "zustand";
import type { WorkspaceDetail, WorkspaceMeta } from "../types/dataset";
import {
  deleteWorkspace,
  getWorkspace,
  listWorkspaces,
} from "../services/api/workspaceApi";

interface WorkspaceState {
  workspaces: WorkspaceMeta[];
  loaded: boolean;
  /** In-memory cache of opened workspaces (the source of truth is on disk). */
  details: Record<string, WorkspaceDetail>;

  refresh: () => Promise<void>;
  load: (id: string) => Promise<WorkspaceDetail>;
  invalidate: (id: string) => void;
  remove: (id: string) => Promise<void>;
}

export const useWorkspaceStore = create<WorkspaceState>((set, get) => ({
  workspaces: [],
  loaded: false,
  details: {},

  refresh: async () => {
    try {
      const workspaces = await listWorkspaces();
      set({ workspaces, loaded: true });
    } catch {
      // The list is a convenience; a failure must never break the app.
      set({ loaded: true });
    }
  },

  load: async (id) => {
    const cached = get().details[id];
    if (cached) return cached;
    const detail = await getWorkspace(id);
    set((state) => ({ details: { ...state.details, [id]: detail } }));
    return detail;
  },

  invalidate: (id) =>
    set((state) => {
      const next = { ...state.details };
      delete next[id];
      return { details: next };
    }),

  remove: async (id) => {
    await deleteWorkspace(id);
    set((state) => {
      const details = { ...state.details };
      delete details[id];
      return {
        details,
        workspaces: state.workspaces.filter((item) => item.id !== id),
      };
    });
  },
}));