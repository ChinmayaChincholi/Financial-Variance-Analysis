import {
  useNavigate,
  useParams,
} from "react-router-dom";

import {
  AnalysisTable,
} from "../components/AnalysisTable";

import {
  ExportButton,
} from "../components/ExportButton";

import {
  PageHeader,
} from "../navigation/PageHeader";

import {
  useAnalysisStore,
} from "../state/analysisStore";

import type {
  Metric,
  Scope,
} from "../types/dataset";

export function UniqueProjectsPage() {
  const navigate =
    useNavigate();

  const {
      metric,
      region,
    } = useParams<{
      metric: Metric;
      region?: string;
    }>();

    const scope: Scope =
      region !== undefined
        ? "region"
        : "project";

  const session =
    useAnalysisStore(
      (state) => state.session,
    );

  if (!session) {
    navigate("/", {
      replace: true,
    });

    return null;
  }

  if (
    scope !== "project" &&
    scope !== "region"
  ) {
    navigate("/scope", {
      replace: true,
    });

    return null;
  }

  if (
    metric !== "revenue" &&
    metric !== "cost"
  ) {
    navigate("/scope", {
      replace: true,
    });

    return null;
  }

  const decodedRegion =
    region
      ? decodeURIComponent(region)
      : undefined;

  const result =
    scope === "region"
      ? session.regionWise[
          decodedRegion ?? ""
        ]?.[metric].unique
      : session.projectWise[
          metric
        ].unique;

  if (!result) {
    return (
      <main className="app-shell">
        <div className="page-container">
          <PageHeader
            title="No Data"
          />

          <div className="empty-state">
            No unique project data
            is available for this
            selection.
          </div>
        </div>
      </main>
    );
  }

  const scopeName =
    scope === "region"
      ? decodedRegion!
      : "Project";

  const metricLabel =
    metric === "revenue"
      ? "Revenue"
      : "Cost";

  return (
    <main className="app-shell">
      <div className="page-container">
        <PageHeader
          title={`Unique ${metricLabel}`}
          subtitle={`${scopeName}-wise aggregated values`}
        >
          <ExportButton
            result={result}
            filename={`${scopeName}-${metric}-unique.xlsx`}
          />
        </PageHeader>

        <AnalysisTable
          result={result}
        />
      </div>
    </main>
  );
}