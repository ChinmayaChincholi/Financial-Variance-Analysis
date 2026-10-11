import { useEffect, useState } from "react";
import { Link, NavLink, useMatch, useNavigate } from "react-router-dom";
import { X } from "lucide-react";
import { BrandMark } from "./Brand";
import { useAnalysisStore } from "../state/analysisStore";
import { useWorkspaceStore } from "../state/workspaceStore";
import { cancelIngestion } from "../services/ingestionController";

export function Sidebar() {
  const navigate = useNavigate();
  const workspaces = useWorkspaceStore((state) => state.workspaces);
  const loaded = useWorkspaceStore((state) => state.loaded);
  const refresh = useWorkspaceStore((state) => state.refresh);
  const remove = useWorkspaceStore((state) => state.remove);
  const phase = useAnalysisStore((state) => state.phase);
  const match = useMatch("/workspace/:id/*");
  const activeId = match?.params.id ?? null;

  const [confirmingId, setConfirmingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  function startNewAnalysis() {
    if (phase !== "idle") cancelIngestion();
    navigate("/");
  }

  async function confirmDelete(id: string) {
    try {
      await remove(id);
      setDeleteError(null);
      setConfirmingId(null);
      if (id === activeId) navigate("/");
    } catch {
      setDeleteError("Could not delete that workspace. Please try again.");
    }
  }

  return (
    <aside className="sb">
      <Link to="/" className="sb-brand" onClick={startNewAnalysis}>
        <BrandMark size={22} />
        <span>Variance Studio</span>
      </Link>

      <button type="button" className="sb-new" onClick={startNewAnalysis}>
        + New analysis
      </button>

      <h4>Workspaces</h4>
      <nav className="sb-list" aria-label="Workspaces">
        {loaded && workspaces.length === 0 && (
          <p className="sb-empty">Analyses you run are saved here.</p>
        )}

        {workspaces.map((workspace) =>
          confirmingId === workspace.id ? (
            <div key={workspace.id} className="sb-confirm" role="alert">
              <span>Delete “{workspace.name}”?</span>
              <div>
                <button
                  type="button"
                  className="sb-yes"
                  onClick={() => void confirmDelete(workspace.id)}
                >
                  Delete
                </button>
                <button
                  type="button"
                  className="sb-no"
                  onClick={() => setConfirmingId(null)}
                >
                  Keep
                </button>
              </div>
            </div>
          ) : (
            <div key={workspace.id} className="sb-row">
              <NavLink
                to={`/workspace/${workspace.id}/summary`}
                className={() =>
                  workspace.id === activeId ? "sb-link on" : "sb-link"
                }
                title={`${workspace.filename} · ${workspace.sheet_name}`}
              >
                {workspace.name}
              </NavLink>
              <button
                type="button"
                className="sb-delete"
                aria-label={`Delete workspace ${workspace.name}`}
                onClick={() => {
                  setDeleteError(null);
                  setConfirmingId(workspace.id);
                }}
              >
                <X size={14} aria-hidden="true" />
              </button>
            </div>
          ),
        )}
        {deleteError && <p className="sb-error">{deleteError}</p>}
      </nav>

      <span className="pill sb-offline">Offline · stays on this PC</span>
    </aside>
  );
}