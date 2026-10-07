import { Navigate, Route, Routes } from "react-router-dom";

import { HomePage } from "../pages/HomePage";
import { ProcessingPage } from "../pages/ProcessingPage";
import { ClarificationPage } from "../pages/ClarificationPage";
import { ScopePage } from "../pages/ScopePage";
import { OptionsPage } from "../pages/OptionsPage";
import { RegionSelectionPage } from "../pages/RegionSelectionPage";
import { UniqueProjectsPage } from "../pages/UniqueProjectsPage";
import { PeriodSelectionPage } from "../pages/PeriodSelectionPage";
import { AnalysisResultPage } from "../pages/AnalysisResultPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/processing" element={<ProcessingPage />} />
      <Route path="/clarification" element={<ClarificationPage />} />

      <Route path="/scope" element={<ScopePage />} />

      <Route
        path="/options/:scope/:metric"
        element={<OptionsPage />}
      />

      <Route
        path="/regions"
        element={<RegionSelectionPage />}
      />

      <Route
        path="/options/region/:region/:metric"
        element={<OptionsPage />}
      />

      <Route
        path="/unique/:scope/:metric"
        element={<UniqueProjectsPage />}
      />

      <Route
        path="/unique/region/:region/:metric"
        element={<UniqueProjectsPage />}
      />

      <Route
        path="/periods/:scope/:metric/:period/:region?"
        element={<PeriodSelectionPage />}
      />

      <Route
        path="/analysis/:scope/:metric/:period/:selectionId/:region?"
        element={<AnalysisResultPage />}
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}