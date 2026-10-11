import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.workspace_routes import router
from storage.workspace_store import WorkspaceStore, set_store


@pytest.fixture()
def client(tmp_path):
    set_store(WorkspaceStore(tmp_path / "workspaces.sqlite3"))
    app = FastAPI()
    app.include_router(router)
    yield TestClient(app)
    set_store(None)


def _save(filename="data.xlsx"):
    from storage.workspace_store import get_store

    return get_store().save(
        {
            "dataset": {"filename": filename, "sheet_name": "S"},
            "summary": {"unique_projects": 2},
            "projectWise": {"revenue": {"unique": None}},
        },
        file_size=10,
    )


def test_list_is_empty_initially(client):
    response = client.get("/api/workspaces")
    assert response.status_code == 200
    assert response.json() == {"workspaces": []}


def test_list_get_and_delete_flow(client):
    meta = _save()

    listed = client.get("/api/workspaces").json()["workspaces"]
    assert [w["id"] for w in listed] == [meta["id"]]

    response = client.get(f"/api/workspaces/{meta['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["id"] == meta["id"]
    assert body["session"]["projectWise"]["revenue"]["unique"] is None

    assert client.delete(f"/api/workspaces/{meta['id']}").json() == {"deleted": True}
    assert client.get(f"/api/workspaces/{meta['id']}").status_code == 404
    assert client.delete(f"/api/workspaces/{meta['id']}").status_code == 404


def test_malformed_id_is_a_404(client):
    assert client.get("/api/workspaces/not-a-real-id").status_code == 404
    assert client.delete("/api/workspaces/..%2F..%2Fetc").status_code == 404