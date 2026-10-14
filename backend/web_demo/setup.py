"""
Turns the FastAPI application into the hosted web demo.

Called from api.app.create_app() only when VARIANCE_STUDIO_MODE=web. In the
default (desktop) mode none of this runs and the application behaves exactly
as the packaged offline version does.
"""

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from storage.workspace_store import set_store
from web_demo.middleware import DemoMiddleware, SelectiveGZipMiddleware
from web_demo.routes import router as demo_router
from web_demo.settings import WebSettings
from web_demo.visitors import VisitorWorkspaceStores

logger = logging.getLogger("variance_studio.web")


def configure_web_app(app: FastAPI) -> WebSettings:
    """
    Install the web-demo behaviour on the app.

    Must run before the frontend catch-all route is registered, so the
    /api/demo routes are not shadowed by it.
    """
    settings = WebSettings.from_env()
    stores = VisitorWorkspaceStores(max_workspaces=settings.max_workspaces)

    # Every get_store() call in the services and routes now resolves to the
    # store of the visitor making the request.
    set_store(stores)

    app.state.web_settings = settings
    app.state.visitor_stores = stores

    app.include_router(demo_router)

    # Added last = outermost. The demo middleware runs first, so size and
    # concurrency limits apply before anything else touches the request.
    app.add_middleware(SelectiveGZipMiddleware)
    app.add_middleware(DemoMiddleware, settings=settings)

    return settings


async def _cleanup_loop(
        stores: VisitorWorkspaceStores,
        settings: WebSettings,
) -> None:
    max_age_seconds = settings.retention_hours * 3600
    while True:
        try:
            removed = await asyncio.to_thread(
                stores.purge_idle, max_age_seconds
            )
            if removed:
                logger.info("Removed expired data of %d visitor(s).", removed)
        except Exception:  # keep the sweep alive whatever happens
            logger.exception("Cleaning up expired visitor data failed.")
        await asyncio.sleep(settings.cleanup_interval_seconds)


@asynccontextmanager
async def web_lifespan(app: FastAPI) -> AsyncIterator[None]:
    task = asyncio.create_task(
        _cleanup_loop(app.state.visitor_stores, app.state.web_settings)
    )
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task