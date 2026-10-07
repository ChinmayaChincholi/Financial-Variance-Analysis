import type {
  DatasetSession,
  IngestionResponse,
} from "./dataset";

export interface SheetListResponse {
  filename: string;
  sheets: string[];
}

export interface ProcessDatasetResponse
  extends IngestionResponse {}

export interface ResolveDatasetResponse
  extends IngestionResponse {}

export interface ExportRequest {
  rows: Record<string, unknown>[];
  columns: string[];
  sheet_name?: string;
  filename?: string;
}

export type SessionOrNull =
  DatasetSession | null;