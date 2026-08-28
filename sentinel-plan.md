# Sentinel — Continuous Test Maintenance for Legacy RPG

## Top-Level Overview

Sentinel is a Python background agent that watches an IBM i source member codebase, runs RPGUnit tests after a successful compile, and — using Bob as its reasoning engine — classifies each test failure as either a **stale test** (intentional code change broke an outdated assertion) or a **genuine regression** (the change introduced a real bug). For stale tests it proposes a repaired test as a reviewable diff. For regressions it halts and flags. For uncovered new code it proposes a new test. Nothing is auto-committed; every proposal requires an explicit developer accept or reject.

**Runtime:** Python
**IBM i connection:** itoolkit / Code for IBM i open-source tooling
**Review layer:** CLI diff view (web view is a stretch goal)
**Environment:** Live IBM i with RPGUnit installed
**Test suite naming convention:** Append `T` suffix (e.g. `ORDCALC` → `ORDCALCT`)
**Bob integration:** `ibm-watsonx-ai` Python SDK calling watsonx.ai inference API directly

**Scope boundary:** Procedure-level unit tests only. No DB2 integration, no cross-module analysis, no IDE extension, no multi-user persistence, no auth.

---

## Architecture at a Glance

```
[IBM i source member] --compile--> [Sentinel Watcher]
                                         |
                                    diff against last-known-good
                                         |
                                   [RPGUnit Runner]
                                         |
                              parse failures + assertion output
                                         |
                                   [Bob Classifier]
                          (diff + failing test + last passing state + assertion)
                                         |
                          confidence >= threshold?
                                /                  \
                           YES                      NO
                 stale / regression / new     Ask developer which
                         |
                  [Proposal Engine]
              render git-style diff to CLI
                         |
              developer: accept / reject / edit
```

---

## Sub-Tasks

---

### Sub-Task 1 — Project Scaffold and IBM i Connection Layer

**Intent**  
Establish the Python project structure, dependency management, and a verified connection to IBM i using itoolkit. This is the foundation everything else builds on and must be validated first — if IBM i connectivity fails, the whole project is blocked.

**Expected Outcomes**
- `pyproject.toml` or `requirements.txt` with all dependencies declared
- `sentinel/` package directory with `__init__.py`
- `sentinel/ibmi.py` module that can connect to IBM i, run a CL command, and return its output
- `.env.example` updated with the IBM i connection variables
- A smoke-test script that prints "IBM i connection OK" when run

**Todo List**
1. Create `pyproject.toml` (or `requirements.txt`) with dependencies: `itoolkit`, `python-dotenv`, `watchdog`, `rich` (CLI rendering), `ibm-watsonx-ai` (Bob/watsonx inference)
2. Create `sentinel/` package with `__init__.py`
3. Create `sentinel/ibmi.py` — wraps itoolkit transport, exposes `run_cl(command) -> str` and `get_source_member(lib, srcpf, mbr) -> str`
4. Update `.env.example` with `IBMI_HOST`, `IBMI_USER`, `IBMI_PASSWORD`, `IBMI_PORT`
5. Create `scripts/smoke_test_connection.py` that calls `run_cl("DSPJOB")` and asserts a non-empty result
6. Add `README.md` section on setup and connection requirements

**Relevant Context**
- itoolkit docs: https://python-itoolkit.readthedocs.io
- `.env.example` already exists in repo root — extend it, do not replace it
- `.gitignore` already ignores `.env` files — credentials are safe

**Status:** [x] done

---

### Sub-Task 2 — Source Member Watcher and Diff Engine

**Intent**  
Detect when a source member has been successfully compiled and produce a structured diff between the new version and the last-known-good version. This diff is the primary input to the Bob classifier.

**Expected Outcomes**
- `sentinel/watcher.py` — polls or watches for compile-complete events on IBM i
- `sentinel/diff.py` — fetches the current source member text, compares against the stored snapshot, and returns a unified diff string
- `sentinel/store.py` — simple file-based snapshot store (last-known-good text keyed by `lib/srcpf/mbr`)
- On a detected compile event, a diff string is printed to the terminal (raw, ugly is fine at this stage)

