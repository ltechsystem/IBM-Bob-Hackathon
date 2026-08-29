"""
backend/llm.py — watsonx.ai / IBM Granite integration.

Modes
-----
BACKEND_STUB=true  (default when no WATSONX_API_KEY is set)
  All pipeline stages return deterministic hard-coded data identical to the
  frontend mock data.  No network calls are made.

BACKEND_STUB=false  (requires WATSONX_API_KEY, WATSONX_PROJECT_ID, WATSONX_URL)
  Each stage sends a prompt to IBM Granite via ibm-watsonx-ai and parses the
  structured response.

The stub mode is intentional — it lets the full pipeline run end-to-end in CI
and during front-end development without credentials.
"""

from __future__ import annotations

import json
import os
import re
import textwrap
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Stub toggle
# ---------------------------------------------------------------------------

def _is_stub() -> bool:
    env = os.environ.get("BACKEND_STUB", "").lower()
    if env in ("false", "0", "no"):
        return False
    # Default to stub if no API key is configured
    return not bool(os.environ.get("WATSONX_API_KEY", "").strip())


# ---------------------------------------------------------------------------
# Lazy watsonx client
# ---------------------------------------------------------------------------

_client: Optional[object] = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    try:
        from ibm_watsonx_ai import APIClient, Credentials  # type: ignore
        creds = Credentials(
            url=os.environ["WATSONX_URL"],
            api_key=os.environ["WATSONX_API_KEY"],
        )
        _client = APIClient(creds)
        return _client
    except Exception as exc:
        raise RuntimeError(
            "watsonx.ai client initialisation failed. "
            "Set BACKEND_STUB=true for development or provide WATSONX_API_KEY / WATSONX_URL."
        ) from exc


def _call_llm(prompt: str, max_tokens: int = 512) -> str:
    """Send a prompt to IBM Granite and return the generated text."""
    client = _get_client()
    model_id = os.environ.get("WATSONX_MODEL_ID", "ibm/granite-3-3-8b-instruct")
    project_id = os.environ["WATSONX_PROJECT_ID"]

    from ibm_watsonx_ai.foundation_models import ModelInference  # type: ignore
    model = ModelInference(
        model_id=model_id,
        api_client=client,
        project_id=project_id,
    )
    response = model.generate_text(
        prompt=prompt,
        params={"max_new_tokens": max_tokens, "temperature": 0.2},
    )
    return response


# ---------------------------------------------------------------------------
# Stub data (mirrors frontend/src/mockdata/)
# ---------------------------------------------------------------------------

_STUB_LOG_LINES: List[Dict] = [
    {"time": "21:13:55", "level": "INFO",  "message": "GET /users/1 200 OK"},
    {"time": "21:13:57", "level": "INFO",  "message": "GET /users/2 200 OK"},
    {"time": "21:14:02", "level": "ERROR", "message": "AttributeError: 'NoneType' object has no attribute 'name' — app/main.py:13"},
    {"time": "21:14:02", "level": "ERROR", "message": "Unhandled exception in get_user() — request: GET /users/999"},
    {"time": "21:14:05", "level": "INFO",  "message": "POST /users 201 Created"},
    {"time": "21:14:10", "level": "WARN",  "message": "Slow query detected: SELECT * FROM users (320ms)"},
]

_STUB_EVIDENCE_FILES: List[Dict] = [
    {"path": "app/main.py",         "relevance": "HIGH",   "reason": "Route handler — contains the crashing line"},
    {"path": "app/models.py",       "relevance": "HIGH",   "reason": "User model definition — return type is Optional[User]"},
    {"path": "app/database.py",     "relevance": "MEDIUM", "reason": "DB session factory — get_user() can return None"},
    {"path": "tests/test_users.py", "relevance": "MEDIUM", "reason": "Existing tests — no test for missing user"},
    {"path": "requirements.txt",    "relevance": "LOW",    "reason": "Dependency versions — FastAPI 0.104"},
]

_STUB_SUBAGENT_FINDINGS: List[Dict] = [
    {
        "agent": "Subagent A — Log Analyzer",
        "focus": "Error patterns in app logs",
        "finding": "AttributeError on line 13 of app/main.py triggered for GET /users/999 (user does not exist).",
        "confidence": "HIGH",
    },
    {
        "agent": "Subagent B — Code Inspector",
        "focus": "Route handler source code",
        "finding": "`user.name` is accessed at line 13 with no None-check. `get_user()` returns `Optional[User]`.",
        "confidence": "HIGH",
    },
    {
        "agent": "Subagent C — Schema Validator",
        "focus": "DB model & return types",
        "finding": "models.py User.name is non-nullable, but get_user() legitimately returns None for missing IDs.",
        "confidence": "HIGH",
    },
    {
        "agent": "Subagent D — Test Coverage",
        "focus": "Existing test suite",
        "finding": "tests/test_users.py has no test for missing user_id. Zero coverage on the error path.",
        "confidence": "MEDIUM",
    },
]

