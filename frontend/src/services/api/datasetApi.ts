import {
  apiRequest,
  API_BASE_URL,
} from "./client";

import type {
  DatasetProgressEvent,
  DatasetStreamEvent,
  IngestionResponse,
  WorkbookInspectionResponse,
} from "../../types/dataset";


export async function inspectWorkbook(
  file: File,
  signal?: AbortSignal,
): Promise<WorkbookInspectionResponse> {
  const formData =
    new FormData();

  formData.append(
    "file",
    file,
  );

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
  const formData =
    new FormData();

  formData.append(
    "file",
    file,
  );

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


/**
 * Process a dataset while receiving real backend stage events.
 *
 * The backend uses NDJSON because the request is a multipart POST.
 * This gives us streaming progress without requiring a second
 * websocket/SSE connection.
 */
export async function processDatasetWithProgress(
  file: File,
  sheetName: string | undefined,
  onProgress: (
    event: DatasetProgressEvent,
  ) => void,
  signal?: AbortSignal,
): Promise<IngestionResponse> {
  const formData =
    new FormData();

  formData.append(
    "file",
    file,
  );

  if (sheetName) {
    formData.append(
      "sheet_name",
      sheetName,
    );
  }

  const response = await fetch(
    `${API_BASE_URL}/api/dataset/process/stream`,
    {
      method: "POST",
      body: formData,
      signal,
      headers: {
        Accept:
          "application/x-ndjson",
      },
    },
  );

  if (!response.ok) {
    let message =
      `Processing failed with status ${response.status}`;

    try {
      const data =
        await response.json();

      if (data?.detail) {
        message = data.detail;
      } else if (data?.message) {
        message = data.message;
      }
    } catch {
      // Keep default message.
    }

    throw new Error(message);
  }

  if (!response.body) {
    throw new Error(
      "The backend did not provide a processing stream.",
    );
  }

  const reader =
    response.body.getReader();

  const decoder =
    new TextDecoder();

  let buffer = "";

  let finalResponse:
    | IngestionResponse
    | null = null;

  while (true) {
    const {
      value,
      done,
    } = await reader.read();

    if (done) {
      break;
    }

    buffer += decoder.decode(
      value,
      {
        stream: true,
      },
    );

    const lines =
      buffer.split("\n");

    buffer =
      lines.pop() ?? "";

    for (const line of lines) {
      if (!line.trim()) {
        continue;
      }

      const event =
        JSON.parse(
          line,
        ) as DatasetStreamEvent;

      if (
        event.type ===
        "progress"
      ) {
        onProgress(event);
        continue;
      }

      if (
        event.type ===
        "error"
      ) {
        throw new Error(
          event.message,
        );
      }

      if (
        event.type ===
        "result"
      ) {
        finalResponse =
          event.data;
      }
    }
  }

  /*
   * The final NDJSON line may not end with \n.
   */
  if (buffer.trim()) {
    const event =
      JSON.parse(
        buffer,
      ) as DatasetStreamEvent;

    if (
      event.type ===
      "progress"
    ) {
      onProgress(event);
    } else if (
      event.type ===
      "error"
    ) {
      throw new Error(
        event.message,
      );
    } else if (
      event.type ===
      "result"
    ) {
      finalResponse =
        event.data;
    }
  }

  if (!finalResponse) {
    throw new Error(
      "The backend processing stream ended without a result.",
    );
  }

  return finalResponse;
}


export async function resolveDataset(
  file: File,
  choices: Record<string, string>,
  sheetName: string,
  signal?: AbortSignal,
): Promise<IngestionResponse> {
  const formData =
    new FormData();

  formData.append(
    "file",
    file,
  );

  formData.append(
    "sheet_name",
    sheetName,
  );

  formData.append(
    "choices",
    JSON.stringify(
      choices,
    ),
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