**Todo List**
1. Decide and implement compile detection strategy: poll the job log or a compile-output queue via `run_cl` for a CPFXXXX success message (document the chosen CL command in a comment)
2. Create `sentinel/store.py` — reads/writes member snapshots to `.sentinel_store/` directory as plain `.rpgle` text files
3. Create `sentinel/diff.py` — calls `get_source_member()`, diffs against the stored snapshot using Python's `difflib.unified_diff`, returns the diff string and updates the snapshot on success
4. Create `sentinel/watcher.py` — main polling loop, calls compile detection, triggers diff on a new compile, logs member name and diff summary to terminal
5. Write a manual test: `scripts/test_diff.py` — manually triggers a diff for a named member without needing a compile event

**Relevant Context**
- `sentinel/ibmi.py` from Sub-Task 1 provides `run_cl` and `get_source_member`
- Snapshot store lives in `.sentinel_store/` — add this to `.gitignore`
- Keep the polling interval configurable via an env var `SENTINEL_POLL_INTERVAL_SECS` (default 5)

**Status:** [x] done

---

### Sub-Task 3 — RPGUnit Runner and Failure Parser

**Intent**  
Invoke the RPGUnit test runner against the affected test suite on IBM i and parse its output into structured failure records. Each record carries the test name, the assertion that failed, and the actual vs expected values — exactly the context Bob needs.

**Expected Outcomes**
- `sentinel/runner.py` — invokes RPGUnit via CL command for a given service program, captures output
- `sentinel/parser.py` — parses RPGUnit XML or text output into a list of `TestFailure` dataclasses
- Given a compile event for member `MYMOD`, the watcher can identify the corresponding test suite `MYMODT` and return a list of `TestFailure` objects
- A manual test script `scripts/test_runner.py` runs the suite and prints parsed failures

**Todo List**
1. Determine the exact CL command to invoke RPGUnit (typically `RUCALLTST`) and document it in a comment in `runner.py`
2. Create `sentinel/runner.py` — takes `(lib, test_svcpgm)` parameters, runs the test command via `run_cl`, captures full output
3. Determine RPGUnit output format (XML via `RUTESTRMT` or plain text) and document the decision
4. Create `sentinel/parser.py` — parses the output into a list of `TestFailure(test_name, procedure, assertion, expected, actual, raw_output)` dataclasses
5. Create a naming convention function in `runner.py`: given source member name, return the assumed test suite name (e.g. append `T` suffix — make this configurable)
6. Wire runner invocation into `watcher.py` after a diff is produced
7. Write `scripts/test_runner.py` — manually invoke and parse for a named test suite

**Relevant Context**
- RPGUnit CL commands: `RUCALLTST`, `RUCRTTST`; output format depends on RPGUnit version installed — confirm against the live environment
- `sentinel/ibmi.py` `run_cl` is the execution primitive
- `TestFailure` dataclass lives in `sentinel/models.py` (create this file)

**Status:** [x] done

---

### Sub-Task 4 — Bob Classifier Integration

**Intent**  
For each `TestFailure`, call Bob with a structured prompt containing the change diff, the failing test source, the last-passing test source, and the assertion failure output. Bob returns a classification: `STALE`, `REGRESSION`, or `NEW_COVERAGE_NEEDED`, plus a confidence score and a plain-language rationale.

**Expected Outcomes**
- `sentinel/classifier.py` — builds the prompt, calls the Bob/watsonx API, parses the structured response
- `sentinel/models.py` extended with `Classification(verdict, confidence, rationale, proposed_test_patch)` dataclass
- A confidence threshold (env var `SENTINEL_CONFIDENCE_THRESHOLD`, default `0.75`) — below it the verdict is `UNCERTAIN`
- A manual test script `scripts/test_classifier.py` that sends a hardcoded diff + failure and prints the classification
- Bob API call stubbed by a flag `SENTINEL_BOB_STUB=true` so the pipeline can run without a live Bob call during development

