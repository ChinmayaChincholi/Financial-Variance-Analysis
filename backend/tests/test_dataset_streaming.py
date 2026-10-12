import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from services import dataset_service


def _collect(job, path):
    async def run():
        return [json.loads(line) async for line in dataset_service._stream_job(path, job)]

    return asyncio.run(run())


def test_stream_emits_progress_then_result_and_cleans_up(tmp_path):
    temp = tmp_path / "upload.xlsx"
    temp.write_text("x")

    def job(emit):
        emit("Computing project-wise analysis")
        emit("Importing dataset", "10 rows · 4 columns")
        return {"status": "resolved", "workspace": {"id": "w"}}

    events = _collect(job, str(temp))

    assert events[0] == {"type": "progress", "stage": "Computing project-wise analysis"}
    assert events[1] == {
        "type": "progress",
        "stage": "Importing dataset",
        "detail": "10 rows · 4 columns",
    }
    assert events[-1] == {"type": "result", "data": {"status": "resolved", "workspace": {"id": "w"}}}
    assert not Path(temp).exists()


def test_stream_reports_job_errors_as_an_error_event(tmp_path):
    temp = tmp_path / "upload.xlsx"
    temp.write_text("x")

    def job(emit):
        raise ValueError("Sheet is empty.")

    events = _collect(job, str(temp))
    assert events == [{"type": "error", "message": "Sheet is empty."}]
    assert not temp.exists()


@pytest.fixture()
def resolve_env(monkeypatch):
    mapping = SimpleNamespace(
        region_col="Region",
        has_revenue=lambda: True,
        has_cost=lambda: True,
    )
    ingestion = SimpleNamespace(status="resolved", column_mapping=mapping)

    class Frame:
        columns = ["a", "b", "c"]

        def __len__(self):
            return 1240

    calls = {}

    monkeypatch.setattr(dataset_service, "_read_workbook_sheets", lambda path: ["Projects"])
    monkeypatch.setattr(
        dataset_service,
        "resolve_ingestion_with_choices_and_dataframe",
        lambda **kwargs: (ingestion, Frame()),
    )

    def fake_precompute(**kwargs):
        callback = kwargs["progress_callback"]
        callback("Computing project-wise analysis")
        callback("Computing region-wise analysis")
        return SimpleNamespace(to_dict=lambda: {"dataset": {}})

    monkeypatch.setattr(dataset_service, "precompute_dataset", fake_precompute)
    monkeypatch.setattr(
        dataset_service,
        "_save_workspace",
        lambda session, path: calls.setdefault("saved", {"id": "w1"}),
    )
    return calls


def test_resolve_streams_the_remaining_stages_in_order(resolve_env):
    seen = []

    result = dataset_service._resolve_materialized_dataset(
        "file.xlsx",
        "data.xlsx",
        "Projects",
        json.dumps({"metric_block_0": "Revenue"}),
        lambda stage, detail=None: seen.append((stage, detail)),
    )

    assert result == {"status": "resolved", "workspace": {"id": "w1"}}
    stages = [stage for stage, _ in seen]
    assert stages == [
        "Detecting columns",
        "Importing dataset",
        "Detecting columns",
        "Computing project-wise analysis",
        "Computing region-wise analysis",
        "Finalizing results",
    ]
    assert ("Importing dataset", "1,240 rows · 3 columns") in seen
    assert ("Detecting columns", "Project, Region, revenue and cost months") in seen


def test_resolve_rejects_bad_choices(resolve_env):
    with pytest.raises(ValueError, match="Invalid clarification choices"):
        dataset_service._resolve_materialized_dataset("f.xlsx", "d.xlsx", "Projects", "{nope")
    with pytest.raises(ValueError, match="JSON object"):
        dataset_service._resolve_materialized_dataset("f.xlsx", "d.xlsx", "Projects", "[1]")


def test_resolve_rejects_unknown_sheet(resolve_env):
    with pytest.raises(ValueError, match="does not exist"):
        dataset_service._resolve_materialized_dataset("f.xlsx", "d.xlsx", "Other", "{}")