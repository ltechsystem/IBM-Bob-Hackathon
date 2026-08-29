"""
backend/models.py — Pydantic models that mirror the TypeScript interfaces
defined in frontend/src/mockdata/incident.ts and LogViewerStage.tsx.

All models are used for:
  • SQLite persistence (via raw sqlite3 — no ORM needed)
  • FastAPI request/response schemas
  • Internal pipeline data passing
"""

from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Log line
# ---------------------------------------------------------------------------

class LogLine(BaseModel):
    time: str
    level: Literal["INFO", "WARN", "ERROR"]
    message: str


# ---------------------------------------------------------------------------
# Incident brief
# ---------------------------------------------------------------------------

class IncidentBrief(BaseModel):
    id: str
    title: str
    severity: Literal["P1", "P2", "P3"]
    service: str
    errorType: str
    errorMessage: str
    affectedEndpoint: str
    reportedAt: str


# ---------------------------------------------------------------------------
# Evidence file
# ---------------------------------------------------------------------------

class EvidenceFile(BaseModel):
    path: str
    relevance: Literal["HIGH", "MEDIUM", "LOW"]
    reason: str


# ---------------------------------------------------------------------------
# Subagent finding
# ---------------------------------------------------------------------------

class SubagentFinding(BaseModel):
    agent: str
    focus: str
    finding: str
    confidence: Literal["HIGH", "MEDIUM", "LOW"]


# ---------------------------------------------------------------------------
# Root cause
# ---------------------------------------------------------------------------

class RootCause(BaseModel):
    file: str
    line: int
    summary: str
    confidence: Literal["HIGH", "MEDIUM", "LOW"]
    explanation: str


# ---------------------------------------------------------------------------
# Diff hunk
# ---------------------------------------------------------------------------

class DiffHunk(BaseModel):
    file: str
    before: List[str]
    after: List[str]
    lineNumber: int


# ---------------------------------------------------------------------------
# Test result
# ---------------------------------------------------------------------------

class TestResult(BaseModel):
    name: str
    status: Literal["PASSED", "FAILED"]
    message: Optional[str] = None


# ---------------------------------------------------------------------------
# Full pipeline result (stored in SQLite + returned by GET /incidents/{id})
# ---------------------------------------------------------------------------

class PipelineResult(BaseModel):
    incident: IncidentBrief
    logLines: List[LogLine]
    evidenceFiles: List[EvidenceFile]
    subagentFindings: List[SubagentFinding]
    rootCause: RootCause
    diffHunk: DiffHunk
    testResults: List[TestResult]


# ---------------------------------------------------------------------------
# Request body for POST /incidents/run
# ---------------------------------------------------------------------------

class RunIncidentRequest(BaseModel):
    """
    Minimal description of the incident to trigger the pipeline.
    The backend will derive all other fields via LLM or stub logic.
    """
    id: str = "INC-2024-001"
    title: str = "GET /users/{user_id} crashes with AttributeError"
    severity: Literal["P1", "P2", "P3"] = "P1"
    service: str = "user-service"
    errorType: str = "AttributeError"
    errorMessage: str = "'NoneType' object has no attribute 'name'"
    affectedEndpoint: str = "GET /users/{user_id}"
    logPath: str = "app/logs/app.log"
    # Raw log text — newline-separated log entries
    rawLog: str = ""
