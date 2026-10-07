"""
Health-check API routes.

This router only exposes application status.
"""

from fastapi import APIRouter


router = APIRouter(
    prefix="/api",
    tags=["Health"],
)


@router.get("/health")
def health_check() -> dict:
    return {
        "status": "ok"
    }