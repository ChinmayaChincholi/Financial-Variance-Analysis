import { BarChart3, CircleDollarSign } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";

import { AnalysisCard } from "../components/AnalysisCard";
import { PageHeader } from "../navigation/PageHeader";
import type {
  Metric,
  Scope,
} from "../types/dataset";

export function OptionsPage() {
  const navigate = useNavigate();

  const {
    scope,
    metric,
    region,
  } = useParams<{
    scope: Scope;
    metric: Metric;
    region?: string;
  }>();

  if (
    scope !== "project" &&
    scope !== "region"
  ) {
    navigate("/scope");
    return null;
  }

  if (
    metric !== "revenue" &&
    metric !== "cost"
  ) {
    navigate("/scope");
    return null;
  }

  const title =
    metric === "revenue"
      ? "Revenue Analysis"
      : "Cost Analysis";

  const scopeLabel =
    scope === "project"
      ? "Project-wise"
      : region
        ? region
        : "Region-wise";

  const basePath = region
    ? `/options/region/${encodeURIComponent(region)}/${metric}`
    : `/options/${scope}/${metric}`;

  return (
    <main className="app-shell">
      <div className="page-container">
        <PageHeader
          title={title}
          subtitle={`${scopeLabel} ${metric} analysis`}
        />

        <div className="card-grid">
          <AnalysisCard
            title="View Unique Projects"
            description="View the unique projects and their aggregated values."
            icon={<BarChart3 size={24} />}
            onClick={() => {
              if (region) {
                navigate(
                  `/unique/region/${encodeURIComponent(region)}/${metric}`,
                );
              } else {
                navigate(
                  `/unique/${scope}/${metric}`,
                );
              }
            }}
          />

          <AnalysisCard
            title="Month-on-Month Analysis"
            description="Compare monthly values and identify month-to-month variations."
            icon={<BarChart3 size={24} />}
            onClick={() =>
              navigate(
                `${basePath.replace(
                  "/options/",
                  "/periods/",
                )}/MoM`,
              )
            }
          />

          <AnalysisCard
            title="Quarter-on-Quarter Analysis"
            description="Compare consecutive quarters and their variations."
            icon={<BarChart3 size={24} />}
            onClick={() =>
              navigate(
                `${basePath.replace(
                  "/options/",
                  "/periods/",
                )}/QoQ`,
              )
            }
          />

          <AnalysisCard
            title="Year-on-Year Analysis"
            description="Compare yearly values and identify annual variations."
            icon={<CircleDollarSign size={24} />}
            onClick={() =>
              navigate(
                `${basePath.replace(
                  "/options/",
                  "/periods/",
                )}/YoY`,
              )
            }
          />
        </div>
      </div>
    </main>
  );
}