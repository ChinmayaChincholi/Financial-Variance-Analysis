import { apiRequest } from "./client";
import type {
  IngestionResponse,
} from "../../types/dataset";

export async function processDataset(
  file: File,
  sheetName?: string,
): Promise<IngestionResponse> {
  const formData = new FormData();

  formData.append("file", file);

  if (sheetName) {
    formData.append("sheet_name", sheetName);
  }

  return apiRequest<IngestionResponse>("/api/process", {
    method: "POST",
    body: formData,
  });
}

export async function resolveDataset(
  file: File,
  choices: Record<string, string>,
  sheetName?: string,
): Promise<IngestionResponse> {
  const formData = new FormData();

  formData.append("file", file);
  formData.append("choices", JSON.stringify(choices));

  if (sheetName) {
    formData.append("sheet_name", sheetName);
  }

  return apiRequest<IngestionResponse>("/api/process/resolve", {
    method: "POST",
    body: formData,
  });
}