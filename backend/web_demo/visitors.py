"""
Per-visitor storage for the web demo.

The desktop application keeps one SQLite file for the single person using the
computer. On a shared website that would let every visitor see (and overwrite)
every other visitor's uploaded financial data, so the demo gives each browser
its own private store:

    <data dir>/visitors/<visitor id>/workspaces.sqlite3

The visitor id is a random token kept in an HttpOnly cookie. There are no
accounts; the id only separates one browser's workspaces from another's.

VisitorWorkspaceStores exposes the same methods as WorkspaceStore
(save / list / get / delete), so the existing routes and services work
unchanged: they call get_store(), which returns this object in web mode, and
each call is routed to the store of the visitor whose request is running.
"""

import os
import re
import shutil
import threading
import time
import uuid
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from storage.workspace_store import DB_FILENAME, WorkspaceStore, default_data_dir

COOKIE_NAME = "vs_visitor"

_VISITOR_ID = re.compile(r"^[0-9a-f]{32}$")

# Set by the web middleware for the duration of each request. Context
# variables are copied into the worker threads and tasks the request spawns,
# which is how the background processing job still knows whose data it is
# saving.
current_visitor: ContextVar[str | None] = ContextVar(
    "current_visitor", default=None
)


def new_visitor_id() -> str:
    return uuid.uuid4().hex


def is_valid_visitor_id(value: str | None) -> bool:
    return bool(value) and _VISITOR_ID.fullmatch(value) is not None


class VisitorWorkspaceStores:
    def __init__(self, max_workspaces: int, root: Path | None = None) -> None:
        self._max_workspaces = max_workspaces
        self._root = Path(root) if root is not None else (
                default_data_dir() / "visitors"
        )
        self._root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._stores: dict[str, WorkspaceStore] = {}

    @property
    def root(self) -> Path:
        return self._root

    # ------------------------------------------------------------------
    # Routing to the current visitor's store
    # ------------------------------------------------------------------

    def _store(self) -> WorkspaceStore:
        visitor_id = current_visitor.get()
        if not is_valid_visitor_id(visitor_id):
            # Never fall back to a shared store: refusing is safer than
            # mixing one visitor's data with another's.
            raise RuntimeError("No visitor is associated with this request.")

        directory = self._root / visitor_id
        with self._lock:
            store = self._stores.get(visitor_id)
            if store is None or not directory.is_dir():
                store = WorkspaceStore(directory / DB_FILENAME)
                self._stores[visitor_id] = store
            return store

    # ------------------------------------------------------------------
    # Same interface as WorkspaceStore
    # ------------------------------------------------------------------

    def save(
            self,
            session: dict[str, Any],
            *,
            file_size: int | None = None,
    ) -> dict[str, Any]:
        store = self._store()
        meta = store.save(session, file_size=file_size)

        # Keep each visitor's storage bounded: drop the least recently
        # opened workspaces beyond the cap. The one just saved is the most
        # recently opened, so it is never the one removed.
        for stale in store.list()[self._max_workspaces:]:
            store.delete(stale["id"])
        return meta

    def list(self) -> list[dict[str, Any]]:
        return self._store().list()

    def get(
            self,
            workspace_id: str,
            *,
            touch: bool = True,
    ) -> tuple[dict[str, Any], str] | None:
        return self._store().get(workspace_id, touch=touch)

    def delete(self, workspace_id: str) -> bool:
        return self._store().delete(workspace_id)

    # ------------------------------------------------------------------
    # Retention
    # ------------------------------------------------------------------

    @staticmethod
    def _last_activity(directory: Path) -> float:
        newest = directory.stat().st_mtime
        with os.scandir(directory) as entries:
            for entry in entries:
                try:
                    newest = max(newest, entry.stat().st_mtime)
                except OSError:
                    continue
        return newest

    def purge_idle(
            self,
            max_age_seconds: float,
            now: float | None = None,
    ) -> int:
        """
        Delete the data of visitors with no activity for max_age_seconds.

        Only directories named like visitor ids are touched, so nothing else
        that happens to live under the data folder can be removed. Returns
        the number of visitors removed.
        """
        current = time.time() if now is None else now
        removed = 0

        with os.scandir(self._root) as iterator:
            entries = list(iterator)

        for entry in entries:
            if not entry.is_dir(follow_symlinks=False):
                continue
            if not is_valid_visitor_id(entry.name):
                continue
            try:
                idle_for = current - self._last_activity(Path(entry.path))
            except OSError:
                continue
            if idle_for <= max_age_seconds:
                continue

            with self._lock:
                self._stores.pop(entry.name, None)
                shutil.rmtree(entry.path, ignore_errors=True)
            removed += 1

        return removed