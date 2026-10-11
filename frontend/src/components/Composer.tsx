import { useRef, useState } from "react";
import { useIngestion } from "../hooks/useIngestion";

/** The only input in the app: attach a file. No typing. */
export function Composer() {
  const { attach } = useIngestion();
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="composer-wrap">
      <div className="card composer">
        <span className="muted composer-text">
          No typing needed. Attach an Excel file to start a new analysis.
        </span>
        <button
          type="button"
          className="btn"
          onClick={() => inputRef.current?.click()}
        >
          Attach file
        </button>
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.xls"
          hidden
          onChange={(event) => {
            const file = event.target.files?.[0];
            event.target.value = "";
            if (file) setError(attach(file));
          }}
        />
      </div>
      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}
    </div>
  );
}