import {
  BarChart3,
  CalendarDays,
  CircleDollarSign,
} from "lucide-react";

import {
  useNavigate,
  useParams,
} from "react-router-dom";

import {
  AnalysisCard,
} from "../components/AnalysisCard";

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

export function AnalysisTypePage() {
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
    (scope !== "project" &&
      scope !== "region") ||
    (metric !== "revenue" &&
      metric !== "cost")
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

  const analysis =
    scope === "region"
      ? session.regionWise[
          decodedRegion ?? ""
        ]?.[metric]
      : session.projectWise[
          metric
        ];

  if (!analysis) {
    return (
      <main className="app-shell">
        <div className="page-container">
          <PageHeader
            title="No Data"
          />

          <div className="empty-state">
            No {metric} data is
            available for this
            selection.
          </div>
        </div>
      </main>
    );
  }

  const prefix =
    scope === "region"
      ? `/periods/region/${encodeURIComponent(
          decodedRegion!,
        )}/${metric}`
      : `/periods/project/${metric}`;

  const metricLabel =
    metric === "revenue"
      ? "Revenue"
      : "Cost";

  return (
    <main className="app-shell">
      <div className="page-container">
        <PageHeader
          title={`Analysis by ${metricLabel}`}
          subtitle="Choose the comparison type."
        />

        <div className="card-grid">
          <AnalysisCard
            title="Month-on-Month"
            description="Compare the latest three available months."
            icon={
              <BarChart3
                size={24}
              />
            }
            disabled={
              analysis.mom &&
              Object.keys(
                analysis.mom,
              ).length === 0
            }
            onClick={() =>
              navigate(
                `${prefix}/MoM`,
              )
            }
          />

          <AnalysisCard
            title="Quarter-on-Quarter"
            description="Compare every valid consecutive fiscal-quarter pair."
            icon={
              <CalendarDays
                size={24}
              />
            }
            disabled={
              analysis.qoq &&
              Object.keys(
                analysis.qoq,
              ).length === 0
            }
            onClick={() =>
              navigate(
                `${prefix}/QoQ`,
              )
            }
          />

          <AnalysisCard
            title="Year-on-Year"
            description="Compare every valid consecutive completed fiscal-year pair."
            icon={
              <CircleDollarSign
                size={24}
              />
            }
            disabled={
              analysis.yoy &&
              Object.keys(
                analysis.yoy,
              ).length === 0
            }
            onClick={() =>
              navigate(
                `${prefix}/YoY`,
              )
            }
          />
        </div>
      </div>
    </main>
  );
}