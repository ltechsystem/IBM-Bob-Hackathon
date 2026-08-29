"""Evidence service — loads structured evidence for Bob to reason over.

In fixture/demo mode (demo_case is set), returns a deterministic JSON payload
from backend/demo_cases/. In live mode (demo_case is None), this is where
diff_service and test_runner would be called — not yet implemented.
"""

import json
from pathlib import Path

from fastapi import HTTPException

from backend.models import EvidencePayload, EvidenceRequest

DEMO_CASES_DIR = Path(__file__).parent / "demo_cases"
VALID_DEMO_CASES = {"stale_test", "regression", "uncertain"}


def get_evidence(req: EvidenceRequest) -> EvidencePayload:
    if req.demo_case is not None:
        return _load_fixture(req.demo_case)

    # Live mode placeholder — will be wired to diff_service + test_runner later.
    raise HTTPException(
        status_code=501,
        detail="Live evidence gathering not yet implemented. Pass demo_case=stale_test|regression|uncertain.",
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
