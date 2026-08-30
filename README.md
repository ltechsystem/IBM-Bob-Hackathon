# Sentinel — Continuous Test Maintenance for IBM i RPG

Sentinel is a Python agent that watches legacy IBM i RPG source members, runs the
RPGUnit test suite after each compile, and uses **Bob (IBM's AI coding assistant)**
to classify each test failure into one of three verdicts:

| Verdict | Meaning | Action |
|---------|---------|--------|
| **STALE TEST** | The code changed intentionally; the test encodes the old behaviour | Bob proposes a test update diff for developer review |
| **REGRESSION** | The code change introduced a real bug; the test is correct | Red banner, no patch — fix the source code |
| **UNCERTAIN** | Evidence is insufficient to decide | Escalated to the developer for manual judgement |

**The core differentiator:** a naive tool would silently update a failing assertion
to match whatever the broken code now produces. Sentinel refuses to do this.
When a failure is a genuine regression, it stops, flags it, and surfaces it to the
developer. The test is the contract. Only intentional behaviour changes warrant test
updates — and even then, every proposed update requires an explicit human accept.

---

## How it works

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
        +-- STALE TEST    -> show coloured diff, prompt: [A]ccept [R]eject [E]dit
        +-- REGRESSION    -> red banner, no patch proposed, snapshot NOT updated
        +-- UNCERTAIN     -> yellow banner, escalate to developer
        |
        v
Developer reviews and decides — nothing auto-commits
```

Bob is invoked as a subprocess via the Bob Shell CLI
(`bob --auth-method api-key --chat-mode rpg-test-classifier`). The custom Bob mode
and SKILL.md reasoning spec live in `.bob/` and `sentinel/skill/`.

---

## Quick start — stub demo (no IBM i required)

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

See [`demo/README.md`](demo/README.md) for the full step-by-step demo script including
talking points, expected terminal output, and the new-coverage scenario.

---

## Running the API test suite

```bash
pip install fastapi uvicorn "pydantic>=2" httpx pytest pytest-asyncio
cd api
pytest tests/ -v
```

---

## Project layout

| Path | Purpose |
|------|---------|
| `sentinel/` | Python watcher, diff engine, RPGUnit runner, parser, coverage, classifier, proposals |
| `sentinel/classifier.py` | Invokes Bob Shell CLI; stub mode controlled by `SENTINEL_BOB_STUB` |
| `sentinel/skill/SKILL.md` | Bob reasoning specification — 6-step classification rules and guardrails |
| `sentinel/prompts/classify.txt` | Prompt template for the real Bob subprocess path |
| `sentinel/watcher.py` | Main loop: compile event -> diff -> tests -> classify -> propose |
| `api/` | FastAPI evidence broker (`/evidence`, `/classification-result`, `/results`) |
| `api/demo_cases/` | Deterministic JSON fixtures for all three demo scenarios |
| `api/tests/` | API test suite (pytest + httpx, in-process ASGI) |
| `.bob/custom_modes.yaml` | Bob custom mode definition for `rpg-test-classifier` |
| `demo/` | Demo script, RPG source files, and changed-source variants |
| `scripts/` | Development utilities: classifier test, proposal preview, smoke test, coverage test |

---

## Environment variables

### Stub mode (demo — no IBM i or Bob API key required)

| Variable | Purpose | Values |
|----------|---------|--------|
| `IBMI_STUB` | Skip all IBM i calls; return deterministic RPG source | `true` / `false` |
| `SENTINEL_BOB_STUB` | Skip the real Bob subprocess call; return a hardcoded verdict | `true` / `false` |
| `SENTINEL_STUB_SCENARIO` | Which RPGUnit output to simulate | `one_failure` / `all_pass` / `regression` |
| `SENTINEL_BOB_STUB_VERDICT` | Which verdict to return in stub mode | `stale` / `regression` / `new_coverage` / `uncertain` |
| `SENTINEL_STUB_COVERAGE_BEFORE` | Coverage figure shown before the change | e.g. `2/4` |
| `SENTINEL_STUB_COVERAGE_AFTER` | Coverage figure shown after accepting a patch | e.g. `3/4` |

### Live mode (real IBM i + Bob)

| Variable | Purpose | Default |
|----------|---------|---------|
| `IBMI_HOST` | IBM i hostname or IP | — |
| `IBMI_USER` | IBM i user profile | — |
| `IBMI_PASSWORD` | IBM i password | — |
| `IBMI_PORT` | XMLSERVICE HTTP port | `80` |
| `BOBSHELL_API_KEY` | Inference-scoped API key from bob.ibm.com | — |
| `SENTINEL_POLL_INTERVAL_SECS` | Watcher poll interval | `5` |
| `SENTINEL_CONFIDENCE_THRESHOLD` | Minimum confidence for a non-UNCERTAIN verdict | `0.75` |

---

## IBM i connection (live mode only)

Sentinel connects to IBM i via **XMLSERVICE** over HTTP (itoolkit).

1. Ensure XMLSERVICE is installed: `CHKOBJ OBJ(QXMLSERV/XMLSTOREDP) OBJTYPE(*PGM)`
2. Start the IBM i HTTP server: `STRTCPSVR SERVER(*HTTP) HTTPSVR(ZSVR)`
3. Confirm the CGI endpoint: `http://<IBMI_HOST>:<IBMI_PORT>/cgi-bin/xmlcgi.pgm`
4. Verify: `python scripts/smoke_test_connection.py`

---

## Security

- `.gitignore` and `.bobignore` prevent committing credentials and AI session logs
- All credentials are loaded from `.env` (copy `.env.example` to `.env` and fill in values)
- See [`SECURITY.MD`](SECURITY.MD) for detailed guidelines
