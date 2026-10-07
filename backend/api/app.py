"""
FastAPI application entry point.

This file is intentionally kept small.

Responsibilities:
- Create the FastAPI application.
- Register API routers.

It does NOT:
- read Excel files
- perform ingestion
- perform financial analysis
- build analysis results
- generate Excel exports
"""

from fastapi import FastAPI

from api.routes.dataset_routes import router as dataset_router
from api.routes.health_routes import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Financial Revenue & Cost Analysis API",
        version="1.0.0",
    )

    app.include_router(health_router)
    app.include_router(dataset_router)

    return app


app = create_app()