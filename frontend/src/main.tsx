import ReactDOM from "react-dom/client";

import {
  BrowserRouter,
} from "react-router-dom";

import App from "./app/App";

import { ErrorBoundary } from "./components/ErrorBoundary"; // ← CHANGED (added)

import "./styles/globals.css";

ReactDOM.createRoot(
  document.getElementById(
    "root",
  )!,
).render(
  <ErrorBoundary> {/* ← CHANGED (wrapper added) */}
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </ErrorBoundary>,
);