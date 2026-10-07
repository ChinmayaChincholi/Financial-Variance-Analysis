import {
  useNavigate,
} from "react-router-dom";

import {
  RegionCard,
} from "../components/RegionCard";

import {
  PageHeader,
} from "../navigation/PageHeader";

import {
  useAnalysisStore,
} from "../state/analysisStore";

export function RegionSelectionPage() {
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

  return (
    <main className="app-shell">
      <div className="page-container">
        <PageHeader
          title="Select Region"
          subtitle="Choose a region to continue with region-wise analysis."
        />

        {session.regions.length ===
        0 ? (
          <div className="empty-state">
            No regions were detected
            in this dataset.
          </div>
        ) : (
          <div className="region-grid">
            {session.regions.map(
              (region) => (
                <RegionCard
                  key={region}
                  region={region}
                  onClick={() =>
                    navigate(
                      `/options/region/${encodeURIComponent(
                        region,
                      )}`,
                    )
                  }
                />
              ),
            )}
          </div>
        )}
      </div>
    </main>
  );
}