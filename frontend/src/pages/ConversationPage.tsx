import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Check } from "lucide-react";
import { AssistantRow, FileChip } from "../components/Messages";
import { BrandMark, Ring } from "../components/Brand";
import { Composer } from "../components/Composer";
import { useElapsed } from "../hooks/useElapsed";
import { useIngestion } from "../hooks/useIngestion";
import {
  BACKEND_STAGES,
  useAnalysisStore,
} from "../state/analysisStore";
import { useWorkspaceStore } from "../state/workspaceStore";
import type {
  ClarificationCandidate,
  ClarificationRequest,
} from "../types/dataset";
import { formatElapsed } from "../utils/formatting";

/* ------------------------------------------------------------------ */
/* Idle: attach a file                                                 */
/* ------------------------------------------------------------------ */

function Landing() {
  const { attach } = useIngestion();
  const workspaces = useWorkspaceStore((state) => state.workspaces);
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function accept(file: File | undefined) {
    if (file) setError(attach(file));
  }

  return (
    <div className="col landing">
      <div className="landing-mark">
        <BrandMark size={34} />
      </div>
      <h1 className="display">What moved this quarter?</h1>
      <p className="lead">
        Attach your dataset. I&apos;ll read it, ask only if I&apos;m unsure, and
        prepare every comparison.
      </p>

      <div
        className={`card dropzone ${dragging ? "drag" : ""}`}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          accept(event.dataTransfer.files?.[0]);
        }}
      >
        <div className="dz-title">Drop an Excel file here</div>
        <p className="muted">.xlsx or .xls · processed entirely offline</p>
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
            accept(file);
          }}
        />
      </div>

      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}

      {workspaces.length > 0 && (
        <p className="muted recent">
          Or reopen:{" "}
          {workspaces.slice(0, 3).map((workspace) => (
            <Link
              key={workspace.id}
              className="pill pill-link"
              to={`/workspace/${workspace.id}/summary`}
            >
              {workspace.name}
            </Link>
          ))}
        </p>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Processing: real stages, spinner ring                               */
/* ------------------------------------------------------------------ */

const STEPS = [
  { active: "Importing dataset", done: "Imported dataset" },
  { active: "Detecting columns", done: "Detected columns" },
  {
    active: "Computing project-wise analysis",
    done: "Computed project-wise analysis",
  },
  {
    active: "Computing region-wise analysis",
    done: "Computed region-wise analysis",
  },
  { active: "Preparing your comparisons", done: "Prepared your comparisons" },
];

function Processing() {
  const { cancel } = useIngestion();
  const phase = useAnalysisStore((state) => state.phase);
  const stageIndex = useAnalysisStore((state) => state.stageIndex);
  const details = useAnalysisStore((state) => state.stageDetails);
  const startedAt = useAnalysisStore((state) => state.startedAt);
  const elapsed = useElapsed(startedAt);
  const resolving = phase === "resolving";

  return (
    <AssistantRow icon={<Ring size={28} />}>
      <div className="msg" role="status" aria-live="polite">
        {resolving ? "Applying your choices…" : "Reading your workbook…"}
      </div>

      {resolving ? (
        <div className="steps">
          <div className="step">
            <Ring size={18} />
            <strong>Computing every comparison</strong>
          </div>
        </div>
      ) : (
        <ol className="steps">
          {STEPS.map((step, index) => {
            const state =
              index < stageIndex
                ? "done"
                : index === stageIndex
                  ? "active"
                  : "pending";
            const detail = details[BACKEND_STAGES[index]];
            return (
              <li key={step.active} className={`step ${state}`}>
                {state === "done" && (
                  <Check size={16} className="ok" aria-hidden="true" />
                )}
                {state === "active" && <Ring size={18} />}
                {state === "pending" && (
                  <span className="step-dot" aria-hidden="true">
                    ○
                  </span>
                )}
                <span>
                  {state === "done" ? step.done : step.active}
                  {state === "done" && detail && (
                    <span className="muted"> {detail}</span>
                  )}
                </span>
              </li>
            );
          })}
        </ol>
      )}

      <p className="muted small">
        Elapsed {formatElapsed(elapsed)} ·{" "}
        <button type="button" className="link-button inline" onClick={cancel}>
          Cancel
        </button>
      </p>
    </AssistantRow>
  );
}

/* ------------------------------------------------------------------ */
/* Questions                                                           */
/* ------------------------------------------------------------------ */

const NONE_VALUE = "__none__";

function sheetQuestionTitle(count: number) {
  return `Your workbook has ${count} sheets. Which one holds the financial data?`;
}

function SheetQuestion() {
  const { chooseSheet } = useIngestion();
  const sheets = useAnalysisStore((state) => state.sheets);

  return (
    <AssistantRow>
      <div className="msg">{sheetQuestionTitle(sheets.length)}</div>
      <div className="card q-card">
        <div className="muted small">Choose a sheet</div>
        {sheets.map((sheet) => (
          <button
            key={sheet}
            type="button"
            className="opt"
            onClick={() => chooseSheet(sheet)}
          >
            <strong>{sheet}</strong>
          </button>
        ))}
      </div>
    </AssistantRow>
  );
}

function questionTitle(question: ClarificationRequest): {
  title: string;
  context: string | null;
} {
  const [firstLine, ...rest] = question.message.split("\n\n");
  const context = rest.join("\n\n").trim() || null;

  if (question.field === "header_row") {
    return { title: "Which row holds the column headers?", context };
  }
  if (question.field === "project_name") {
    return { title: "Which column contains the project name?", context };
  }
  if (question.field === "region") {
    return { title: "Which column contains the region?", context };
  }
  if (question.field.startsWith("metric_block_")) {
    return { title: "Is this block Revenue or Cost?", context: context ?? firstLine };
  }
  return { title: firstLine, context };
}

interface Option {
  value: string;
  label: string;
  candidate?: ClarificationCandidate;
}

function OptionDetail({ candidate }: { candidate: ClarificationCandidate }) {
  const samples = candidate.sample_values.slice(0, 3).map((value) => String(value));
  const reasons = candidate.reasons.slice(0, 2);
  return (
    <>
      {samples.length > 0 && (
        <div className="muted small">sample: {samples.join(" · ")}</div>
      )}
      {reasons.length > 0 && (
        <div className="muted small">{reasons.join(" · ")}</div>
      )}
    </>
  );
}

function Questions() {
  const { submit } = useIngestion();
  const questions = useAnalysisStore((state) => state.clarifications);
  const choices = useAnalysisStore((state) => state.choices);
  const choose = useAnalysisStore((state) => state.choose);

  const answered = questions.filter((question) => choices[question.field]);
  const currentIndex = questions.findIndex((question) => !choices[question.field]);
  const complete = answered.length === questions.length;

  const metricOnly = questions.every((question) =>
    question.field.startsWith("metric_block_"),
  );
  const intro = metricOnly
    ? "Your headers don't say which months are revenue and which are cost."
    : "I couldn't be certain about a few things in your file.";
  const heading =
    questions.length === 1 ? "One quick check." : `${questions.length} quick checks.`;

  return (
    <AssistantRow>
      <div className="msg">
        {heading} {intro}
      </div>

      {questions.map((question, index) => {
        const { title, context } = questionTitle(question);
        const selected = choices[question.field];
        const dimmed = currentIndex !== -1 && index > currentIndex;
        const isMetric = question.field.startsWith("metric_block_");

        const options: Option[] = question.candidates.map((candidate) => ({
          value: candidate.column,
          label: candidate.column,
          candidate,
        }));
        if (question.allow_none) {
          options.push({ value: NONE_VALUE, label: "No such column" });
        }

        return (
          <div
            key={question.field}
            className={`card q-card ${dimmed ? "dim" : ""}`}
            aria-disabled={dimmed}
          >
            <div className="muted small">
              Question {index + 1} of {questions.length}
            </div>
            <div className="q-title">{title}</div>
            {context && <div className="muted q-context">{context}</div>}

            {!dimmed &&
              options.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  className={`opt ${selected === option.value ? "sel" : ""}`}
                  aria-pressed={selected === option.value}
                  onClick={() => choose(question.field, option.value)}
                >
                  <strong>{option.label}</strong>
                  {!isMetric && option.candidate && (
                    <OptionDetail candidate={option.candidate} />
                  )}
                </button>
              ))}
          </div>
        );
      })}

      <p className="q-actions">
        <button
          type="button"
          className="btn"
          disabled={!complete}
          onClick={submit}
        >
          Continue
        </button>
        <span className="muted small">I only ask when I can&apos;t be sure.</span>
      </p>
    </AssistantRow>
  );
}

