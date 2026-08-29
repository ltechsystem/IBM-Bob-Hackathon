# Restructure Plan — Remove `des_review/` Personal-Name Wrapper

## Overview

The `des_review/` folder was contributed under a personal-name branch and needs to be
promoted to proper project-level locations. Its contents form the REST API layer and
Bob reasoning skill for the Sentinel system. The goal is a flat, descriptive layout
that makes the project's structure self-evident to any new contributor.

### Target Layout

```
IBM-Bob-Hackathon/
├── api/                        ← was des_review/backend/
│   ├── __init__.py
│   ├── main.py
│   ├── models.py
│   ├── evidence_service.py
│   ├── requirements.txt
│   ├── demo_cases/
│   │   ├── stale_test.json
│   │   ├── regression.json
│   │   └── uncertain.json
│   └── tests/                  ← was des_review/tests/
│       ├── __init__.py
│       ├── test_evidence.py
│       ├── test_models.py
│       └── test_results.py
├── sentinel/
│   ├── skill/                  ← was des_review/test-failure-classifier/
│   │   └── SKILL.md
│   └── ... (existing files unchanged)
└── ... (all other root files unchanged)
```

---

## Sub-Tasks

---

### Sub-Task 1 — Move `des_review/backend/` → `api/`

**Intent**
Replace the personal-name wrapper with a conventional `api/` directory at the root.
All Python source files, demo fixtures, and the requirements file move verbatim —
no content changes, only paths.

**Expected Outcomes**
- `api/` exists at the repo root with all backend files inside it.
- `api/requirements.txt` is present and identical to `des_review/backend/requirements.txt`.
- `des_review/backend/` no longer exists.

**Todo List**
1. Create `api/` directory by moving `des_review/backend/__init__.py` → `api/__init__.py`
2. Move `des_review/backend/main.py` → `api/main.py`
3. Move `des_review/backend/models.py` → `api/models.py`
4. Move `des_review/backend/evidence_service.py` → `api/evidence_service.py`
5. Move `des_review/backend/requirements.txt` → `api/requirements.txt`
6. Move `des_review/backend/demo_cases/` → `api/demo_cases/` (all three JSON files)

**Relevant Context**
- Source: `des_review/backend/`
- `evidence_service.py` loads fixtures via a relative path — verify the path still resolves after move (currently uses `Path(__file__).parent / "demo_cases"`)

**Status** — `[ ] pending`

---

### Sub-Task 2 — Move `des_review/tests/` → `api/tests/`

**Intent**
Keep the API tests scoped to the `api/` module. The tests use `httpx.AsyncClient` against
the FastAPI app imported from the backend — the import paths will need updating to reflect
the new `api.*` package location.

**Expected Outcomes**
- `api/tests/` exists with all three test files and `__init__.py`.
- Import statements in each test file reference `api.main`, `api.models`, `api.evidence_service` (or equivalent relative imports).
- `des_review/tests/` no longer exists.

**Todo List**
1. Move `des_review/tests/__init__.py` → `api/tests/__init__.py`
2. Move `des_review/tests/test_evidence.py` → `api/tests/test_evidence.py`
3. Move `des_review/tests/test_models.py` → `api/tests/test_models.py`
4. Move `des_review/tests/test_results.py` → `api/tests/test_results.py`
5. In each test file, update any `from backend.` or `from des_review.backend.` imports to `from api.`
6. Verify tests pass: `cd api && pytest tests/`

**Relevant Context**
- `des_review/tests/test_evidence.py`, `test_models.py`, `test_results.py`
- Tests import the FastAPI `app` object and Pydantic models — import paths are the only change needed

**Status** — `[ ] pending`

---

### Sub-Task 3 — Move `des_review/test-failure-classifier/SKILL.md` → `sentinel/skill/SKILL.md`

**Intent**
The SKILL.md is the reasoning specification Bob uses when Sentinel invokes the classifier.
It belongs inside `sentinel/` because that is the component that triggers Bob and consumes
the classification output. A dedicated `skill/` subfolder keeps it discoverable without
polluting the `sentinel/` root.

**Expected Outcomes**
- `sentinel/skill/SKILL.md` exists and is byte-for-byte identical to the original.
- `des_review/test-failure-classifier/` no longer exists.
- Any reference to the skill path in `sentinel/classifier.py` or docs is updated.

**Todo List**
1. Create `sentinel/skill/` directory by moving `des_review/test-failure-classifier/SKILL.md` → `sentinel/skill/SKILL.md`
2. Search `sentinel/` for any hardcoded path referencing `test-failure-classifier` or `SKILL.md` and update it
3. Update `README.md` if it references the old skill path (currently no reference found — confirm)

**Relevant Context**
- Source: `des_review/test-failure-classifier/SKILL.md`
- `sentinel/classifier.py` — check whether it loads or references the SKILL.md path

**Status** — `[ ] pending`

---

### Sub-Task 4 — Delete the now-empty `des_review/` folder

**Intent**
After Sub-Tasks 1–3 all content has been moved out. Remove the empty shell so no trace
of the personal-name folder remains in the working tree.

**Expected Outcomes**
- `des_review/` does not exist in the repo.
- `git status` shows all moves as renames (no orphaned files).

**Todo List**
1. Confirm `des_review/` is fully empty (no files remaining)
2. Delete the `des_review/` directory
3. Stage all moves with `git mv` (or equivalent) so Git tracks them as renames, not delete + add
4. Verify with `git status` that no untracked files remain

**Relevant Context**
- Use `git mv` for each file move in Sub-Tasks 1–3 so history is preserved
- All four sub-tasks should be committed together as a single atomic restructure commit

**Status** — `[ ] pending`

---

### Sub-Task 5 — Update README and root-level documentation

**Intent**
The `README.md` Sentinel section and `sentinel-plan.md` should reflect the new paths so
new contributors aren't confused. No content changes — path references only.

**Expected Outcomes**
- `README.md` references `api/` for the REST layer and `sentinel/skill/SKILL.md` for the skill.
- `sentinel-plan.md` updated if it references any `des_review` path.

**Todo List**
1. Search `README.md` for any mention of `des_review` → update or remove
2. Search `sentinel-plan.md` for any mention of `des_review` → update or remove
3. Add a brief "Project Layout" section to `README.md` that lists `api/`, `sentinel/`, `demo/`, `scripts/`

**Relevant Context**
- `README.md` (lines 72–135) — currently no `des_review` mention found, confirm after moves
- `sentinel-plan.md` — check for path references

**Status** — `[ ] pending`
