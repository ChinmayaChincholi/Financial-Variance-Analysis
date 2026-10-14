"""
Tests for the hosted web demo (VARIANCE_STUDIO_MODE=web).

Covers: the desktop mode staying untouched, private per-visitor workspaces
(including through the streaming processing path), upload and concurrency
limits, retention, and the security/cache/compression headers.
"""

import asyncio
import json
import os
import random
import time
from functools import lru_cache
from io import BytesIO

import httpx
import pytest
import xlsxwriter
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.app import create_app
from storage.workspace_store import set_store
from web_demo.middleware import DemoMiddleware
from web_demo.settings import WebSettings, is_web_mode
from web_demo.visitors import COOKIE_NAME, VisitorWorkspaceStores

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

SAMPLE_FILENAME = "Test_Financial_Dataset.xlsx"


@lru_cache(maxsize=1)
def build_sample_workbook() -> bytes:
    """
    A small, fictional workbook in the layout the application expects: one
    row per resource (many per project), then a revenue block and a cost
    block. Large enough for column detection to be confident, so analysing
    it never needs to ask a question.
    """
    rng = random.Random(7)
    months = [
        "Apr 2025", "May 2025", "Jun 2025", "Jul 2025", "Aug 2025",
        "Sep 2025", "Oct 2025", "Nov 2025", "Dec 2025", "Jan 2026",
        "Feb 2026", "Mar 2026",
    ]
    regions = ["North America", "Europe", "Asia Pacific", "Middle East"]
    headers = [
        "Emp ID", "Resource Name", "Project Name", "Region",
        *[f"Revenue {m}" for m in months],
        *[f"Cost {m}" for m in months],
    ]

    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    sheet = workbook.add_worksheet("Financials")
    sheet.write_row(0, 0, headers)

    # Few projects with many resources each: column detection recognises a
    # project column by its repeated values, so this mirrors real data.
    row = 1
    for project_index in range(3):
        for resource_index in range(64):
            revenues = [
                round(rng.uniform(4000, 9000) * (1 + 0.02 * month), -1)
                for month in range(len(months))
            ]
            costs = [round(value * rng.uniform(0.6, 0.8), -1) for value in revenues]
            sheet.write_row(
                row,
                0,
                [
                    f"E{1000 + row}",
                    f"Person {row}",
                    f"Project {project_index + 1}",
                    regions[resource_index % 4],
                    *revenues,
                    *costs,
                ],
            )
            row += 1

    workbook.close()
    return output.getvalue()


@pytest.fixture(autouse=True)
def _reset_global_store():
    yield
    set_store(None)


@pytest.fixture
def web_env(monkeypatch, tmp_path):
    monkeypatch.setenv("VARIANCE_STUDIO_MODE", "web")
    monkeypatch.setenv("VARIANCE_STUDIO_DATA_DIR", str(tmp_path / "data"))
    # Keep these tests independent of any frontend build on this machine.
    monkeypatch.setenv("VARIANCE_STUDIO_FRONTEND_DIR", str(tmp_path / "none"))
    return tmp_path


@pytest.fixture
def web_app(web_env) -> FastAPI:
    return create_app()


@pytest.fixture
def client(web_app) -> TestClient:
    return TestClient(web_app)


def _upload(client: TestClient, path: str, filename: str = SAMPLE_FILENAME):
    return client.post(
        path,
        files={"file": (filename, build_sample_workbook(), XLSX)},
    )


def _stream_result(response) -> dict:
    events = [json.loads(line) for line in response.text.splitlines() if line]
    assert events[-1]["type"] == "result", events[-1]
    return events[-1]["data"]


# ---------------------------------------------------------------------------
# Mode switch
# ---------------------------------------------------------------------------


def test_default_mode_is_desktop(monkeypatch):
    monkeypatch.delenv("VARIANCE_STUDIO_MODE", raising=False)
    assert is_web_mode() is False


def test_invalid_mode_fails_fast(monkeypatch):
    monkeypatch.setenv("VARIANCE_STUDIO_MODE", "websit")
    with pytest.raises(ValueError):
        is_web_mode()


