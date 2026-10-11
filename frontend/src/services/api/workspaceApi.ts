import { apiRequest } from "./client";
import type { WorkspaceDetail, WorkspaceMeta } from "../../types/dataset";

export async function listWorkspaces(): Promise<WorkspaceMeta[]> {
  const data = await apiRequest<{ workspaces: WorkspaceMeta[] }>(
    "/api/workspaces",
  );
  return data.workspaces;
}

export function getWorkspace(id: string): Promise<WorkspaceDetail> {
  return apiRequest<WorkspaceDetail>(
    `/api/workspaces/${encodeURIComponent(id)}`,
  );
}

export async function deleteWorkspace(id: string): Promise<void> {
  await apiRequest<{ deleted: boolean }>(
    `/api/workspaces/${encodeURIComponent(id)}`,
    { method: "DELETE" },
  );
}