**Todo List**
1. Create `sentinel/models.py` with `TestFailure` and `Classification` dataclasses
2. Create `sentinel/classifier.py` — `classify(diff: str, failure: TestFailure, last_good_test: str) -> Classification`
3. Write the Bob prompt template in `sentinel/prompts/classify.txt` — inputs are: `{diff}`, `{failing_test}`, `{last_good_test}`, `{assertion_output}`; instruct the model to respond in a parseable format: `VERDICT: <STALE|REGRESSION|NEW_COVERAGE_NEEDED>`, `CONFIDENCE: <0.0-1.0>`, `RATIONALE: <text>`, `PROPOSED_PATCH: <unified diff or empty>`
4. Add response parser in `classifier.py` that extracts the four fields from Bob's text response
5. Implement the confidence gate: if confidence < threshold, override verdict to `UNCERTAIN` and do not populate `proposed_patch`
6. Implement the stub mode: if `SENTINEL_BOB_STUB=true`, return a hardcoded `Classification` without making an API call
7. Add `WATSONX_API_KEY`, `WATSONX_PROJECT_ID`, `WATSONX_URL`, `WATSONX_MODEL_ID`, `SENTINEL_CONFIDENCE_THRESHOLD` to `.env.example`
8. Write `scripts/test_classifier.py`

**Relevant Context**
- The stub mode is critical for allowing Sub-Tasks 2, 3, and 5 to be developed and tested without a live Bob dependency
- Prompt file in `sentinel/prompts/classify.txt` keeps the prompt reviewable and editable without touching Python code
- The four-field response format must be strict enough to parse reliably; if Bob returns freeform text, the parser should log a warning and return `UNCERTAIN`

**Status:** [ ] pending

---

### Sub-Task 5 — Proposal Engine and CLI Review Layer

**Intent**  
Render each classification result as a human-readable, git-style diff in the terminal and give the developer an explicit accept / reject / edit prompt per proposal. Accepted proposals are written to a local patch file ready to apply. This is where the usability score lives — do not ship raw log output.

**Expected Outcomes**
- `sentinel/proposals.py` — takes a `Classification`, renders the proposed patch as a coloured unified diff using `rich`, prompts the developer
- Accepted patches are saved to `./proposals/<timestamp>_<member>.patch`
- Rejected patches are logged to `./proposals/<timestamp>_<member>.rejected`
- For `REGRESSION` verdict: no patch is offered; a red banner is printed: "REGRESSION DETECTED — manual review required"
- For `UNCERTAIN` verdict: both interpretations are shown and the developer is asked to classify manually
- A clear demo-ready terminal output with colour coding: green for stale proposals, red for regressions, yellow for uncertain

**Todo List**
1. Create `sentinel/proposals.py` with `present_proposal(classification: Classification, member: str)` — the main entry point
2. Use `rich.syntax` for diff highlighting and `rich.panel` for verdict banners
3. Implement the three render paths: `STALE`/`NEW_COVERAGE_NEEDED` (show diff, prompt accept/reject/edit), `REGRESSION` (red banner, no patch), `UNCERTAIN` (show both sides, ask developer to classify)
4. For `edit` choice: open the patch in `$EDITOR` (fall back to `notepad` on Windows), re-read the edited file, save as accepted patch
5. Save accepted/rejected files under `./proposals/` — add this directory to `.gitignore` (or add a `.gitkeep` and ignore `*.patch`)
6. Wire `proposals.py` into `watcher.py` as the final step of the pipeline: compile → diff → run tests → classify → present proposal
7. Write `scripts/demo_proposal.py` — feeds a hardcoded `Classification` through `present_proposal` so the UI can be developed and rehearsed without the full pipeline running

**Relevant Context**
- `rich` is already in the dependency list from Sub-Task 1
- The `edit` path needs to handle the case where `$EDITOR` is not set gracefully
- `proposals/` directory should be created on first run if it does not exist

**Status:** [ ] pending

---

### Sub-Task 6 — Coverage Instrumentation

**Intent**  
Measure RPGUnit line/procedure coverage before and after the change and display the delta as a concrete number in the terminal output. This satisfies the "Effectiveness" judging criterion — a number is worth more than a claim.

**Expected Outcomes**
- `sentinel/coverage.py` — invokes the RPGUnit coverage report command, parses the result into a `CoverageReport(procedures_total, procedures_covered, pct)` dataclass
- The watcher prints "Coverage before: X% → after: Y% (+Z%)" at the end of each pipeline run
- A manual test script `scripts/test_coverage.py`

**Todo List**
1. Determine the RPGUnit command for coverage reporting (check `RUCOVERAGE` or equivalent in the live environment)
2. Create `sentinel/coverage.py` with `get_coverage(lib, svcpgm) -> CoverageReport`
3. Extend `sentinel/models.py` with the `CoverageReport` dataclass
4. In `watcher.py`, capture coverage before running tests, then capture it again after proposals are accepted, and print the delta using `rich`
5. If the RPGUnit version does not support coverage, stub it with a warning and a hardcoded delta for demo purposes — document this clearly
6. Write `scripts/test_coverage.py`

