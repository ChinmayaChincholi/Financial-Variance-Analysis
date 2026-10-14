import { Outlet } from "react-router-dom";
import { IS_WEB } from "../config/appMode";
import { DemoBanner } from "./DemoBanner";
import { Sidebar } from "./Sidebar";

export function Shell() {
  const app = (
    <div className="app">
      <Sidebar />
      <main className="mn">
        <Outlet />
      </main>
    </div>
  );

  if (!IS_WEB) return app;

  return (
    <div className="web-frame">
      <DemoBanner />
      {app}
    </div>
  );
}