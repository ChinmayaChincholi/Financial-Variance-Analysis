import {
  BarChart3,
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

export function OptionsPage() {
  const navigate =
    useNavigate();

  const {
      region,
    } = useParams<{
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

  const decodedRegion =
    region
      ? decodeURIComponent(region)
      : undefined;

  if (
    scope === "region" &&
    !decodedRegion
  ) {
    navigate("/regions", {
      replace: true,
    });

    return null;
  }

  const metricAnalysis =
    (
      metric: Metric,
    ) =>
      scope === "region"
        ? session.regionWise[
            decodedRegion!
          ]?.[metric]
        : session.projectWise[
            metric
          ];

  const revenue =
    metricAnalysis("revenue");

  const cost =
    metricAnalysis("cost");

  if (!revenue && !cost) {
    return (
      <main className="app-shell">
        <div className="page-container">
          <PageHeader
            title="No Analysis Data"
          />

          <div className="empty-state">
            No Revenue or Cost data
            is available for this
            selection.
          </div>
        </div>
      </main>
    );
  }

  const prefix =
    scope === "region"
      ? `/options/region/${encodeURIComponent(
          decodedRegion!,
        )}`
      : "/options/project";

  const analysisPrefix =
    scope === "region"
      ? `/analysis-options/region/${encodeURIComponent(
          decodedRegion!,
        )}`
      : "/analysis-options/project";

  const scopeLabel =
    scope === "region"
      ? `${decodedRegion} Region-wise`
      : "Project-wise";

  const revenueAvailable =
    Boolean(revenue?.unique);

  const costAvailable =
    Boolean(cost?.unique);

  const revenueAnalysisAvailable =
    Boolean(
      revenue &&
        (
          revenue.mom &&
          Object.keys(
            revenue.mom,
          ).length
        ) ||
        (
          revenue.qoq &&
          Object.keys(
            revenue.qoq,
          ).length
        ) ||
        (
          revenue.yoy &&
          Object.keys(
            revenue.yoy,
          ).length
        ),
    );

  const costAnalysisAvailable =
    Boolean(
      cost &&
        (
          cost.mom &&
          Object.keys(
            cost.mom,
          ).length
        ) ||
        (
          cost.qoq &&
          Object.keys(
            cost.qoq,
          ).length
        ) ||
        (
          cost.yoy &&
          Object.keys(
            cost.yoy,
          ).length
        ),
    );

  return (
    <main className="app-shell">
      <div className="page-container">
        <PageHeader
          title={`${scopeLabel} Analysis`}
          subtitle="Choose the revenue/cost view you want to open."
        />

        <div className="card-grid">
          <AnalysisCard
            title="View Unique Projects & Revenue"
            description="View aggregated revenue for each unique project."
            icon={
              <BarChart3
                size={24}
              />
            }
            disabled={
              !revenueAvailable
            }
            onClick={() =>
              navigate(
                `${prefix}/unique/revenue`,
              )
            }
          />

          <AnalysisCard
            title="View Unique Projects & Cost"
            description="View aggregated cost for each unique project."
            icon={
              <BarChart3
                size={24}
              />
            }
            disabled={
              !costAvailable
            }
            onClick={() =>
              navigate(
                `${prefix}/unique/cost`,
              )
            }
          />

          <AnalysisCard
            title="Analysis by Revenue"
            description="Compare revenue month-on-month, quarter-on-quarter or year-on-year."
            icon={
              <BarChart3
                size={24}
              />
            }
            disabled={
              !revenueAnalysisAvailable
            }
            onClick={() =>
              navigate(
                `${analysisPrefix}/revenue`,
              )
            }
          />

          <AnalysisCard
            title="Analysis by Cost"
            description="Compare cost month-on-month, quarter-on-quarter or year-on-year."
            icon={
              <CircleDollarSign
                size={24}
              />
            }
            disabled={
              !costAnalysisAvailable
            }
            onClick={() =>
              navigate(
                `${analysisPrefix}/cost`,
              )
            }
          />
        </div>
      </div>
    </main>
  );
}