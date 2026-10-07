import type {
  ClarificationRequest,
  IngestionResponse,
} from "./dataset";

export interface ProcessDatasetResponse extends IngestionResponse {}

export interface ResolveDatasetResponse extends IngestionResponse {}

export interface ResolveDatasetPayload {
  file: File;
  choices: Record<string, string>;
}

export interface ApiErrorResponse {
  detail?: string;
  message?: string;
  error?: string;
}

export interface ApiClientError extends Error {
  status?: number;
}