def test_desktop_mode_has_no_web_behaviour(monkeypatch, tmp_path):
    monkeypatch.delenv("VARIANCE_STUDIO_MODE", raising=False)
    monkeypatch.setenv("VARIANCE_STUDIO_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("VARIANCE_STUDIO_FRONTEND_DIR", str(tmp_path / "none"))
    app = create_app()
    client = TestClient(app)

    assert not hasattr(app.state, "web_settings")
    assert app.openapi_url == "/openapi.json"
    health = client.get("/api/health")
    assert health.status_code == 200
    assert "set-cookie" not in health.headers
    assert "content-security-policy" not in health.headers
    assert client.get("/api/demo/config").status_code in (404, 405)
    # The desktop store is the single shared one, never a per-visitor one.
    workspaces = client.get("/api/workspaces")
    assert workspaces.status_code == 200
    assert "set-cookie" not in workspaces.headers


def test_web_mode_disables_interactive_docs(web_app):
    assert web_app.docs_url is None
    assert web_app.redoc_url is None
    assert web_app.openapi_url is None


# ---------------------------------------------------------------------------
# Visitor cookie
# ---------------------------------------------------------------------------


def test_visitor_cookie_is_issued_with_safe_attributes(client):
    response = client.get("/api/workspaces")
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{COOKIE_NAME}=")
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie
    assert "Path=/" in cookie
    assert "Max-Age=" in cookie
    assert "Secure" not in cookie  # plain http in this test

    # Sent back on the next request, so it is not re-issued.
    again = client.get("/api/workspaces")
    assert "set-cookie" not in again.headers


def test_cookie_is_secure_behind_https_proxy(client):
    response = client.get(
        "/api/workspaces", headers={"x-forwarded-proto": "https"}
    )
    assert "Secure" in response.headers["set-cookie"]
    assert "strict-transport-security" in response.headers


def test_health_check_does_not_create_visitors(client, web_env):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert "set-cookie" not in response.headers


def test_tampered_cookie_is_replaced_and_never_used_as_a_path(client, web_env):
    response = client.get(
        "/api/workspaces",
        headers={"cookie": f"{COOKIE_NAME}=../../etc"},
    )
    assert response.status_code == 200
    assert COOKIE_NAME in response.headers["set-cookie"]
    assert "etc" not in response.headers["set-cookie"]
    visitors_dir = web_env / "data" / "visitors"
    assert all(len(p.name) == 32 for p in visitors_dir.iterdir())


# ---------------------------------------------------------------------------
# Privacy: one browser can never see another's workspaces
# ---------------------------------------------------------------------------


def test_workspaces_are_private_per_visitor(web_app):
    alice = TestClient(web_app)
    bob = TestClient(web_app)

    result = _upload(alice, "/api/dataset/process").json()
    assert result["status"] == "resolved"
    workspace_id = result["workspace"]["id"]

    assert [w["id"] for w in alice.get("/api/workspaces").json()["workspaces"]] == [
        workspace_id
    ]
    assert bob.get("/api/workspaces").json()["workspaces"] == []
    assert bob.get(f"/api/workspaces/{workspace_id}").status_code == 404
    assert bob.delete(f"/api/workspaces/{workspace_id}").status_code == 404

    # Alice still has it after Bob's attempts.
    assert alice.get(f"/api/workspaces/{workspace_id}").status_code == 200


def test_same_filename_from_two_visitors_does_not_collide(web_app):
    alice = TestClient(web_app)
    bob = TestClient(web_app)

    a = _upload(alice, "/api/dataset/process").json()["workspace"]["id"]
    b = _upload(bob, "/api/dataset/process").json()["workspace"]["id"]

    assert a != b
    assert len(alice.get("/api/workspaces").json()["workspaces"]) == 1
    assert len(bob.get("/api/workspaces").json()["workspaces"]) == 1


def test_streaming_processing_saves_to_the_right_visitor(web_app):
    """The streaming path saves from a background thread; it must still
    know whose request it belongs to."""
    alice = TestClient(web_app)
    bob = TestClient(web_app)

    response = _upload(alice, "/api/dataset/process/stream")
    assert response.status_code == 200
    data = _stream_result(response)
    assert data["status"] == "resolved"
    workspace_id = data["workspace"]["id"]

    assert len(alice.get("/api/workspaces").json()["workspaces"]) == 1
    assert bob.get("/api/workspaces").json()["workspaces"] == []
    assert bob.get(f"/api/workspaces/{workspace_id}").status_code == 404


def test_each_visitor_keeps_only_the_most_recent_workspaces(
        web_env, monkeypatch
):
    monkeypatch.setenv("VARIANCE_STUDIO_MAX_WORKSPACES", "2")
    client = TestClient(create_app())

    ids = []
    for name in ("first.xlsx", "second.xlsx", "third.xlsx"):
        ids.append(
            _upload(client, "/api/dataset/process", name).json()["workspace"]["id"]
        )

    listed = [w["id"] for w in client.get("/api/workspaces").json()["workspaces"]]
    assert len(listed) == 2
    assert ids[2] in listed
    assert ids[0] not in listed


def test_store_refuses_to_run_without_a_visitor(tmp_path):
    stores = VisitorWorkspaceStores(max_workspaces=3, root=tmp_path)
    with pytest.raises(RuntimeError):
        stores.list()


# ---------------------------------------------------------------------------
# Analysis and config
# ---------------------------------------------------------------------------


def test_uploaded_dataset_is_analysed_without_questions(client):
    result = _upload(client, "/api/dataset/process").json()
    assert result["status"] == "resolved"

    workspace = client.get(
        f"/api/workspaces/{result['workspace']['id']}"
    ).json()
    session = workspace["session"]
    assert session["projectWise"]
    assert session["regionWise"]
    assert len(session["regions"]) == 4


def test_demo_config_reports_the_server_limits(web_env, monkeypatch):
    monkeypatch.setenv("VARIANCE_STUDIO_MAX_UPLOAD_MB", "5")
    monkeypatch.setenv("VARIANCE_STUDIO_RETENTION_HOURS", "12")
    config = TestClient(create_app()).get("/api/demo/config").json()
    assert config["mode"] == "web"
    assert config["max_upload_mb"] == 5
    assert config["retention_hours"] == 12


def test_default_upload_limit_is_50_mb(web_env, monkeypatch):
    monkeypatch.delenv("VARIANCE_STUDIO_MAX_UPLOAD_MB", raising=False)
    config = TestClient(create_app()).get("/api/demo/config").json()
    assert config["max_upload_mb"] == 50


def test_there_is_no_public_sample_dataset_endpoint(client):
    assert client.get("/api/demo/sample").status_code == 404


@pytest.mark.parametrize(
    "name, value",
    [
        ("VARIANCE_STUDIO_MAX_UPLOAD_MB", "abc"),
        ("VARIANCE_STUDIO_MAX_UPLOAD_MB", "0"),
        ("VARIANCE_STUDIO_RETENTION_HOURS", "-1"),
        ("VARIANCE_STUDIO_MAX_CONCURRENT_JOBS", "0"),
    ],
)
def test_invalid_settings_fail_fast(web_env, monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError):
        create_app()


# ---------------------------------------------------------------------------
# Limits
# ---------------------------------------------------------------------------


def test_oversized_upload_is_rejected_with_a_clear_message(
        web_env, monkeypatch
):
    monkeypatch.setenv("VARIANCE_STUDIO_MAX_UPLOAD_MB", "0.5")
    client = TestClient(create_app())

    big = b"0" * (1024 * 1024)
    response = client.post(
        "/api/dataset/process",
        files={"file": ("big.xlsx", big, XLSX)},
    )
    assert response.status_code == 413
    assert "0.5 MB" in response.json()["detail"]


def test_chunked_upload_without_a_declared_length_is_also_limited(
        web_env, monkeypatch
):
    monkeypatch.setenv("VARIANCE_STUDIO_MAX_UPLOAD_MB", "0.5")
    client = TestClient(create_app())

    boundary = "testboundary"
    head = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="big.xlsx"\r\n'
        f"Content-Type: {XLSX}\r\n\r\n"
    ).encode()
    tail = f"\r\n--{boundary}--\r\n".encode()

    def body():
        yield head
        for _ in range(16):
            yield b"0" * (128 * 1024)
        yield tail

    response = client.post(
        "/api/dataset/process",
        content=body(),
        headers={"content-type": f"multipart/form-data; boundary={boundary}"},
    )
    assert response.status_code == 413
    assert "MB limit" in response.json()["detail"]


