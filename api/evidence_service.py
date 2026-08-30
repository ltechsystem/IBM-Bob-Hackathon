"""Evidence service — loads structured evidence for Bob to reason over.

In fixture/demo mode (demo_case is set), returns a deterministic JSON payload
from api/demo_cases/.  In live mode (demo_case is None), pulls real data from
the Sentinel snapshot store and the RPGUnit runner.
"""

import json
from pathlib import Path

from fastapi import HTTPException

from api.models import EvidencePayload, EvidenceRequest

DEMO_CASES_DIR = Path(__file__).parent / "demo_cases"
VALID_DEMO_CASES = {"stale_test", "regression", "uncertain"}


def get_evidence(req: EvidenceRequest) -> EvidencePayload:
    if req.demo_case is not None:
        return _load_fixture(req.demo_case)

    return _live_evidence(req)


def _live_evidence(req: EvidenceRequest) -> EvidencePayload:
    """
    Build an EvidencePayload from live Sentinel data.

    Requires the sentinel package to be importable (i.e. the repo root must be
    on PYTHONPATH, which is the case when running from the project root with
    ``uvicorn api.main:app``).

    The file field is treated as ``LIB/SRCPF/MBR``.  If it doesn't contain
    slashes we fall back to sensible defaults so the API stays usable from the
    demo UI even without a live IBM i connection.
    """
    try:
        from sentinel.store import load_snapshot
        from sentinel.diff import diff_member
        from sentinel.runner import run_tests, test_suite_name
        from sentinel.parser import parse_output, parse_summary
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Sentinel package not available: {exc}. "
                   "Ensure the project root is on PYTHONPATH or pass demo_case=stale_test|regression|uncertain.",
        ) from exc

    # Parse lib/srcpf/mbr from the file field (e.g. "MYLIB/QRPGLESRC/ORDCALC")
    parts = req.file.replace("\\", "/").split("/")
    if len(parts) == 3:
        lib, srcpf, mbr = parts
    else:
        raise HTTPException(
            status_code=400,
            detail=(
                "In live mode the 'file' field must be 'LIB/SRCPF/MBR', "
                f"e.g. 'MYLIB/QRPGLESRC/ORDCALC'. Got: {req.file!r}"
            ),
        )

    # Diff
    try:
        diff_result = diff_member(lib, srcpf, mbr)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Sentinel diff failed: {exc}") from exc

    # Load last-good snapshot for the test suite member
    suite = test_suite_name(mbr)
    last_good_test = load_snapshot(lib, srcpf, suite) or ""

    # Run tests and find the specific failure
    try:
        raw_output = run_tests(lib, suite)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"RPGUnit runner failed: {exc}") from exc

    summary = parse_summary(raw_output)
    failures = parse_output(raw_output, suite)

    # Find the requested test failure (or use the first one)
    failure = next(
        (f for f in failures if f.procedure.lower() == req.test_name.lower()),
        failures[0] if failures else None,
    )

    return EvidencePayload(
        file=req.file,
        procedure=failure.procedure if failure else None,
        test_name=req.test_name,
        diff=diff_result.unified_diff or None,
        last_passing_code=diff_result.previous_source,
        last_passing_test=last_good_test or None,
        test_source=raw_output,
        expected=failure.expected if failure else None,
        actual=failure.actual if failure else None,
        assertion_output=failure.raw_output if failure else None,
        tests_passing=summary["tests_run"] - summary["failures"] - summary["errors"],
        tests_failing=summary["failures"],
    )


def _load_fixture(demo_case: str) -> EvidencePayload:
    if demo_case not in VALID_DEMO_CASES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown demo_case '{demo_case}'. Valid values: {sorted(VALID_DEMO_CASES)}",
        )

    fixture_path = DEMO_CASES_DIR / f"{demo_case}.json"
    raw = json.loads(fixture_path.read_text(encoding="utf-8"))

    # Strip internal metadata keys (prefixed with _) before parsing into the model.
    data = {k: v for k, v in raw.items() if not k.startswith("_")}
    return EvidencePayload(**data)
