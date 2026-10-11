"""
FastAPI application entry point.

In development the React app runs on Vite (port 5173) and proxies /api here.
In the packaged, fully offline setup this same server also serves the built
frontend from frontend/dist, so one process is the entire application.
"""

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from api.routes.dataset_routes import router as dataset_router
from api.routes.export_routes import router as export_router
from api.routes.health_routes import router as health_router
from api.routes.workspace_routes import router as workspace_router

FRONTEND_DIR_ENV = "VARIANCE_STUDIO_FRONTEND_DIR"


def _frontend_dist_dir() -> Path | None:
    override = os.environ.get(FRONTEND_DIR_ENV)
    if override:
        candidate = Path(override).expanduser()
    else:
        # backend/api/app.py -> project root / frontend / dist
        candidate = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if (candidate / "index.html").is_file():
        return candidate.resolve()
    return None


def _mount_frontend(app: FastAPI) -> None:
    dist = _frontend_dist_dir()
    if dist is None:
        return

    index_file = dist / "index.html"

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str) -> FileResponse:
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found.")
        if full_path:
            candidate = (dist / full_path).resolve()
            if candidate.is_file() and dist in candidate.parents:
                return FileResponse(candidate)
        # Client-side routes (e.g. /workspace/<id>) fall back to the app shell.
        return FileResponse(index_file)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Financial Revenue & Cost Analysis API",
        version="2.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(dataset_router)
    app.include_router(workspace_router)
    app.include_router(export_router)

    # Must be registered last so it never shadows an API route.
    _mount_frontend(app)

    return app


app = create_app()