def test_upload_just_under_the_limit_still_works(web_env, monkeypatch):
    monkeypatch.setenv("VARIANCE_STUDIO_MAX_UPLOAD_MB", "1")
    client = TestClient(create_app())
    assert len(build_sample_workbook()) < 1024 * 1024
    assert _upload(client, "/api/dataset/process").status_code == 200


def test_busy_server_answers_503_instead_of_queueing():
    settings = WebSettings(max_concurrent_jobs=1)
    release = asyncio.Event()
    started = asyncio.Event()

    async def slow_app(scope, receive, send):
        started.set()
        await release.wait()
        await send(
            {"type": "http.response.start", "status": 200, "headers": []}
        )
        await send({"type": "http.response.body", "body": b"{}"})

    async def scenario():
        middleware = DemoMiddleware(slow_app, settings)
        transport = httpx.ASGITransport(app=middleware)
        async with httpx.AsyncClient(
                transport=transport, base_url="http://test"
        ) as http:
            first = asyncio.create_task(http.post("/api/dataset/process"))
            await started.wait()

            second = await http.post("/api/dataset/process")
            assert second.status_code == 503
            assert second.headers["retry-after"] == "5"

            # Other endpoints are unaffected while a job runs.
            release.set()
            assert (await first).status_code == 200

            # The slot is released afterwards.
            third = await http.post("/api/dataset/process")
            assert third.status_code == 200

    asyncio.run(scenario())


