import {
  Navigate,
  Outlet,
} from "react-router-dom";

import {
  useAnalysisStore,
} from "../state/analysisStore";

export function RequireSession() {
  const session =
    useAnalysisStore(
      (state) => state.session,
    );

  if (!session) {
    return (
      <Navigate
        to="/"
        replace
      />
    );
  }

  return <Outlet />;
}