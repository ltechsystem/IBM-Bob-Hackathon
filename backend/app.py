"""
backend/app.py — FastAPI application.

Endpoints
---------
GET  /                          health check
GET  /api/incidents             list all stored incidents (id, title, severity, created_at)
POST /api/incidents/run         run the full pipeline and store the result
GET  /api/incidents/{id}        retrieve a stored pipeline result
DELETE /api/incidents/{id}      delete a stored incident

CORS
----
Allows requests from the Vite dev server (http://localhost:5173) and from the
same origin in production.  Configured via BACKEND_CORS_ORIGINS env var
(comma-separated list, default "http://localhost:5173").
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.database import (
    delete_incident,
    init_db,
    list_incidents,
    list_sentinel_classifications,
    load_incident,
    save_incident,
    save_sentinel_classification,
)
from backend.models import PipelineResult, RunIncidentRequest, SentinelClassification
from backend.pipeline import run_pipeline

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Bob Debug Agent API",
    description=(
        "FastAPI + SQLite backend that drives the Incident Pipeline UI. "
        "Each POST /api/incidents/run executes the full 8-stage debug pipeline "
        "using watsonx.ai (IBM Granite) or the built-in stub mode."
    ),
    version="0.1.0",
)

# CORS — allow the Vite dev server and production same-origin
_origins_env = os.environ.get("BACKEND_CORS_ORIGINS", "http://localhost:5173")
_allowed_origins = [o.strip() for o in _origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Static assets — serve the frontend public/ directory at /static
# ---------------------------------------------------------------------------

_PUBLIC_DIR = Path(__file__).parent.parent / "frontend" / "public"
if _PUBLIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_PUBLIC_DIR)), name="static")

# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

@app.on_event("startup")
def on_startup() -> None:
    init_db()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", tags=["health"])
def health() -> dict:
    """Simple health-check endpoint."""
    return {"status": "ok", "service": "bob-debug-agent"}


@app.get("/api/incidents", tags=["incidents"])
def get_incidents() -> List[Dict[str, Any]]:
    """Return a lightweight list of all stored incidents."""
    return list_incidents()


@app.post("/api/incidents/run", response_model=PipelineResult, tags=["incidents"])
def run_incident(req: RunIncidentRequest) -> PipelineResult:
    """
    Execute the full 8-stage debug pipeline for the given incident request
    and persist the result to SQLite.

    In stub mode (default) all LLM calls are short-circuited and the response
    mirrors the frontend mock data exactly.  Set BACKEND_STUB=false and provide
    watsonx.ai credentials to use live AI inference.
    """
    result = run_pipeline(req)
    save_incident(result)
    return result


@app.get("/api/incidents/{incident_id}", response_model=PipelineResult, tags=["incidents"])
def get_incident(incident_id: str) -> PipelineResult:
    """Retrieve a previously stored pipeline result by incident ID."""
    result = load_incident(incident_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found")
    return result


@app.delete("/api/incidents/{incident_id}", tags=["incidents"])
def remove_incident(incident_id: str) -> Dict[str, Any]:
    """Delete a stored incident."""
    deleted = delete_incident(incident_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found")
    return {"deleted": True, "id": incident_id}


# ---------------------------------------------------------------------------
# Sentinel routes
# ---------------------------------------------------------------------------

@app.post("/api/sentinel/results", tags=["sentinel"])
def post_sentinel_result(result: SentinelClassification) -> Dict[str, Any]:
    """
    Accept a classification result from Sentinel (posted by sentinel/proposals.py
    after the developer reviews it in the terminal).

    Sets received_at automatically if not provided by the caller.
    """
    from datetime import datetime, timezone
    if not result.received_at:
        result = result.model_copy(
            update={"received_at": datetime.now(timezone.utc).isoformat()}
        )
    db_id = save_sentinel_classification(result)
    return {"status": "ok", "id": db_id}


@app.get("/api/sentinel/results", tags=["sentinel"])
def get_sentinel_results() -> List[Dict[str, Any]]:
    """Return all stored Sentinel classification results, newest first."""
    return list_sentinel_classifications()
