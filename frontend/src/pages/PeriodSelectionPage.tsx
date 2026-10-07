import { useNavigate, useParams } from "react-router-dom";

import { PeriodSelector } from "../components/PeriodSelector";
import { PageHeader } from "../navigation/PageHeader";
import { useAnalysisStore } from "../state/analysisStore";
import type {
  Metric,
  PeriodType,
  Scope,
} from "../types/dataset";

export function PeriodSelectionPage() {
  const navigate = useNavigate();

  const {
    scope,
    metric,
    period,
    region,
  } = useParams<{
    scope: Scope;
    metric: Metric;
    period: PeriodType;
    region?: string;
  }>();

  const session = useAnalysisStore(
    (state) => state.session,
  );

  if (!session) {
    navigate("/");
    return null;
  }

  if (
    (scope !== "project" &&
      scope !== "region") ||
    (metric !== "revenue" &&
      metric !== "cost") ||
    (period !== "MoM" &&
      period !== "QoQ" &&
      period !== "YoY")
  ) {
    navigate("/scope");
    return null;
  }

  const periodKey =
    period.toLowerCase() as "mom" | "qoq" | "yoy";

  const options =
    session.periods[metric][periodKey];

  const decodedRegion = region
    ? decodeURIComponent(region)
    : undefined;

  const title =
    period === "MoM"
      ? "Month-on-Month Analysis"
      : period === "QoQ"
        ? "Quarter-on-Quarter Analysis"
        : "Year-on-Year Analysis";

  function handleSelect(optionId: string) {
    const encodedRegion = decodedRegion
      ? `/${encodeURIComponent(decodedRegion)}`
      : "";

    navigate(
      `/analysis/${scope}/${metric}/${period}/${encodeURIComponent(optionId)}${encodedRegion}`,
    );
  }

  return (
    <main className="app-shell">
      <div className="page-container">
        <PageHeader
          title={title}
          subtitle="Select the comparison period."
        />

        <PeriodSelector
          options={options}
          onSelect={(option) =>
            handleSelect(option.id)
          }
        />
      </div>
    </main>
  );
}