_STUB_ROOT_CAUSE = {
    "file": "app/main.py",
    "line": 13,
    "summary": "Missing None-check before accessing user.name",
    "confidence": "HIGH",
    "explanation": (
        "get_user(user_id) returns None when the user does not exist in the database. "
        "The route handler at line 13 dereferences user.name without first checking whether "
        "user is None, raising AttributeError for any non-existent user_id."
    ),
}

_STUB_DIFF_HUNK = {
    "file": "app/main.py",
    "lineNumber": 11,
    "before": [
        '@app.get("/users/{user_id}")',
        "def get_user_route(user_id: int, db: Session = Depends(get_db)):",
        "    user = get_user(db, user_id)",
        '    return {"id": user.id, "name": user.name}',
    ],
    "after": [
        '@app.get("/users/{user_id}")',
        "def get_user_route(user_id: int, db: Session = Depends(get_db)):",
        "    user = get_user(db, user_id)",
        "    if user is None:",
        '        raise HTTPException(status_code=404, detail="User not found")',
        '    return {"id": user.id, "name": user.name}',
    ],
}

_STUB_TEST_RESULTS = [
    {"name": "test_get_existing_user",    "status": "PASSED", "message": None},
    {"name": "test_get_missing_user_404", "status": "PASSED", "message": "New regression test — GET /users/999 → 404"},
    {"name": "test_create_user",          "status": "PASSED", "message": None},
    {"name": "test_list_users",           "status": "PASSED", "message": None},
]


# ---------------------------------------------------------------------------
# LLM prompt helpers
# ---------------------------------------------------------------------------

def _parse_json_block(text: str, fallback: object) -> object:
    """Extract the first JSON block from an LLM response."""
    match = re.search(r"```json\s*(.*?)```", text, re.DOTALL)
    raw = match.group(1) if match else text
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        return fallback


# ---------------------------------------------------------------------------
# Public pipeline stage functions
# ---------------------------------------------------------------------------

def parse_log_lines(raw_log: str, log_path: str) -> list[dict]:
    """Stage 0 — Parse raw log text into structured log lines."""
    if _is_stub() or not raw_log.strip():
        return _STUB_LOG_LINES

    prompt = textwrap.dedent(f"""
        Parse the following application log and return a JSON array of objects.
        Each object must have exactly three keys: "time" (HH:MM:SS string),
        "level" (one of INFO, WARN, ERROR), "message" (string).
        Return ONLY a JSON code block — no explanation.

        Log path: {log_path}
        Log content:
        {raw_log}
    """).strip()

    text = _call_llm(prompt, max_tokens=800)
    return _parse_json_block(text, _STUB_LOG_LINES)  # type: ignore


def build_incident_brief(req_data: dict) -> dict:
    """Stage 1 — Construct / enrich a structured incident brief."""
    if _is_stub():
        return {
            "id": req_data.get("id", "INC-2024-001"),
            "title": req_data.get("title", "GET /users/{user_id} crashes with AttributeError"),
            "severity": req_data.get("severity", "P1"),
            "service": req_data.get("service", "user-service"),
            "errorType": req_data.get("errorType", "AttributeError"),
            "errorMessage": req_data.get("errorMessage", "'NoneType' object has no attribute 'name'"),
            "affectedEndpoint": req_data.get("affectedEndpoint", "GET /users/{user_id}"),
            "reportedAt": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        }

    prompt = textwrap.dedent(f"""
        You are an incident management assistant. Given the following incident data,
        return a JSON object with exactly these fields:
        id, title, severity (P1/P2/P3), service, errorType, errorMessage,
        affectedEndpoint, reportedAt (ISO timestamp string).
        Return ONLY a JSON code block.

        Input data:
        {json.dumps(req_data, indent=2)}
    """).strip()

    text = _call_llm(prompt, max_tokens=300)
    result = _parse_json_block(text, None)
    if not isinstance(result, dict):
        return build_incident_brief.__wrapped__(req_data)  # type: ignore
    return result


