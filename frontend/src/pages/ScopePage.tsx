import {
  FolderKanban,
  Map,
} from "lucide-react";

import {
  useNavigate,
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

export function ScopePage() {
  const navigate =
    useNavigate();

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

  const hasRegion =
    Boolean(
      session.mapping.region_col,
    ) &&
    session.regions.length > 0;

  return (
    <main className="app-shell">
      <div className="page-container">
        <PageHeader
          title="Choose Analysis"
          subtitle="Select how you want to analyze the dataset."
        />

        <div className="card-grid two-column">
          <AnalysisCard
            title="Project-wise Analysis"
            description="Analyze revenue and cost across individual projects."
            icon={
              <FolderKanban
                size={24}
              />
            }
            onClick={() =>
              navigate(
                "/options/project",
              )
            }
          />

          <AnalysisCard
            title="Region-wise Analysis"
            description={
              hasRegion
                ? "Analyze revenue and cost by region."
                : "Region data was not detected in this dataset."
            }
            icon={
              <Map size={24} />
            }
            disabled={!hasRegion}
            onClick={() =>
              navigate("/regions")
            }
          />
        </div>
      </div>
    </main>
  );
}