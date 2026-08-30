# IBM Bob Hackathon — Debug Agent + Sentinel

This repository contains two integrated systems built for the IBM watsonx Hackathon:

1. **Bob Debug Agent** — A full-stack web application that runs an 8-stage AI-powered incident pipeline (FastAPI + React + IBM Granite / watsonx.ai).
2. **Sentinel** — A Python agent for continuous test maintenance on IBM i RPG source members, using Bob as the reasoning engine to classify RPGUnit test failures.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Project Layout](#project-layout)
- [Bob Debug Agent](#bob-debug-agent)
  - [Pipeline Stages](#pipeline-stages)
  - [Backend (FastAPI)](#backend-fastapi)
  - [Frontend (React + Vite)](#frontend-react--vite)
  - [Running the Debug Agent](#running-the-debug-agent)
- [Sentinel — RPG Continuous Test Maintenance](#sentinel--rpg-continuous-test-maintenance)
  - [How Sentinel Works](#how-sentinel-works)
  - [Sentinel Modules](#sentinel-modules)
  - [Quick Start — Stub Demo](#quick-start--stub-demo-no-ibm-i-required)
  - [IBM i Live Mode](#ibm-i-connection-live-mode-only)
- [API Layer (`api/`)](#api-layer-api)
- [Test Suites](#test-suites)
  - [Backend Tests](#backend-tests-teststest_backendpy)
  - [API Tests](#api-tests-apitests)
  - [Frontend Tests](#frontend-tests-frontendsrctests)
- [Environment Variables](#environment-variables)
- [Security](#security)

---

## Project Overview

| Verdict | Meaning | Action |
|---------|---------|--------|
| **STALE TEST** | Code changed intentionally; test encodes the old behaviour | Bob proposes a test update diff for developer review |
| **REGRESSION** | Code change introduced a real bug; test is correct | Red banner — no patch, fix the source code |
| **NEW_COVERAGE_NEEDED** | New code branch added with no test | Bob proposes a new test procedure |
| **UNCERTAIN** | Evidence insufficient to decide | Escalated to the developer for manual judgement |

**Core differentiator:** A naive tool would silently update a failing assertion to match whatever the broken code produces. Sentinel refuses. When a failure is a genuine regression it stops, flags it, and surfaces it to the developer. The test is the contract — only intentional behaviour changes warrant test updates, and every proposed update requires explicit human acceptance.

---

## Project Layout

```
IBM-Bob-Hackathon/
├── backend/                  ← FastAPI + SQLite debug agent backend
│   ├── app.py                  API routes (incidents + Sentinel results)
│   ├── pipeline.py             8-stage debug pipeline orchestrator
│   ├── llm.py                  watsonx.ai / IBM Granite integration + stub mode
│   ├── models.py               Pydantic models (PipelineResult, SentinelClassification, …)
│   └── database.py             SQLite layer (incidents + sentinel_classifications tables)
├── frontend/                 ← React + Vite + TypeScript + Tailwind UI
│   ├── src/
│   │   ├── App.tsx             Main app — pipeline animation + API integration
│   │   ├── api/
│   │   │   ├── client.ts       Typed fetch wrappers for all backend endpoints
│   │   │   └── types.ts        TypeScript interfaces mirroring backend Pydantic models
│   │   ├── components/
│   │   │   └── pipelines/      One component per pipeline stage + shared utilities
│   │   ├── mockdata/           Static fallback data (incident + log lines)
│   │   └── tests/              Vitest component tests
│   └── public/                 SVG icons, logos, favicon
├── sentinel/                 ← Continuous test maintenance agent for IBM i RPG
│   ├── watcher.py              Main loop: compile event → diff → tests → classify → propose
│   ├── classifier.py           Invokes Bob Shell CLI; stub mode controlled by SENTINEL_BOB_STUB
│   ├── proposals.py            CLI review layer: coloured diff, [A]ccept/[R]eject/[E]dit
│   ├── diff.py                 Source member diff engine (unified diff + snapshot store)
│   ├── store.py                Flat-file snapshot store (.sentinel_store/)
│   ├── runner.py               RPGUnit test runner (RUCALLTST) wrapper
│   ├── parser.py               RPGUnit output → TestFailure dataclasses
│   ├── coverage.py             RUCOVERAGE invocation and coverage delta reporting
│   ├── ibmi.py                 IBM i itoolkit/XMLSERVICE connection layer
│   ├── models.py               TestFailure, Classification, CoverageReport dataclasses
│   ├── prompts/classify.txt    Bob prompt template for the live classification path
│   └── skill/SKILL.md          Bob reasoning specification — 6-step classification rules
├── api/                      ← RPG test maintenance evidence broker (FastAPI)
│   ├── main.py                 Endpoints: /health, /evidence, /classification-result, /results, /review-action
│   ├── models.py               EvidenceRequest, EvidencePayload, ClassificationResult, ReviewActionRequest
│   ├── evidence_service.py     Fixture loader (demo) + live Sentinel data bridge
│   ├── demo_cases/             Deterministic JSON fixtures for all three demo scenarios
│   │   ├── stale_test.json
│   │   ├── regression.json
│   │   └── uncertain.json
│   └── tests/                  pytest + httpx async API tests
│       ├── test_evidence.py
│       ├── test_models.py
│       └── test_results.py
├── tests/
│   └── test_backend.py         Integration tests for the FastAPI debug agent backend
├── demo/                     ← Scripted demo: RPG source + step-by-step presenter script
│   ├── ORDCALC.rpgle           Base source member (all tests pass)
│   ├── ORDCALCT.rpgle          RPGUnit test suite (3 procedures)
│   ├── changes/                Pre-scripted source variants for each demo step
│   │   ├── step1_stale.rpgle   Rounding rule change (2 dp → 1 dp)
│   │   ├── step2_regression.rpgle  Off-by-one bug
│   │   └── step3_new_branch.rpgle  New premium discount branch
│   └── README.md               Full step-by-step demo script with expected terminal output
├── scripts/                  ← Development utilities (run standalone)
│   ├── smoke_test_connection.py  Verify IBM i XMLSERVICE connectivity
│   ├── test_classifier.py        Send hardcoded diff + failure → print classification
│   ├── test_runner.py            Manually invoke RPGUnit and print parsed failures
│   ├── test_coverage.py          Manually invoke coverage reporter
│   ├── test_diff.py              Manually trigger a diff for a named member
│   └── demo_proposal.py          Feed a hardcoded Classification through present_proposal
├── .bob/
│   └── custom_modes.yaml       Bob custom mode: rpg-test-classifier
├── pyproject.toml              Python project config + all dependencies
├── requirements.txt            Flat dependency list (alternative to pyproject.toml)
└── SECURITY.MD                 Credential management guidelines
```

---

## Bob Debug Agent

### Pipeline Stages

The debug agent runs an **8-stage pipeline** for each incident:

| Stage | Component | Description |
|-------|-----------|-------------|
| 0 | Log Viewer | Parse raw application log text into structured `LogLine` records |
| 1 | Incident Intake | Build a structured `IncidentBrief` (ID, title, severity, service, error) |
| 2 | Evidence Collector | Identify relevant source files with `HIGH/MEDIUM/LOW` relevance ratings |
| 3 | Evidence Correlator | 4 parallel subagents (Log Analyzer, Code Inspector, Schema Validator, Test Coverage) each produce one finding |
| 4 | Root Cause Analyzer | Synthesise subagent findings into a single `RootCause` with file, line, and confidence |
| 5 | Fix Recommender | Generate a before/after `DiffHunk` for the minimal fix |
| 6 | Fix Implementer | Render the diff hunk as applied code (same hunk, no extra LLM call) |
| 7 | Test Validator | Produce representative `TestResult` records (pass/fail) after the fix |
| 8 | Report Generator | Assemble and display the final incident report summary |
| 10 | Sentinel Stage | Display IBM i RPG test classification results from Sentinel |

### Backend (FastAPI)

**Entry point:** [`backend/app.py`](backend/app.py)

#### Incident endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/` | Health check |
| `GET`  | `/api/incidents` | List all stored incidents (id, title, severity, service, created_at) |
| `POST` | `/api/incidents/run` | Run the full 8-stage pipeline and persist to SQLite |
| `GET`  | `/api/incidents/{id}` | Retrieve a stored pipeline result |
| `DELETE` | `/api/incidents/{id}` | Delete a stored incident |

#### Sentinel endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/sentinel/results` | Accept a Sentinel classification result (posted by `sentinel/proposals.py`) |
| `GET`  | `/api/sentinel/results` | Return all stored Sentinel classification results, newest first |

#### Key files

| File | Purpose |
|------|---------|
| [`backend/pipeline.py`](backend/pipeline.py) | Orchestrates all 8 pipeline stages; importable without an HTTP server |
| [`backend/llm.py`](backend/llm.py) | watsonx.ai / IBM Granite integration. `BACKEND_STUB=true` (default) returns deterministic data without network calls. `BACKEND_STUB=false` requires `WATSONX_API_KEY`, `WATSONX_PROJECT_ID`, `WATSONX_URL` |
| [`backend/models.py`](backend/models.py) | Pydantic models: `LogLine`, `IncidentBrief`, `EvidenceFile`, `SubagentFinding`, `RootCause`, `DiffHunk`, `TestResult`, `PipelineResult`, `SentinelClassification`, `RunIncidentRequest` |
| [`backend/database.py`](backend/database.py) | SQLite via plain `sqlite3` — `incidents` table + `sentinel_classifications` table. DB path configurable via `BACKEND_DB_PATH` (default `.backend_db/incidents.db`) |

#### LLM / stub mode

`BACKEND_STUB=true` is the **default** when no `WATSONX_API_KEY` is set. All pipeline stages return deterministic hard-coded data identical to the frontend mock data. No network calls are made — the full pipeline runs end-to-end in CI and during frontend development without credentials.

Set `BACKEND_STUB=false` and provide `WATSONX_API_KEY`, `WATSONX_PROJECT_ID`, and `WATSONX_URL` to use live IBM Granite inference.

### Frontend (React + Vite)

**Stack:** React 19, TypeScript, Vite 8, Tailwind CSS 3, Vitest 4

#### Pipeline stage components

| Component | Stage | Source |
|-----------|-------|--------|
| `LogViewerStage` | 0 | [`frontend/src/components/pipelines/LogViewerStage.tsx`](frontend/src/components/pipelines/LogViewerStage.tsx) |
| `IncidentIntakeStage` | 1 | [`frontend/src/components/pipelines/IncidentIntakeStage.tsx`](frontend/src/components/pipelines/IncidentIntakeStage.tsx) |
| `EvidenceCollectorStage` | 2 | [`frontend/src/components/pipelines/EvidenceCollectorStage.tsx`](frontend/src/components/pipelines/EvidenceCollectorStage.tsx) |
| `EvidenceCorrelatorStage` | 3 | [`frontend/src/components/pipelines/EvidenceCorrelatorStage.tsx`](frontend/src/components/pipelines/EvidenceCorrelatorStage.tsx) |
| `RootCauseStage` | 4 | [`frontend/src/components/pipelines/RootCauseStage.tsx`](frontend/src/components/pipelines/RootCauseStage.tsx) |
| `FixRecommenderStage` | 5 | [`frontend/src/components/pipelines/FixRecommenderStage.tsx`](frontend/src/components/pipelines/FixRecommenderStage.tsx) |
| `FixImplementerStage` | 6 | [`frontend/src/components/pipelines/FixImplementerStage.tsx`](frontend/src/components/pipelines/FixImplementerStage.tsx) |
| `TestValidatorStage` | 7 | [`frontend/src/components/pipelines/TestValidatorStage.tsx`](frontend/src/components/pipelines/TestValidatorStage.tsx) |
| `ReportGeneratorStage` | 8 | [`frontend/src/components/pipelines/ReportGeneratorStage.tsx`](frontend/src/components/pipelines/ReportGeneratorStage.tsx) |
| `SentinelStage` | 10 | [`frontend/src/components/pipelines/SentinelStage.tsx`](frontend/src/components/pipelines/SentinelStage.tsx) |

#### API client

[`frontend/src/api/client.ts`](frontend/src/api/client.ts) — typed fetch wrappers:
- `listIncidents()` — GET `/api/incidents`
- `loadIncident(id)` — GET `/api/incidents/{id}`
- `runIncident(req)` — POST `/api/incidents/run`
- `fetchOrRunIncident(req)` — load cached result or run pipeline
- `deleteIncident(id)` — DELETE `/api/incidents/{id}`
- `listSentinelResults()` — GET `/api/sentinel/results`

The Vite dev server proxies all `/api/*` requests to `http://localhost:8000` (see [`frontend/vite.config.ts`](frontend/vite.config.ts)).

### Running the Debug Agent

```bash
# 1. Install Python dependencies
pip install -e .
# or:  pip install -r requirements.txt

# 2. Start the FastAPI backend (stub mode — no credentials required)
uvicorn backend.app:app --reload
# Server runs at http://localhost:8000
# Interactive API docs at http://localhost:8000/docs

# 3. Install frontend dependencies and start the dev server
cd frontend
npm install
npm run dev
# UI runs at http://localhost:5173
```

For live AI inference, set the watsonx.ai environment variables before starting the backend:

```bash
export BACKEND_STUB=false
export WATSONX_API_KEY=your_key
export WATSONX_PROJECT_ID=your_project_id
export WATSONX_URL=https://us-south.ml.cloud.ibm.com
export WATSONX_MODEL_ID=ibm/granite-3-3-8b-instruct   # optional, this is the default
```

---

## Sentinel — RPG Continuous Test Maintenance

### How Sentinel Works

```
RPG source member compile
        |
        v
Sentinel detects compile event
        |
        v
Diff against last-known-good snapshot
        |
        v
Run RPGUnit test suite (RUCALLTST)
        |
  tests pass? --- YES -> commit snapshot, show coverage delta
        | NO
        v
Parse test failures (procedure, assertion, expected, actual)
        |
        v
Bob classifies each failure
  (diff + failing test + last-passing test + assertion output)
        |
        +-- STALE TEST         -> show coloured diff, prompt: [A]ccept [R]eject [E]dit
        +-- REGRESSION         -> red banner, no patch proposed, snapshot NOT updated
        +-- NEW_COVERAGE_NEEDED -> show proposed new test, prompt: [A]ccept [R]eject [E]dit
        +-- UNCERTAIN          -> yellow banner, escalate to developer
        |
        v
Developer reviews and decides — nothing auto-commits
        |
        v
Accepted patches saved to ./proposals/<timestamp>_<member>.patch
Bob Shell CLI notified via POST /api/sentinel/results (if SENTINEL_BACKEND_URL is set)
```

Bob is invoked as a subprocess via the Bob Shell CLI:
```
bob --auth-method api-key --chat-mode rpg-test-classifier
    --approval-mode auto_edit --hide-intermediary-output
```
The custom mode `rpg-test-classifier` (defined in [`.bob/custom_modes.yaml`](.bob/custom_modes.yaml)) carries the role definition and custom instructions. The prompt itself supplies the variable context (diff, failing test, last-passing test, assertion output).

### Sentinel Modules

| Module | Purpose |
|--------|---------|
| [`sentinel/watcher.py`](sentinel/watcher.py) | Main loop; CLI entry point (`python -m sentinel.watcher`) |
| [`sentinel/classifier.py`](sentinel/classifier.py) | Invokes Bob Shell CLI; stub controlled by `SENTINEL_BOB_STUB` |
| [`sentinel/proposals.py`](sentinel/proposals.py) | Rich CLI diff rendering, [A]ccept/[R]eject/[E]dit, saves patches, POSTs to backend |
| [`sentinel/diff.py`](sentinel/diff.py) | Fetches source member, diffs against snapshot, returns `DiffResult` |
| [`sentinel/store.py`](sentinel/store.py) | Flat-file snapshot store — reads/writes `.sentinel_store/*.rpgle` |
| [`sentinel/runner.py`](sentinel/runner.py) | Invokes RPGUnit `RUCALLTST`, captures output |
| [`sentinel/parser.py`](sentinel/parser.py) | Parses RPGUnit output into `TestFailure` dataclasses |
| [`sentinel/coverage.py`](sentinel/coverage.py) | Invokes `RUCOVERAGE`, parses procedure-coverage CSV, prints before/after delta |
| [`sentinel/ibmi.py`](sentinel/ibmi.py) | itoolkit/XMLSERVICE transport — `run_cl(cmd)`, `get_source_member(lib, srcpf, mbr)` |
| [`sentinel/models.py`](sentinel/models.py) | `TestFailure`, `Classification`, `CoverageReport` dataclasses |
| [`sentinel/prompts/classify.txt`](sentinel/prompts/classify.txt) | Prompt template for the live Bob subprocess path |
| [`sentinel/skill/SKILL.md`](sentinel/skill/SKILL.md) | Bob reasoning specification — 6-step classification rules and guardrails |

### Quick Start — Stub Demo (no IBM i required)

```powershell
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS

# 2. Install Sentinel
pip install -e .

# 3. Set stub-mode environment variables (no IBM i, no Bob API key needed)
$env:IBMI_STUB = "true"
$env:SENTINEL_BOB_STUB = "true"

# 4. Seed the baseline snapshot (must be done once before each demo step)
$env:SENTINEL_STUB_SCENARIO = "all_pass"
Remove-Item -Path ".sentinel_store\MYLIB__QRPGLESRC__ORDCALC.rpgle" -ErrorAction SilentlyContinue
python -c "from dotenv import load_dotenv; load_dotenv(); from sentinel.diff import seed_snapshot; seed_snapshot('MYLIB','QRPGLESRC','ORDCALC'); print('seeded')"

# 5. Run the stale-test scenario (intentional rounding change)
$env:SENTINEL_STUB_SCENARIO = "one_failure"
$env:SENTINEL_BOB_STUB_VERDICT = "stale"
python -m sentinel.watcher --lib MYLIB --srcpf QRPGLESRC --mbr ORDCALC --once

# 6. Reset and run the regression scenario (genuine off-by-one bug)
$env:SENTINEL_STUB_SCENARIO = "all_pass"
Remove-Item -Path ".sentinel_store\MYLIB__QRPGLESRC__ORDCALC.rpgle" -ErrorAction SilentlyContinue
python -c "from dotenv import load_dotenv; load_dotenv(); from sentinel.diff import seed_snapshot; seed_snapshot('MYLIB','QRPGLESRC','ORDCALC'); print('seeded')"

$env:SENTINEL_STUB_SCENARIO = "regression"
$env:SENTINEL_BOB_STUB_VERDICT = "regression"
python -m sentinel.watcher --lib MYLIB --srcpf QRPGLESRC --mbr ORDCALC --once
```

See [`demo/README.md`](demo/README.md) for the full step-by-step demo script including talking points, expected terminal output, and the new-coverage scenario.

### IBM i Connection (live mode only)

Sentinel connects to IBM i via **XMLSERVICE** over HTTP (itoolkit).

1. Ensure XMLSERVICE is installed: `CHKOBJ OBJ(QXMLSERV/XMLSTOREDP) OBJTYPE(*PGM)`
2. Start the IBM i HTTP server: `STRTCPSVR SERVER(*HTTP) HTTPSVR(ZSVR)`
3. Confirm the CGI endpoint: `http://<IBMI_HOST>:<IBMI_PORT>/cgi-bin/xmlcgi.pgm`
4. Verify: `python scripts/smoke_test_connection.py`

---

## API Layer (`api/`)

The `api/` package is a separate FastAPI service acting as the **evidence broker** for the Sentinel classification loop. Bob calls this API to retrieve structured evidence before classifying, and posts classification results back so the React UI can display them.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/health` | Health check |
| `POST` | `/evidence` | Return structured evidence for a given file + test. Pass `demo_case=stale_test\|regression\|uncertain` for deterministic fixture responses |
| `POST` | `/classification-result` | Accept Bob's classification result (stored in-memory, keyed by `test_name`) |
| `GET`  | `/results` | Return all stored classification results |
| `GET`  | `/results/{test_name}` | Return a single result by test name |
| `POST` | `/review-action` | Record developer's Accept / Reject / Flag decision |

### Models (`api/models.py`)

| Model | Description |
|-------|-------------|
| `Classification` (enum) | `STALE_TEST` \| `REGRESSION` \| `UNCERTAIN` |
| `RecommendedAction` (enum) | `UPDATE_TEST` \| `FIX_CODE` \| `ASK_HUMAN` \| `ADD_TEST` \| `NO_ACTION` |
| `ReviewAction` (enum) | `ACCEPT` \| `REJECT` \| `FLAG` |
| `EvidenceRequest` | `file`, `test_name`, optional `demo_case` |
| `EvidencePayload` | Full evidence context: diff, last-passing code/test, assertion output, coverage metrics |
| `ClassificationResult` | Bob's verdict + Pydantic validators enforcing safety invariants |
| `ReviewActionRequest` | `test_name` + `action` |

`ClassificationResult` enforces **safety invariants** at the model level:
- `REGRESSION` must NOT have `recommended_action=UPDATE_TEST` or a `proposed_diff`; must have `needs_human_review=True`
- `UNCERTAIN` must use `recommended_action=ASK_HUMAN`; must have `needs_human_review=True`
- Any `confidence < 0.6` requires `needs_human_review=True`
- `proposed_diff` is only allowed for `STALE_TEST` + `UPDATE_TEST`

### Running the API server

```bash
pip install fastapi uvicorn "pydantic>=2" httpx
uvicorn api.main:app --reload --port 8001
# Docs at http://localhost:8001/docs
```

---

## Test Suites

### Backend Tests (`tests/test_backend.py`)

Integration tests for the FastAPI debug agent backend. Runs entirely with `BACKEND_STUB=true` (no watsonx.ai credentials required). Uses FastAPI `TestClient` (requires `httpx`).

```bash
pytest tests/test_backend.py -v
```

**Tests covered:**

| Test | Description |
|------|-------------|
| `test_health` | GET `/` returns `{"status": "ok"}` |
| `test_run_pipeline_stub` | POST `/api/incidents/run` returns full `PipelineResult` with all fields |
| `test_list_incidents_empty` | GET `/api/incidents` returns `[]` on empty DB |
| `test_list_incidents_after_run` | Incident appears in list after pipeline run |
| `test_get_incident_not_found` | GET `/api/incidents/INC-MISSING` returns 404 |
| `test_get_incident_after_run` | GET `/api/incidents/{id}` returns correct stored result |
| `test_delete_incident` | DELETE `/api/incidents/{id}` removes the incident |
| `test_delete_incident_not_found` | DELETE on non-existent ID returns 404 |

### API Tests (`api/tests/`)

pytest + httpx async tests against the `api/` evidence broker. No IBM i connection or API key required.

```bash
pip install fastapi uvicorn "pydantic>=2" httpx pytest pytest-asyncio
cd api
pytest tests/ -v
```

#### `test_evidence.py`

| Test | Description |
|------|-------------|
| `test_health` | GET `/health` returns `{"status": "ok"}` |
| `test_evidence_stale_test` | Stale test fixture returns correct fields including `developer_intent` |
| `test_evidence_regression` | Regression fixture returns correct `expected`/`actual` values; `developer_intent` is None |
| `test_evidence_uncertain` | Uncertain fixture returns correct assertion values |
| `test_evidence_unknown_demo_case` | Unknown `demo_case` returns 400 |
| `test_evidence_no_demo_case_returns_501` | Live mode (no `demo_case`) returns 501 when Sentinel is unavailable |
| `test_evidence_missing_required_fields` | Missing `file` or `test_name` returns 422 |

#### `test_models.py`

Validates Pydantic model schema and enum constraints (28 test cases), including:
- Enum completeness for `Classification`, `RecommendedAction`, `ReviewAction`
- `EvidenceRequest` required fields
- `EvidencePayload` numeric bounds (`coverage_before` 0–100, `tests_passing/failing` ≥ 0)
- `ClassificationResult` safety invariants (REGRESSION, UNCERTAIN, low-confidence, `proposed_diff` gate)
- Multiple violation reporting (all constraint errors surfaced together)

#### `test_results.py`

| Test group | Description |
|------------|-------------|
| POST `/classification-result` | Store stale, regression, uncertain results; overwrite; invalid confidence; invalid classification enum |
| GET `/results` | Empty list; all results returned |
| GET `/results/{test_name}` | Retrieve by name; 404 for unknown |
| POST `/review-action` | Accept, Reject, Flag actions; invalid action returns 422 |

### Frontend Tests (`frontend/src/tests/`)

Vitest + React Testing Library component tests. Run with:

```bash
cd frontend
npm test          # single run
npm run test:watch  # watch mode
```

| Test file | Component | Tests |
|-----------|-----------|-------|
| `StepTracker.test.tsx` | `StepTracker` | Renders all labels, status text, defaults to pending for unknown ID |
| `shared.test.tsx` | `StageShell`, `ConfidenceBadge`, `StatusBadge`, `Connector` | Stage number/label/title/description, HIGH/MEDIUM/LOW badges, done/running/pending status, renders without crash |
| `EvidenceCollectorStage.test.tsx` | `EvidenceCollectorStage` | Evidence file list rendering |
| `EvidenceCorrelatorStage.test.tsx` | `EvidenceCorrelatorStage` | Subagent findings rendering |
| `FixRecommenderStage.test.tsx` | `FixRecommenderStage` | Diff hunk before/after rendering |
| `IncidentIntakeStage.test.tsx` | `IncidentIntakeStage` | Incident brief fields |
| `LogViewerStage.test.tsx` | `LogViewerStage` | Log line list with level badges |
| `RootCauseStage.test.tsx` | `RootCauseStage` | Root cause file, line, summary, confidence |
| `TestValidatorStage.test.tsx` | `TestValidatorStage` | Test result pass/fail rendering |

---

## Environment Variables

### Stub mode (demo — no IBM i or Bob API key required)

| Variable | Purpose | Values |
|----------|---------|--------|
| `IBMI_STUB` | Skip all IBM i calls; return deterministic RPG source | `true` / `false` |
| `SENTINEL_BOB_STUB` | Skip the real Bob subprocess call; return a hardcoded verdict | `true` / `false` |
| `SENTINEL_STUB_SCENARIO` | Which RPGUnit output to simulate | `one_failure` / `all_pass` / `regression` |
| `SENTINEL_BOB_STUB_VERDICT` | Which verdict to return in stub mode | `stale` / `regression` / `new_coverage` / `uncertain` |
| `SENTINEL_STUB_COVERAGE_BEFORE` | Coverage figure shown before the change | e.g. `2/4` |
| `SENTINEL_STUB_COVERAGE_AFTER` | Coverage figure shown after accepting a patch | e.g. `3/4` |
| `BACKEND_STUB` | Skip watsonx.ai LLM calls; return mock data | `true` (default) / `false` |

### Live mode (real IBM i + Bob + watsonx.ai)

| Variable | Purpose | Default |
|----------|---------|---------|
| `IBMI_HOST` | IBM i hostname or IP | — |
| `IBMI_USER` | IBM i user profile | — |
| `IBMI_PASSWORD` | IBM i password | — |
| `IBMI_PORT` | XMLSERVICE HTTP port | `80` |
| `BOBSHELL_API_KEY` | Inference-scoped API key from bob.ibm.com | — |
| `SENTINEL_POLL_INTERVAL_SECS` | Watcher poll interval | `5` |
| `SENTINEL_CONFIDENCE_THRESHOLD` | Minimum confidence for a non-UNCERTAIN verdict | `0.75` |
| `SENTINEL_BACKEND_URL` | Backend URL for POSTing Sentinel results to the React UI | e.g. `http://localhost:8000` |
| `SENTINEL_PROPOSALS_DIR` | Directory for accepted/rejected patch files | `proposals` |
| `WATSONX_API_KEY` | IBM watsonx.ai API key | — |
| `WATSONX_PROJECT_ID` | watsonx.ai project ID | — |
| `WATSONX_URL` | watsonx.ai service URL | — |
| `WATSONX_MODEL_ID` | Granite model to use | `ibm/granite-3-3-8b-instruct` |
| `BACKEND_CORS_ORIGINS` | Comma-separated allowed CORS origins | `http://localhost:5173` |
| `BACKEND_DB_PATH` | SQLite database file path | `.backend_db/incidents.db` |

---

## Security

- `.gitignore` and `.bobignore` prevent committing credentials and AI session logs
- All credentials are loaded from `.env` (copy `.env.example` to `.env` and fill in values)
- See [`SECURITY.MD`](SECURITY.MD) for detailed guidelines on credential management, AI assistant safety, and what to do if credentials are accidentally exposed
