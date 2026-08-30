"""
tests/test_backend.py — Integration tests for the FastAPI backend.

Runs entirely with BACKEND_STUB=true (no watsonx.ai credentials required).
Uses FastAPI's TestClient (requires httpx).
"""

from __future__ import annotations

import os
import tempfile

import pytest

# Force stub mode and use a temp DB so tests are isolated
os.environ["BACKEND_STUB"] = "true"


@pytest.fixture(autouse=True)
def _tmp_db(tmp_path, monkeypatch):
    """Redirect the SQLite database to a temp directory for each test."""
    db_path = tmp_path / "test_incidents.db"
    monkeypatch.setenv("BACKEND_DB_PATH", str(db_path))
    # Re-import database so it picks up the new env var
    import importlib
    import backend.database as db_mod
    importlib.reload(db_mod)
    db_mod.init_db()
    yield
    # Cleanup handled by tmp_path fixture


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient
    # Reload app so it picks up reloaded database module
    import importlib
    import backend.app as app_mod
    importlib.reload(app_mod)
    return TestClient(app_mod.app)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

def test_health(client):
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Run pipeline
# ---------------------------------------------------------------------------

def test_run_pipeline_stub(client):
    """POST /api/incidents/run returns a full PipelineResult in stub mode."""
    payload = {
        "id": "INC-TEST-001",
        "title": "Test incident",
        "severity": "P1",
        "service": "test-service",
        "errorType": "ValueError",
        "errorMessage": "test error",
        "affectedEndpoint": "GET /test",
        "logPath": "app/logs/app.log",
        "rawLog": "",
    }
    res = client.post("/api/incidents/run", json=payload)
    assert res.status_code == 200

    data = res.json()
    assert data["incident"]["id"] == "INC-TEST-001"
    assert len(data["logLines"]) > 0
    assert len(data["evidenceFiles"]) > 0
    assert len(data["subagentFindings"]) == 4
    assert data["rootCause"]["confidence"] in ("HIGH", "MEDIUM", "LOW")
    assert len(data["diffHunk"]["before"]) > 0
    assert len(data["diffHunk"]["after"]) > 0
    assert len(data["testResults"]) > 0


# ---------------------------------------------------------------------------
# List incidents
# ---------------------------------------------------------------------------

def test_list_incidents_empty(client):
    res = client.get("/api/incidents")
    assert res.status_code == 200
    assert res.json() == []


def test_list_incidents_after_run(client):
    client.post("/api/incidents/run", json={"id": "INC-LIST-001"})
    res = client.get("/api/incidents")
    assert res.status_code == 200
    ids = [i["id"] for i in res.json()]
    assert "INC-LIST-001" in ids


# ---------------------------------------------------------------------------
# Get incident
# ---------------------------------------------------------------------------

def test_get_incident_not_found(client):
    res = client.get("/api/incidents/INC-MISSING")
    assert res.status_code == 404


def test_get_incident_after_run(client):
    client.post("/api/incidents/run", json={"id": "INC-GET-001"})
    res = client.get("/api/incidents/INC-GET-001")
    assert res.status_code == 200
    assert res.json()["incident"]["id"] == "INC-GET-001"


# ---------------------------------------------------------------------------
# Delete incident
# ---------------------------------------------------------------------------

def test_delete_incident(client):
    client.post("/api/incidents/run", json={"id": "INC-DEL-001"})
    res = client.delete("/api/incidents/INC-DEL-001")
    assert res.status_code == 200
    assert res.json()["deleted"] is True

    # Should be gone
    res2 = client.get("/api/incidents/INC-DEL-001")
    assert res2.status_code == 404


def test_delete_incident_not_found(client):
    res = client.delete("/api/incidents/INC-NOBODY")
    assert res.status_code == 404
