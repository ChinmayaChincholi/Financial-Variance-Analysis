import { useEffect } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { AssistantRow, FileChip } from "../components/Messages";
import { Ring } from "../components/Brand";
import { Composer } from "../components/Composer";
import { useWorkspaceStore } from "../state/workspaceStore";
import { DEFAULT_CURRENCY } from "../utils/formatting";
import type {
  CurrencyInfo,
  CurrencySource,
  DatasetSummary,
  WorkspaceMeta,
} from "../types/dataset";

const METRIC_NAMES: Record<string, string> = {
  revenue: "Revenue",
  cost: "Cost",
};

function joinWithAnd(values: string[]): string {
  if (values.length <= 1) return values.join("");
  return `${values.slice(0, -1).join(", ")} and ${values[values.length - 1]}`;
}

const SOURCE_TEXT: Record<CurrencySource, string> = {
  headers: "found in your column headers",
  values: "found in your cell values",
  both: "found in your headers and cell values",
  assumed: "assumed, because no currency was found in your data",
};

function currencyText(currency: CurrencyInfo): string {
  if (currency.mixed) {
    return `Mixed currencies detected (${currency.found.join(", ")}). Amounts are shown without a symbol and are not converted.`;
  }
  return `${currency.name} (${currency.symbol}) · ${SOURCE_TEXT[currency.source]}`;
}

interface SummaryRow {
  label: string;
  value: string;
  warn?: boolean;
}

function summaryRows(workspace: WorkspaceMeta): SummaryRow[] {
  const summary: DatasetSummary = workspace.summary;
  const rows: SummaryRow[] = [];

  rows.push({
    label: "File",
    value: `${workspace.filename} · sheet ${workspace.sheet_name}`,
  });

  rows.push({
    label: "Rows",
    value: `${summary.row_count.toLocaleString("en-US")} rows · ${summary.unique_projects.toLocaleString("en-US")} unique projects`,
  });

  if (summary.regions.length > 0) {
    const shown = summary.regions.slice(0, 8).join(", ");
    const extra =
      summary.regions.length > 8 ? ` +${summary.regions.length - 8} more` : "";
    rows.push({
      label: "Regions",
      value: `${summary.regions.length} region${summary.regions.length === 1 ? "" : "s"}: ${shown}${extra}`,
    });
  } else {
    rows.push({ label: "Regions", value: "No region column found" });
  }

  if (summary.first_month && summary.last_month) {
    rows.push({
      label: "Period covered",
      value: `${summary.first_month} – ${summary.last_month} (${summary.month_count} month${summary.month_count === 1 ? "" : "s"})`,
    });
  }

  rows.push({
    label: "Metrics found",
    value: summary.metrics.length
      ? joinWithAnd(summary.metrics.map((metric) => METRIC_NAMES[metric] ?? metric))
      : "None",
  });

  const comparisons: string[] = [];
  if (summary.comparisons.mom > 0) comparisons.push("Month-on-Month");
  if (summary.comparisons.qoq > 0) comparisons.push("Quarter-on-Quarter");
  if (summary.comparisons.yoy > 0) comparisons.push("Year-on-Year");
  rows.push({
    label: "Comparisons ready",
    value: comparisons.length ? comparisons.join(" · ") : "Project totals only",
  });

  const currency = summary.currency ?? DEFAULT_CURRENCY;
  rows.push({
    label: "Currency",
    value: summary.currency
      ? currencyText(currency)
      : `${currency.name} (${currency.symbol}) · assumed`,
    warn: currency.mixed,
  });

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
              {summaryRows(workspace).map((row) => (
                <div key={row.label} className="kv-row">
                  <dt className="muted">{row.label}</dt>
                  <dd className={row.warn ? "warn" : undefined}>{row.value}</dd>
                </div>
              ))}
            </dl>
          </div>
          {!workspace.summary.currency && (
            <div className="notice" role="note">
              This workspace was saved with an earlier version. Re-import the
              file to add the monthly trend chart and currency detection.
            </div>
          )}
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