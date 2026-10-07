import { apiRequest } from "./client";

import type {
  IngestionResponse,
  WorkbookInspectionResponse,
} from "../../types/dataset";

export async function inspectWorkbook(
  file: File,
  signal?: AbortSignal,
): Promise<WorkbookInspectionResponse> {
  const formData = new FormData();

  formData.append("file", file);

  return apiRequest<WorkbookInspectionResponse>(
    "/api/dataset/sheets",
    {
      method: "POST",
      body: formData,
      signal,
    },
  );
}

export async function processDataset(
  file: File,
  sheetName?: string,
  signal?: AbortSignal,
): Promise<IngestionResponse> {
  const formData = new FormData();

  formData.append("file", file);

  if (sheetName) {
    formData.append(
      "sheet_name",
      sheetName,
    );
  }

  return apiRequest<IngestionResponse>(
    "/api/dataset/process",
    {
      method: "POST",
      body: formData,
      signal,
    },
  );
}

export async function resolveDataset(
  file: File,
  choices: Record<string, string>,
  sheetName: string,
  signal?: AbortSignal,
): Promise<IngestionResponse> {
  const formData = new FormData();

  formData.append("file", file);

  formData.append(
    "sheet_name",
    sheetName,
  );

  formData.append(
    "choices",
    JSON.stringify(choices),
  );

  return apiRequest<IngestionResponse>(
    "/api/dataset/resolve",
    {
      method: "POST",
      body: formData,
      signal,
    },
  );
}