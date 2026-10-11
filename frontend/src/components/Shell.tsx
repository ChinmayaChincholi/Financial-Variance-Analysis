import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";

export function Shell() {
  return (
    <div className="app">
      <Sidebar />
      <main className="mn">
        <Outlet />
      </main>
    </div>
  );
}