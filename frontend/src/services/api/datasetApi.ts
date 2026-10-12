import { API_BASE_URL, readErrorMessage } from "./client";
import type {
  DatasetProgressEvent,
  DatasetStreamEvent,
  IngestionResponse,
} from "../../types/dataset";

function buildForm(file: File, sheetName?: string): FormData {
  const formData = new FormData();
  formData.append("file", file);
  if (sheetName) {
    formData.append("sheet_name", sheetName);
  }
  return formData;
}

/**
 * POST a file and read the backend's NDJSON stream of real stage events.
 *
 * The backend uses NDJSON because the request is a multipart POST. That
 * gives streaming progress without a second websocket/SSE connection.
 */
async function streamIngestion(
  path: string,
  formData: FormData,
  onProgress: (event: DatasetProgressEvent) => void,
  signal?: AbortSignal,
): Promise<IngestionResponse> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    body: formData,
    signal,
    headers: { Accept: "application/x-ndjson" },
  });

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(
        response,
        `Processing failed with status ${response.status}`,
      ),
    );
  }

  if (!response.body) {
    throw new Error("The backend did not provide a processing stream.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalResponse: IngestionResponse | null = null;

  function handleLine(line: string): void {
    if (!line.trim()) return;
    const event = JSON.parse(line) as DatasetStreamEvent;
    if (event.type === "progress") {
      onProgress(event);
    } else if (event.type === "error") {
      throw new Error(event.message);
    } else if (event.type === "result") {
      finalResponse = event.data;
    }
  }

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      handleLine(line);
    }
  }

  // The final NDJSON line may not end with a newline.
  buffer += decoder.decode();
  handleLine(buffer);

  if (!finalResponse) {
    throw new Error("The backend processing stream ended without a result.");
  }
  return finalResponse;
}

/** First pass: import, detect columns, and (if sure) analyse. */
export function processDatasetWithProgress(
  file: File,
  sheetName: string | undefined,
  onProgress: (event: DatasetProgressEvent) => void,
  signal?: AbortSignal,
): Promise<IngestionResponse> {
  return streamIngestion(
    "/api/dataset/process/stream",
    buildForm(file, sheetName),
    onProgress,
    signal,
  );
}

/** Second pass: apply the user's answers and stream the remaining stages. */
export function resolveDatasetWithProgress(
  file: File,
  choices: Record<string, string>,
  sheetName: string,
  onProgress: (event: DatasetProgressEvent) => void,
  signal?: AbortSignal,
): Promise<IngestionResponse> {
  const formData = buildForm(file, sheetName);
  formData.append("choices", JSON.stringify(choices));
  return streamIngestion(
    "/api/dataset/resolve/stream",
    formData,
    onProgress,
    signal,
  );
}