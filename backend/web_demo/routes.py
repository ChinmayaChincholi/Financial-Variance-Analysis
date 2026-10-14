"""Endpoints that exist only in the web demo."""

from fastapi import APIRouter, Request

router = APIRouter(
    prefix="/api/demo",
    tags=["Demo"],
)


@router.get("/config")
def demo_config(request: Request) -> dict:
    """Limits the interface shows to visitors (read from the server settings)."""
    settings = request.app.state.web_settings
    return {
        "mode": "web",
        "retention_hours": settings.retention_hours,
        "max_upload_mb": settings.max_upload_mb,
        "max_workspaces": settings.max_workspaces,
    }