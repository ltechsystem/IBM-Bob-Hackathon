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
# Sentinel classification result (posted by sentinel/proposals.py)
# ---------------------------------------------------------------------------

class SentinelClassification(BaseModel):
    """
    A single RPGUnit test failure classification produced by Sentinel + Bob.

    Posted to POST /api/sentinel/results by sentinel/proposals.py after
    the developer has reviewed the proposal in the terminal.
    """
    # IBM i identifiers
    lib: str
    srcpf: str
    mbr: str
    test_name: str

    # Bob's verdict
    verdict: Literal["STALE", "REGRESSION", "NEW_COVERAGE_NEEDED", "UNCERTAIN"]
    confidence: float
    rationale: str

    # Optional unified diff patch (only present for STALE / NEW_COVERAGE_NEEDED)
    proposed_patch: Optional[str] = None

    # Developer's terminal decision: accepted | rejected | edited | regression | skipped | no_patch
    developer_action: Optional[str] = None

    # ISO-8601 timestamp set by the backend on receipt
    received_at: Optional[str] = None


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
