import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Shell } from "../components/Shell";
import { AnalysisPage } from "../pages/AnalysisPage";
import { ConversationPage } from "../pages/ConversationPage";
import { SummaryPage } from "../pages/SummaryPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Shell />}>
          <Route path="/" element={<ConversationPage />} />
          <Route path="/workspace/:id/summary" element={<SummaryPage />} />
          <Route path="/workspace/:id" element={<AnalysisPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}