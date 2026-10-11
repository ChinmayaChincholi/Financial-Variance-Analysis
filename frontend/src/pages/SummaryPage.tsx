import { useEffect } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { AssistantRow, FileChip } from "../components/Messages";
import { Ring } from "../components/Brand";
import { Composer } from "../components/Composer";
import { useWorkspaceStore } from "../state/workspaceStore";
import type { DatasetSummary, WorkspaceMeta } from "../types/dataset";

const METRIC_NAMES: Record<string, string> = {
  revenue: "Revenue",
  cost: "Cost",
};

function joinWithAnd(values: string[]): string {
  if (values.length <= 1) return values.join("");
  return `${values.slice(0, -1).join(", ")} and ${values[values.length - 1]}`;
}

function summaryRows(workspace: WorkspaceMeta): [string, string][] {
  const summary: DatasetSummary = workspace.summary;
  const rows: [string, string][] = [];

  rows.push(["File", `${workspace.filename} · sheet ${workspace.sheet_name}`]);

  rows.push([
    "Rows",
    `${summary.row_count.toLocaleString("en-IN")} rows · ${summary.unique_projects.toLocaleString("en-IN")} unique projects`,
  ]);

  if (summary.regions.length > 0) {
    const shown = summary.regions.slice(0, 8).join(", ");
    const extra =
      summary.regions.length > 8 ? ` +${summary.regions.length - 8} more` : "";
    rows.push([
      "Regions",
      `${summary.regions.length} region${summary.regions.length === 1 ? "" : "s"}: ${shown}${extra}`,
    ]);
  } else {
    rows.push(["Regions", "No region column found"]);
  }

  if (summary.first_month && summary.last_month) {
    rows.push([
      "Period covered",
      `${summary.first_month} – ${summary.last_month} (${summary.month_count} month${summary.month_count === 1 ? "" : "s"})`,
    ]);
  }

  rows.push([
    "Metrics found",
    summary.metrics.length
      ? joinWithAnd(summary.metrics.map((metric) => METRIC_NAMES[metric] ?? metric))
      : "None",
  ]);

  const comparisons: string[] = [];
  if (summary.comparisons.mom > 0) comparisons.push("Month-on-Month");
  if (summary.comparisons.qoq > 0) comparisons.push("Quarter-on-Quarter");
  if (summary.comparisons.yoy > 0) comparisons.push("Year-on-Year");
  rows.push([
    "Comparisons ready",
    comparisons.length ? comparisons.join(" · ") : "Project totals only",
  ]);

  return rows;
}

export function SummaryPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const workspaces = useWorkspaceStore((state) => state.workspaces);
  const loaded = useWorkspaceStore((state) => state.loaded);
  const refresh = useWorkspaceStore((state) => state.refresh);

  useEffect(() => {
    void refresh();
  }, [refresh, id]);

  const workspace = workspaces.find((item) => item.id === id);

  if (!workspace) {
    if (!loaded) {
      return (
        <div className="col center-note">
          <Ring size={28} />
        </div>
      );
    }
    return (
      <div className="col center-note">
        <h1 className="display">Workspace not found</h1>
        <p className="muted">
          It may have been deleted. You can start a new analysis at any time.
        </p>
        <Link to="/" className="btn">
          Back to start
        </Link>
      </div>
    );
  }

  return (
    <>
      <FileChip name={workspace.filename} size={workspace.file_size} />
      <div className="col">
        <AssistantRow>
          <div className="display msg-large">The analysis is complete!</div>
          <div className="card summary-card">
            <div className="muted small summary-title">Dataset summary</div>
            <dl className="kv">
              {summaryRows(workspace).map(([label, value]) => (
                <div key={label} className="kv-row">
                  <dt className="muted">{label}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
          </div>
          <p className="q-actions">
            <button
              type="button"
              className="btn"
              onClick={() => navigate(`/workspace/${workspace.id}`)}
            >
              Go to analysis →
            </button>
          </p>
        </AssistantRow>
      </div>
      <Composer />
    </>
  );
}