/* ------------------------------------------------------------------ */
/* Error                                                               */
/* ------------------------------------------------------------------ */

function Failure() {
  const { retry } = useIngestion();
  const error = useAnalysisStore((state) => state.error);
  const reset = useAnalysisStore((state) => state.reset);

  return (
    <AssistantRow>
      <div className="msg">I couldn&apos;t finish reading that file.</div>
      <div className="card q-card">
        <div className="error-message" role="alert">
          {error ?? "Something went wrong."}
        </div>
        <p className="q-actions">
          <button type="button" className="btn" onClick={retry}>
            Try again
          </button>
          <button type="button" className="ghost" onClick={reset}>
            Start over
          </button>
        </p>
      </div>
    </AssistantRow>
  );
}

/* ------------------------------------------------------------------ */

export function ConversationPage() {
  const phase = useAnalysisStore((state) => state.phase);
  const file = useAnalysisStore((state) => state.file);

  if (phase === "idle" || !file) {
    return <Landing />;
  }

  return (
    <>
      <FileChip name={file.name} size={file.size} />
      <div className="col">
        {(phase === "processing" || phase === "resolving") && <Processing />}
        {phase === "sheet" && <SheetQuestion />}
        {phase === "clarify" && <Questions />}
        {phase === "error" && <Failure />}
      </div>
      <Composer />
    </>
  );
}