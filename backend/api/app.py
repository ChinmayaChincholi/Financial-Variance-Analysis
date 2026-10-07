"""
FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.dataset_routes import (
    router as dataset_router,
)
from api.routes.export_routes import (
    router as export_router,
)
from api.routes.health_routes import (
    router as health_router,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Financial Revenue & Cost Analysis API",
        version="1.0.0",
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

    app.include_router(
        health_router
    )

    app.include_router(
        dataset_router
    )

    app.include_router(
        export_router
    )

    return app


app = create_app()