# ---------------------------------------------------------------------------
# Retention
# ---------------------------------------------------------------------------


def test_idle_visitors_are_purged_and_active_ones_kept(web_app, web_env):
    old = TestClient(web_app)
    fresh = TestClient(web_app)
    _upload(old, "/api/dataset/process")
    _upload(fresh, "/api/dataset/process")

    stores: VisitorWorkspaceStores = web_app.state.visitor_stores
    visitors = sorted(p for p in stores.root.iterdir() if p.is_dir())
    assert len(visitors) == 2

    # Make exactly one of them look three days idle.
    three_days_ago = time.time() - 3 * 24 * 3600
    stale = visitors[0]
    for path in [stale, *stale.iterdir()]:
        os.utime(path, (three_days_ago, three_days_ago))

    unrelated = stores.root / "not-a-visitor"
    unrelated.mkdir()
    os.utime(unrelated, (three_days_ago, three_days_ago))

    assert stores.purge_idle(24 * 3600) == 1
    assert not stale.exists()
    assert visitors[1].exists()
    assert unrelated.exists()  # only visitor-shaped folders are ever removed


def test_a_purged_visitor_can_keep_using_the_demo(web_app):
    client = TestClient(web_app)
    _upload(client, "/api/dataset/process")

    stores: VisitorWorkspaceStores = web_app.state.visitor_stores
    assert stores.purge_idle(-1) == 1  # everything counts as expired

    assert client.get("/api/workspaces").json()["workspaces"] == []
    assert _upload(client, "/api/dataset/process").status_code == 200
    assert len(client.get("/api/workspaces").json()["workspaces"]) == 1


def test_background_cleanup_starts_and_stops_with_the_app(web_app):
    with TestClient(web_app) as client:
        assert client.get("/api/health").status_code == 200


# ---------------------------------------------------------------------------
# Headers and compression (with a frontend build present)
# ---------------------------------------------------------------------------


@pytest.fixture
def site(web_env, monkeypatch):
    dist = web_env / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>x</title>")
    (dist / "assets" / "app-abc123.js").write_text("console.log(1);" * 400)
    monkeypatch.setenv("VARIANCE_STUDIO_FRONTEND_DIR", str(dist))
    return TestClient(create_app())


def test_security_and_cache_headers(site):
    page = site.get("/", headers={"accept": "text/html"})
    assert page.status_code == 200
    assert page.headers["cache-control"] == "no-cache"
    assert page.headers["x-content-type-options"] == "nosniff"
    assert page.headers["x-frame-options"] == "DENY"
    assert page.headers["referrer-policy"] == "no-referrer"
    assert "noindex" in page.headers["x-robots-tag"]
    assert "default-src 'self'" in page.headers["content-security-policy"]
    assert COOKIE_NAME in page.headers["set-cookie"]  # page loads get a visitor

    asset = site.get("/assets/app-abc123.js")
    assert "immutable" in asset.headers["cache-control"]
    assert "set-cookie" not in asset.headers  # static files do not

    assert site.get("/api/workspaces").headers["cache-control"] == "no-store"


def test_client_side_routes_still_fall_back_to_the_app_shell(site):
    response = site.get("/workspace/0123456789abcdef0123456789abcdef/summary")
    assert response.status_code == 200
    assert "<title>x</title>" in response.text


def test_static_files_and_workspace_json_are_compressed(site):
    asset = site.get("/assets/app-abc123.js", headers={"accept-encoding": "gzip"})
    assert asset.headers.get("content-encoding") == "gzip"

    workspace_id = _upload(site, "/api/dataset/process").json()["workspace"]["id"]
    detail = site.get(
        f"/api/workspaces/{workspace_id}", headers={"accept-encoding": "gzip"}
    )
    assert detail.headers.get("content-encoding") == "gzip"
    assert detail.json()["session"]["projectWise"]


def test_progress_stream_is_never_compressed(site):
    response = site.post(
        "/api/dataset/process/stream",
        files={"file": (SAMPLE_FILENAME, build_sample_workbook(), XLSX)},
        headers={"accept-encoding": "gzip"},
    )
    assert response.status_code == 200
    assert "content-encoding" not in response.headers
    assert response.headers["content-type"].startswith("application/x-ndjson")
    assert _stream_result(response)["status"] == "resolved"