def collect_evidence(brief: dict, log_lines: list[dict]) -> list[dict]:
    """Stage 2 — Identify relevant files from the incident brief."""
    if _is_stub():
        return _STUB_EVIDENCE_FILES

    prompt = textwrap.dedent(f"""
        You are a code analysis agent. Given the incident brief and log lines below,
        identify the most relevant source files. Return a JSON array where each item has:
        "path" (file path string), "relevance" (HIGH/MEDIUM/LOW), "reason" (short string).
        Return ONLY a JSON code block with 3–6 items.

        Incident:
        {json.dumps(brief, indent=2)}

        Log lines (last errors):
        {json.dumps([l for l in log_lines if l.get("level") == "ERROR"], indent=2)}
    """).strip()

    text = _call_llm(prompt, max_tokens=500)
    return _parse_json_block(text, _STUB_EVIDENCE_FILES)  # type: ignore


def correlate_evidence(brief: dict, evidence_files: list[dict]) -> list[dict]:
    """Stage 3 — Run 4 parallel subagent analyses (simulated sequentially)."""
    if _is_stub():
        return _STUB_SUBAGENT_FINDINGS

    agents = [
        ("Subagent A — Log Analyzer",    "Error patterns in app logs"),
        ("Subagent B — Code Inspector",  "Route handler source code"),
        ("Subagent C — Schema Validator","DB model & return types"),
        ("Subagent D — Test Coverage",   "Existing test suite"),
    ]

    findings = []
    for agent_name, focus in agents:
        prompt = textwrap.dedent(f"""
            You are {agent_name}. Your focus is: {focus}.
            Analyse the incident and evidence files below and produce ONE key finding.
            Return a JSON object with keys:
            "agent" (string), "focus" (string), "finding" (string), "confidence" (HIGH/MEDIUM/LOW).
            Return ONLY a JSON code block.

            Incident: {json.dumps(brief)}
            Evidence files: {json.dumps(evidence_files)}
        """).strip()

        text = _call_llm(prompt, max_tokens=300)
        result = _parse_json_block(text, {
            "agent": agent_name,
            "focus": focus,
            "finding": "Analysis unavailable.",
            "confidence": "LOW",
        })
        findings.append(result)
    return findings


def analyze_root_cause(brief: dict, findings: list[dict]) -> dict:
    """Stage 4 — Determine root cause from correlated findings."""
    if _is_stub():
        return _STUB_ROOT_CAUSE

    prompt = textwrap.dedent(f"""
        You are a root cause analysis expert. Using the incident brief and
        subagent findings below, determine the single root cause.
        Return a JSON object with keys:
        "file" (string), "line" (integer), "summary" (short string),
        "confidence" (HIGH/MEDIUM/LOW), "explanation" (2–3 sentence string).
        Return ONLY a JSON code block.

        Incident: {json.dumps(brief)}
        Subagent findings: {json.dumps(findings, indent=2)}
    """).strip()

    text = _call_llm(prompt, max_tokens=400)
    result = _parse_json_block(text, _STUB_ROOT_CAUSE)
    if not isinstance(result, dict):
        return _STUB_ROOT_CAUSE
    return result


def recommend_fix(root_cause: Dict) -> Dict:
    """Stage 5 — Generate a before/after diff hunk for the fix."""
    if _is_stub():
        return _STUB_DIFF_HUNK

    prompt = textwrap.dedent(f"""
        You are a senior software engineer. Given the root cause below,
        produce a minimal code fix as a before/after diff hunk.
        Return a JSON object with keys:
        "file" (string), "lineNumber" (integer),
        "before" (array of strings — original lines),
        "after" (array of strings — fixed lines).
        Return ONLY a JSON code block.

        Root cause: {json.dumps(root_cause, indent=2)}
    """).strip()

    text = _call_llm(prompt, max_tokens=500)
    result = _parse_json_block(text, _STUB_DIFF_HUNK)
    if not isinstance(result, dict):
        return _STUB_DIFF_HUNK
    return result


def validate_tests(diff_hunk: Dict) -> List[Dict]:
    """Stage 7 — Generate representative test results after the fix."""
    if _is_stub():
        return _STUB_TEST_RESULTS

    prompt = textwrap.dedent(f"""
        You are a QA engineer. Given the code fix below, produce a list of
        pytest test results that should now pass.
        Return a JSON array where each item has:
        "name" (test function name string), "status" ("PASSED" or "FAILED"),
        "message" (optional short string or null).
        Include 3–5 tests; at least one should be a new regression test.
        Return ONLY a JSON code block.

        Fix applied:
        {json.dumps(diff_hunk, indent=2)}
    """).strip()

    text = _call_llm(prompt, max_tokens=400)
    result = _parse_json_block(text, _STUB_TEST_RESULTS)
    if not isinstance(result, list):
        return _STUB_TEST_RESULTS
    return result
