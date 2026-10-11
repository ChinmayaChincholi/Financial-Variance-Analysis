"""
Local, offline persistence for analysed datasets ("workspaces").

Every successfully processed dataset is saved here as one gzip-compressed JSON
document inside a SQLite database, so the client can close the application and
reopen the same analysis later without uploading the file again.

Nothing in this module touches the network. The database lives in the
operating system's per-user data folder (override with the
VARIANCE_STUDIO_DATA_DIR environment variable).
"""

from __future__ import annotations

import gzip
import json
import os
import re
import sqlite3
import sys
import threading
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_DIR_NAME = "VarianceStudio"
DATA_DIR_ENV = "VARIANCE_STUDIO_DATA_DIR"
DB_FILENAME = "workspaces.sqlite3"


def default_data_dir() -> Path:
    override = os.environ.get(DATA_DIR_ENV)
    if override:
        return Path(override).expanduser()
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / APP_DIR_NAME


def derive_workspace_name(filename: str) -> str:
    """'FY26_Financial-Dataset.xlsx' -> 'FY26 Financial Dataset'."""
    stem = Path(filename).stem
    cleaned = re.sub(r"[_\-]+", " ", stem)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or "Untitled workspace"


def _now() -> str:
    # Microsecond resolution keeps "most recently opened" ordering deterministic.
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


class WorkspaceStore:
    def __init__(self, db_path: Path | str) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path, timeout=15)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_schema(self) -> None:
        with self._lock, closing(self._connect()) as connection, connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS workspaces (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    sheet_name TEXT NOT NULL,
                    file_size INTEGER,
                    created_at TEXT NOT NULL,
                    last_opened_at TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    payload BLOB NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_workspaces_opened "
                "ON workspaces (last_opened_at DESC)"
            )

    @staticmethod
    def _meta(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "filename": row["filename"],
            "sheet_name": row["sheet_name"],
            "file_size": row["file_size"],
            "created_at": row["created_at"],
            "last_opened_at": row["last_opened_at"],
            "summary": json.loads(row["summary"]),
        }

    def save(
            self,
            session: dict[str, Any],
            *,
            file_size: int | None = None,
    ) -> dict[str, Any]:
        """
        Persist a computed session and return its metadata.

        Re-importing a file with the same name and sheet replaces the earlier
        workspace (same id), so refreshed data never piles up as duplicates.
        """
        dataset = session["dataset"]
        filename = str(dataset["filename"])
        sheet_name = str(dataset["sheet_name"])
        summary = json.dumps(session.get("summary", {}))
        payload = gzip.compress(json.dumps(session).encode("utf-8"), compresslevel=6)
        now = _now()

        with self._lock, closing(self._connect()) as connection, connection:
            existing = connection.execute(
                "SELECT id, name, created_at FROM workspaces "
                "WHERE filename = ? AND sheet_name = ?",
                (filename, sheet_name),
            ).fetchone()

            if existing is not None:
                workspace_id = existing["id"]
                connection.execute(
                    "UPDATE workspaces SET file_size = ?, last_opened_at = ?, "
                    "summary = ?, payload = ? WHERE id = ?",
                    (file_size, now, summary, payload, workspace_id),
                )
            else:
                workspace_id = uuid.uuid4().hex
                connection.execute(
                    "INSERT INTO workspaces (id, name, filename, sheet_name, "
                    "file_size, created_at, last_opened_at, summary, payload) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        workspace_id,
                        derive_workspace_name(filename),
                        filename,
                        sheet_name,
                        file_size,
                        now,
                        now,
                        summary,
                        payload,
                    ),
                )

            row = connection.execute(
                "SELECT id, name, filename, sheet_name, file_size, created_at, "
                "last_opened_at, summary FROM workspaces WHERE id = ?",
                (workspace_id,),
            ).fetchone()
        return self._meta(row)

    def list(self) -> list[dict[str, Any]]:
        with self._lock, closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT id, name, filename, sheet_name, file_size, created_at, "
                "last_opened_at, summary FROM workspaces "
                "ORDER BY last_opened_at DESC, created_at DESC"
            ).fetchall()
        return [self._meta(row) for row in rows]

    def get(
            self,
            workspace_id: str,
            *,
            touch: bool = True,
    ) -> tuple[dict[str, Any], str] | None:
        """Return (metadata, session_json_text) or None if it does not exist."""
        with self._lock, closing(self._connect()) as connection, connection:
            row = connection.execute(
                "SELECT * FROM workspaces WHERE id = ?",
                (workspace_id,),
            ).fetchone()
            if row is None:
                return None
            if touch:
                connection.execute(
                    "UPDATE workspaces SET last_opened_at = ? WHERE id = ?",
                    (_now(), workspace_id),
                )
        meta = self._meta(row)
        payload = gzip.decompress(row["payload"]).decode("utf-8")
        return meta, payload

    def delete(self, workspace_id: str) -> bool:
        with self._lock, closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                "DELETE FROM workspaces WHERE id = ?",
                (workspace_id,),
            )
            return cursor.rowcount > 0


_store: WorkspaceStore | None = None
_store_lock = threading.Lock()


def get_store() -> WorkspaceStore:
    global _store
    with _store_lock:
        if _store is None:
            _store = WorkspaceStore(default_data_dir() / DB_FILENAME)
        return _store


def set_store(store: WorkspaceStore | None) -> None:
    """Swap the process-wide store (used by tests)."""
    global _store
    with _store_lock:
        _store = store