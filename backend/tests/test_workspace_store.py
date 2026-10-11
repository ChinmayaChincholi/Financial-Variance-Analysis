import json

import pytest

from storage.workspace_store import (
    WorkspaceStore,
    default_data_dir,
    derive_workspace_name,
)


def _session(filename="FY26_Financial_Dataset.xlsx", sheet="Projects", marker=1):
    return {
        "dataset": {
            "filename": filename,
            "sheet_name": sheet,
            "row_count": 10,
            "column_count": 4,
        },
        "summary": {"unique_projects": 3, "regions": ["IN", "US"]},
        "marker": marker,
    }


@pytest.fixture()
def store(tmp_path):
    return WorkspaceStore(tmp_path / "data" / "workspaces.sqlite3")


def test_derive_workspace_name():
    assert derive_workspace_name("FY26_Financial-Dataset.xlsx") == "FY26 Financial Dataset"
    assert derive_workspace_name("__.xlsx") == "Untitled workspace"


def test_save_returns_metadata_and_round_trips_session(store):
    meta = store.save(_session(), file_size=1234)

    assert meta["name"] == "FY26 Financial Dataset"
    assert meta["filename"] == "FY26_Financial_Dataset.xlsx"
    assert meta["sheet_name"] == "Projects"
    assert meta["file_size"] == 1234
    assert meta["summary"]["unique_projects"] == 3

    found = store.get(meta["id"])
    assert found is not None
    loaded_meta, payload = found
    assert loaded_meta["id"] == meta["id"]
    assert json.loads(payload)["marker"] == 1


def test_resaving_same_file_and_sheet_replaces_instead_of_duplicating(store):
    first = store.save(_session(marker=1))
    second = store.save(_session(marker=2))

    assert first["id"] == second["id"]
    assert first["created_at"] == second["created_at"]
    assert len(store.list()) == 1
    _, payload = store.get(first["id"])
    assert json.loads(payload)["marker"] == 2


def test_different_sheets_are_separate_workspaces(store):
    store.save(_session(sheet="Projects"))
    store.save(_session(sheet="Other"))
    assert len(store.list()) == 2


def test_list_orders_most_recently_opened_first(store):
    a = store.save(_session(filename="a.xlsx"))
    b = store.save(_session(filename="b.xlsx"))
    assert [w["id"] for w in store.list()][0] == b["id"]

    store.get(a["id"])  # opening a workspace moves it to the top
    assert [w["id"] for w in store.list()][0] == a["id"]


def test_get_unknown_returns_none(store):
    assert store.get("0" * 32) is None


def test_delete(store):
    meta = store.save(_session())
    assert store.delete(meta["id"]) is True
    assert store.delete(meta["id"]) is False
    assert store.list() == []


def test_data_dir_override(monkeypatch, tmp_path):
    monkeypatch.setenv("VARIANCE_STUDIO_DATA_DIR", str(tmp_path / "custom"))
    assert default_data_dir() == tmp_path / "custom"