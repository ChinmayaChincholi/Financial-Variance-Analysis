"""
Workspace HTTP endpoints.

Workspaces are analysed datasets saved on this computer so they can be
reopened without uploading the file again. Everything stays local.
"""

import json
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from storage.workspace_store import get_store

router = APIRouter(
    prefix="/api/workspaces",
    tags=["Workspaces"],
)

_WORKSPACE_ID = re.compile(r"^[0-9a-f]{32}$")


def _require_valid_id(workspace_id: str) -> None:
    if not _WORKSPACE_ID.fullmatch(workspace_id):
        raise HTTPException(status_code=404, detail="Workspace not found.")


@router.get("")
def list_workspaces() -> dict:
    return {"workspaces": get_store().list()}


@router.get("/{workspace_id}")
def get_workspace(workspace_id: str) -> Response:
    _require_valid_id(workspace_id)
    found = get_store().get(workspace_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    meta, session_json = found
    # The session is already serialized JSON; splice it in instead of
    # decoding and re-encoding what can be a very large document.
    body = '{"meta":' + json.dumps(meta) + ',"session":' + session_json + "}"
    return Response(content=body, media_type="application/json")


@router.delete("/{workspace_id}")
def delete_workspace(workspace_id: str) -> dict:
    _require_valid_id(workspace_id)
    if not get_store().delete(workspace_id):
        raise HTTPException(status_code=404, detail="Workspace not found.")
    return {"deleted": True}