**Relevant Context**
- Coverage is the last sub-task because it depends on the runner being stable (Sub-Task 3) and is the highest-risk unknown (RPGUnit version may not support it)
- If coverage is not available: the delta display can be faked with procedure-count before/after as a proxy metric — acceptable for demo

**Status:** [ ] pending

---

### Sub-Task 7 — Demo Hardening and Sample RPG Module

**Intent**  
Create the scripted demo RPG module and test suite that will be used in the live demo. Pre-script every change so the demo runs deterministically. This is not application code — it is demo infrastructure.

**Expected Outcomes**
- `demo/` directory containing:
  - `ORDCALC.rpgle` — sample RPG procedure with a rounding rule and a discount branch
  - `ORDCALCT.rpgle` — corresponding RPGUnit test suite with three tests (one per scenario)
  - `changes/step1_stale.rpgle` — the version of `ORDCALC` that makes one test stale
  - `changes/step2_regression.rpgle` — a version that introduces a real bug
  - `changes/step3_new_branch.rpgle` — a version that adds an uncovered branch
- A `demo/README.md` describing each step, the expected Sentinel output, and what to say at each moment
- The demo can be run start-to-finish by following the `demo/README.md` without improvisation

**Todo List**
1. Write `ORDCALC.rpgle` — a simple order calculation procedure: `calcTotal(qty, price, discount) -> total` with a rounding rule
2. Write `ORDCALCT.rpgle` — three RPGUnit tests: basic calculation, boundary discount, rounding
3. Write `changes/step1_stale.rpgle` — change the rounding rule (intentional change that makes the rounding test stale)
4. Write `changes/step2_regression.rpgle` — introduce an off-by-one error (genuine regression)
5. Write `changes/step3_new_branch.rpgle` — add a new premium discount tier with no test coverage
6. Write `demo/README.md` — step-by-step demo script with expected terminal output at each step and presenter notes
7. Rehearse the full pipeline end-to-end using the demo scripts and fix anything that breaks

**Relevant Context**
- The demo module must be simple enough to understand at a glance on a conference screen
- Steps 7 and 8 of the pitch (regression detection and uncertain classification) are the differentiators — they must not be cut
- RPGUnit test procedures follow the pattern: `dcl-proc test_XXX; ... assert(...); end-proc;`

**Status:** [ ] pending

---

## Dependency Order

```
Sub-Task 1 (scaffold + IBM i connection)
    |
    +---> Sub-Task 2 (watcher + diff)
    |         |
    |         +---> Sub-Task 3 (runner + parser)
    |                   |
    |                   +---> Sub-Task 4 (Bob classifier)
    |                               |
    |                               +---> Sub-Task 5 (proposals + CLI)
    |                                           |
    |                                           +---> Sub-Task 6 (coverage)
    |
    +---> Sub-Task 7 (demo module) -- can start in parallel after Sub-Task 1
```

Sub-Tasks 4 and 5 can be developed with stub data before Sub-Tasks 2 and 3 are complete, thanks to the stub mode and demo scripts.

---

## Cut Scope (explicitly out)

- Real VS Code / RDi extension
- DB2 integration tests
- Auth, multi-user, persistence beyond flat files
- Cross-module dependency analysis
- Web view (stretch goal only — implement only if Sub-Tasks 1–6 are complete and stable)

---

## Key Environment Variables

| Variable | Purpose | Default |
|---|---|---|
| `IBMI_HOST` | IBM i hostname | — |
| `IBMI_USER` | IBM i username | — |
| `IBMI_PASSWORD` | IBM i password | — |
| `WATSONX_API_KEY` | watsonx.ai API key | — |
| `WATSONX_PROJECT_ID` | watsonx.ai project ID | — |
| `WATSONX_URL` | watsonx.ai service URL | — |
| `WATSONX_MODEL_ID` | Model to use for classification | `ibm/granite-13b-instruct-v2` |
| `SENTINEL_POLL_INTERVAL_SECS` | Watcher poll interval | `5` |
| `SENTINEL_CONFIDENCE_THRESHOLD` | Min confidence for auto-verdict | `0.75` |
| `SENTINEL_BOB_STUB` | Skip real Bob call | `false` |
