import {
  Navigate,
  Route,
  Routes,
} from "react-router-dom";

import {
  AnalysisResultPage,
} from "../pages/AnalysisResultPage";

import {
  AnalysisTypePage,
} from "../pages/AnalysisTypePage";

import {
  ClarificationPage,
} from "../pages/ClarificationPage";

import {
  HomePage,
} from "../pages/HomePage";

import {
  OptionsPage,
} from "../pages/OptionsPage";

import {
  PeriodSelectionPage,
} from "../pages/PeriodSelectionPage";

import {
  ProcessingPage,
} from "../pages/ProcessingPage";

import {
  RegionSelectionPage,
} from "../pages/RegionSelectionPage";

import {
  ScopePage,
} from "../pages/ScopePage";

import {
  SheetSelectionPage,
} from "../pages/SheetSelectionPage";

import {
  UniqueProjectsPage,
} from "../pages/UniqueProjectsPage";

export default function App() {
  return (
    <Routes>
      <Route
        path="/"
        element={<HomePage />}
      />

      <Route
        path="/processing"
        element={
          <ProcessingPage />
        }
      />

      <Route
        path="/sheets"
        element={
          <SheetSelectionPage />
        }
      />

      <Route
        path="/clarification"
        element={
          <ClarificationPage />
        }
      />

      <Route
        path="/scope"
        element={<ScopePage />}
      />

      {/* ------------------------------------------------ */}
      {/* Options */}
      {/* ------------------------------------------------ */}

      <Route
        path="/options/project"
        element={
          <OptionsPage />
        }
      />

      <Route
        path="/options/region/:region"
        element={
          <OptionsPage />
        }
      />

      {/* ------------------------------------------------ */}
      {/* Analysis type */}
      {/* ------------------------------------------------ */}

      <Route
        path="/analysis-options/project/:metric"
        element={
          <AnalysisTypePage />
        }
      />

      <Route
        path="/analysis-options/region/:region/:metric"
        element={
          <AnalysisTypePage />
        }
      />

      {/* ------------------------------------------------ */}
      {/* Unique */}
      {/* ------------------------------------------------ */}

      <Route
        path="/options/project/unique/:metric"
        element={
          <UniqueProjectsPage />
        }
      />

      <Route
        path="/options/region/:region/unique/:metric"
        element={
          <UniqueProjectsPage />
        }
      />

      {/* ------------------------------------------------ */}
      {/* Period selection */}
      {/* ------------------------------------------------ */}

      <Route
        path="/periods/project/:metric/:period"
        element={
          <PeriodSelectionPage />
        }
      />

      <Route
        path="/periods/region/:region/:metric/:period"
        element={
          <PeriodSelectionPage />
        }
      />

      {/* ------------------------------------------------ */}
      {/* Analysis result */}
      {/* ------------------------------------------------ */}

      <Route
        path="/analysis/project/:metric/:period/:selectionId"
        element={
          <AnalysisResultPage />
        }
      />

      <Route
        path="/analysis/region/:region/:metric/:period/:selectionId"
        element={
          <AnalysisResultPage />
        }
      />

      {/* ------------------------------------------------ */}
      {/* Region selection */}
      {/* ------------------------------------------------ */}

      <Route
        path="/regions"
        element={
          <RegionSelectionPage />
        }
      />

      {/* ------------------------------------------------ */}
      {/* Fallback */}
      {/* ------------------------------------------------ */}

      <Route
        path="*"
        element={
          <Navigate
            to="/"
            replace
          />
        }
      />
    </Routes>
  );
}