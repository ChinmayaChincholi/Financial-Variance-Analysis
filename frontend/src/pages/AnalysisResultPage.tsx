import {
  useMemo,
} from "react";

import {
  useNavigate,
  useParams,
} from "react-router-dom";

import {
  AnalysisTable,
} from "../components/AnalysisTable";

import {
  SummaryBanner,
} from "../components/SummaryBanner";

import {
  PageHeader,
} from "../navigation/PageHeader";

import {
  useAnalysisStore,
} from "../state/analysisStore";

import type {
  AnalysisResult,
  Metric,
  PeriodType,
  Scope,
} from "../types/dataset";

export function AnalysisResultPage() {
  const navigate =
    useNavigate();

  const {
      metric,
      period,
      selectionId,
      region,
    } = useParams<{
      metric: Metric;
      period: PeriodType;
      selectionId: string;
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

  const decodedRegion =
    region
      ? decodeURIComponent(region)
      : undefined;

  const result =
    useMemo<AnalysisResult | null>(
      () => {
        if (!session) {
          return null;
        }

        if (
          scope !== "project" &&
          scope !== "region"
        ) {
          return null;
        }

        if (
          metric !== "revenue" &&
          metric !== "cost"
        ) {
          return null;
        }

        if (
          period !== "MoM" &&
          period !== "QoQ" &&
          period !== "YoY"
        ) {
          return null;
        }

        const metricAnalysis =
          scope === "region"
            ? session.regionWise[
                decodedRegion ?? ""
              ]?.[metric]
            : session.projectWise[
                metric
              ];

        if (!metricAnalysis) {
          return null;
        }

        const analysisMap =
          period === "MoM"
            ? metricAnalysis.mom
            : period === "QoQ"
              ? metricAnalysis.qoq
              : metricAnalysis.yoy;

        return (
          analysisMap[
            selectionId ?? ""
          ] ?? null
        );
      },
      [
        decodedRegion,
        metric,
        period,
        scope,
        selectionId,
        session,
      ],
    );

  if (!session) {
    navigate("/", {
      replace: true,
    });

    return null;
  }

  if (!result) {
    return (
      <main className="app-shell">
        <div className="page-container">
          <PageHeader
            title="Analysis Result"
          />

          <div className="empty-state">
            No precomputed result
            was found for this
            selection.
          </div>
        </div>
      </main>
    );
  }

  const metricLabel =
    metric === "revenue"
      ? "Revenue"
      : "Cost";

  const periodLabel =
    period === "MoM"
      ? "Month-on-Month"
      : period === "QoQ"
        ? "Quarter-on-Quarter"
        : "Year-on-Year";

  return (
    <main className="app-shell">
      <div className="page-container">
        <PageHeader
          title={`${periodLabel} ${metricLabel}`}
          subtitle={
            decodedRegion
              ? `${decodedRegion} region-wise analysis`
              : "Project-wise analysis"
          }
        />

        <SummaryBanner
          text={
            result.summary_sentence
          }
          sumToReach={
            result.sum_to_reach
          }
        />

        <AnalysisTable
          result={result}
        />
      </div>
    </main>
  );
}