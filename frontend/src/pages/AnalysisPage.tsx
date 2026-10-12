import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { AllProjectsTable } from "../components/AllProjectsTable";
import { Ring } from "../components/Brand";
import { BreakdownTable } from "../components/BreakdownTable";
import { FilterBar } from "../components/FilterBar";
import { SentenceText } from "../components/SentenceCard";
import { BridgeChart } from "../components/charts/BridgeChart";
import { TrendChart } from "../components/charts/TrendChart";
import { exportAnalysisToExcel } from "../services/api/exportApi";
import { useWorkspaceStore } from "../state/workspaceStore";
import type { WorkspaceDetail } from "../types/dataset";
import {
  METRIC_LABEL,
  buildBridge,
  buildDetailRows,
  buildTrend,
  filtersToParams,
  makeExportFilename,
  regionColumnFor,
  resolveFilters,
  scopeLabel,
  stateToRaw,
  withRegionColumn,
  type RawFilters,
} from "../utils/analysisModel";
import { getErrorMessage } from "../utils/errors";
import {
  DEFAULT_CURRENCY,
  formatSignedMoney,
  toNumber,
} from "../utils/formatting";

function useWorkspaceDetail(id: string) {
  const load = useWorkspaceStore((state) => state.load);
  const [detail, setDetail] = useState<WorkspaceDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setDetail(null);
    setError(null);
    load(id)
      .then((loaded) => {
        if (!cancelled) setDetail(loaded);
      })
      .catch((reason: unknown) => {
        if (!cancelled) setError(getErrorMessage(reason));
      });
    return () => {
      cancelled = true;
    };
  }, [id, load]);

  return { detail, error };
}

export function AnalysisPage() {
  const { id = "" } = useParams();
  const { detail, error } = useWorkspaceDetail(id);

  if (error) {
    return (
      <div className="col center-note">
        <h1 className="display">Couldn&apos;t open this workspace</h1>
        <p className="muted">{error}</p>
        <Link to="/" className="btn">
          Back to start
        </Link>
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="col center-note" role="status" aria-live="polite">
        <Ring size={28} />
        <p className="muted">Opening your analysis…</p>
      </div>
    );
  }

  return <AnalysisView key={id} detail={detail} />;
}

function AnalysisView({ detail }: { detail: WorkspaceDetail }) {
  const { meta, session } = detail;
  const [params, setParams] = useSearchParams();
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const currency = session.summary.currency ?? DEFAULT_CURRENCY;

  const resolved = useMemo(
    () =>
      resolveFilters(session, {
        metric: params.get("metric"),
        scope: params.get("scope"),
        region: params.get("region"),
        compare: params.get("compare"),
        period: params.get("period"),
        all: params.get("all"),
      }),
    [session, params],
  );

  // Keep the URL canonical so the view can be reloaded or bookmarked.
  useEffect(() => {
    const canonical = filtersToParams(resolved.state).toString();
    if (canonical !== params.toString()) {
      setParams(canonical, { replace: true });
    }
  }, [resolved, params, setParams]);

  function update(patch: RawFilters) {
    const next = resolveFilters(session, {
      ...stateToRaw(resolved.state),
      ...patch,
    });
    setParams(filtersToParams(next.state), { replace: true });
    setExportError(null);
  }

  const { state, analysis, option, period } = resolved;
  const projectCol = session.mapping.project_col;
  const regionColumn = regionColumnFor(session, state);

  const context = [
    METRIC_LABEL[state.metric],
    scopeLabel(state),
    state.allProjects ? "Monthly totals" : option?.label,
  ]
    .filter(Boolean)
    .join(" · ");

  const model = useMemo(() => {
    if (!period || !option) return null;
    return {
      bridge: buildBridge(period, projectCol, option),
      trend: buildTrend(session, state, option),
      rows: buildDetailRows(period, projectCol, option),
    };
  }, [period, option, projectCol, session, state]);

  async function runExport() {
    const source = state.allProjects ? analysis?.unique : period;
    if (!source) return;
    setExporting(true);
    setExportError(null);
    try {
      await exportAnalysisToExcel(
        withRegionColumn(
          { rows: source.rows, columns: source.columns },
          projectCol,
          regionColumn,
        ),
        makeExportFilename(meta.name, state, option),
      );
    } catch (reason) {
      setExportError(getErrorMessage(reason));
    } finally {
      setExporting(false);
    }
  }

  const net = period ? toNumber(period.sum_to_reach) : 0;
  const totals = analysis?.unique ?? null;
  const legacy = !session.trend;

  return (
    <div className="analysis">
      <Link to={`/workspace/${meta.id}/summary`} className="back-link">
        <ArrowLeft size={15} aria-hidden="true" />
        Back to conversation · {meta.name}
      </Link>

      <FilterBar
        resolved={resolved}
        regions={session.regions}
        onChange={update}
      />

      {state.allProjects ? (
        totals ? (
          <>
            <div className="card hero">
              <div className="hero-top">
                <span className="pill">{context}</span>
              </div>
              <p className="hero-sentence">
                Monthly {METRIC_LABEL[state.metric].toLowerCase()} for every
                project, from {totals.columns[1]} to{" "}
                {totals.columns[totals.columns.length - 1]}.
              </p>
            </div>
            <AllProjectsTable
              table={totals}
              projectColumn={projectCol}
              currency={currency}
              regionColumn={regionColumn}
              exporting={exporting}
              exportError={exportError}
              onExport={() => void runExport()}
            />
          </>
        ) : (
          <EmptyState />
        )
      ) : period && option && model ? (
        <>
          <div className="card hero">
            <div className="hero-top">
              <span className="pill">{context}</span>
              <span className={`big ${net >= 0 ? "up" : "dn"}`}>
                {formatSignedMoney(net, currency)}
              </span>
            </div>
            <p className="hero-sentence">
              <SentenceText
                sentence={period.summary_sentence}
                currency={currency}
              />
            </p>
          </div>

          <div className="charts">
            {model.bridge && (
              <BridgeChart model={model.bridge} currency={currency} />
            )}
            {model.trend ? (
              <TrendChart model={model.trend} currency={currency} />
            ) : (
              legacy && (
                <div className="card chart-card notice-card" role="note">
                  <div className="chart-head">
                    <span>Monthly trend</span>
                  </div>
                  <p className="muted">
                    This workspace was saved before monthly trends and currency
                    detection existed. Re-import the file to add them. Amounts
                    are shown in {currency.symbol || "the dataset's currency"}{" "}
                    until then.
                  </p>
                </div>
              )
            )}
          </div>

          <BreakdownTable
            rows={model.rows}
            startLabel={option.start_period ?? "Start"}
            endLabel={option.end_period ?? "End"}
            currency={currency}
            regionColumn={regionColumn}
            exporting={exporting}
            exportError={exportError}
            onExport={() => void runExport()}
          />
        </>
      ) : (
        <EmptyState />
      )}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="card empty-state">
      <h2 className="display">Nothing to compare for this selection</h2>
      <p className="muted">
        Try another metric, region or comparison. Only options with complete
        data can be analysed.
      </p>
    </div>
  );
}