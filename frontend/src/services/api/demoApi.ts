import { apiRequest } from "./client";

/** Limits reported by the web-demo server (see /api/demo/config). */
export interface DemoConfig {
  mode: "web";
  retention_hours: number;
  max_upload_mb: number;
  max_workspaces: number;
}

export function getDemoConfig(): Promise<DemoConfig> {
  return apiRequest<DemoConfig>("/api/demo/config");
}