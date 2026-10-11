import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { Ring } from "../components/Brand";
import { DetailTable } from "../components/DetailTable";
import { FilterBar } from "../components/FilterBar";
import { SentenceText } from "../components/SentenceCard";
import { TotalsTable } from "../components/TotalsTable";
import { BridgeChart } from "../components/charts/BridgeChart";
import { VarianceBars } from "../components/charts/VarianceBars";
import { exportAnalysisToExcel } from "../services/api/exportApi";
import { useWorkspaceStore } from "../state/workspaceStore";
import type { WorkspaceDetail } from "../types/dataset";
import {
  METRIC_LABEL,
  buildBridge,
  buildDetailRows,
  buildMovers,
  filtersToParams,
  makeExportFilename,
  resolveFilters,
  scopeLabel,
  stateToRaw,
  type RawFilters,
} from "../utils/analysisModel";
import { getErrorMessage } from "../utils/errors";
import {
  chooseUnit,
  formatSignedCompact,
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

  const resolved = useMemo(
    () =>
      resolveFilters(session, {
        metric: params.get("metric"),
        scope: params.get("scope"),
        region: params.get("region"),
        compare: params.get("compare"),
        period: params.get("period"),
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

  const context = [
    METRIC_LABEL[state.metric],
    scopeLabel(state),
    state.compare === "totals" ? "Project totals" : option?.label,
  ]
    .filter(Boolean)
    .join(" · ");

  const model = useMemo(() => {
    if (!period || !option) return null;
    return {
      bridge: buildBridge(period, projectCol, option),
      movers: buildMovers(period, projectCol),
      rows: buildDetailRows(period, projectCol, option),
    };
  }, [period, option, projectCol]);

  const unit = useMemo(() => {
    if (!model?.bridge) {
      const largest = model?.rows.reduce(
        (max, row) => Math.max(max, Math.abs(row.start), Math.abs(row.end)),
        0,
      );
      return chooseUnit(largest ?? 0);
    }
    return chooseUnit(
      Math.max(
        Math.abs(model.bridge.start),
        Math.abs(model.bridge.end),
        Math.abs(model.bridge.net),
      ),
    );
  }, [model]);

  async function runExport() {
    const table = state.compare === "totals" ? analysis?.unique : period;
    if (!table) return;
    setExporting(true);
    setExportError(null);
    try {
      await exportAnalysisToExcel(
        { rows: table.rows, columns: table.columns },
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

      {state.compare === "totals" ? (
        totals ? (
          <>
            <div className="card hero">
              <div className="hero-top">
                <span className="pill">{context}</span>
              </div>
              <p className="hero-sentence">
                Aggregated {METRIC_LABEL[state.metric].toLowerCase()} for every
                unique project, from {totals.columns[1]} to{" "}
                {totals.columns[totals.columns.length - 1]}.
              </p>
            </div>
            <TotalsTable
              table={totals}
              projectColumn={projectCol}
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
                {formatSignedCompact(net)}
              </span>
            </div>
            <p className="hero-sentence">
              <SentenceText sentence={period.summary_sentence} />
            </p>
          </div>

          <div className="charts">
            {model.bridge && <BridgeChart model={model.bridge} unit={unit} />}
            <VarianceBars items={model.movers} unit={unit} />
          </div>

          <DetailTable
            rows={model.rows}
            startLabel={option.start_period ?? "Start"}
            endLabel={option.end_period ?? "End"}
            unit={unit}
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