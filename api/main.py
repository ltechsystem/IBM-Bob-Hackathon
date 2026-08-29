import logging
from typing import Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.models import (
    ClassificationResult,
    EvidencePayload,
    EvidenceRequest,
    ReviewActionRequest,
)
from api.evidence_service import get_evidence

logger = logging.getLogger(__name__)

app = FastAPI(
    title="RPG Test Maintenance API",
    description=(
        "Evidence broker and result store for the Continuous Test Maintenance loop. "
        "Bob is the classification reasoning engine."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory state (no database required for POC)
# ---------------------------------------------------------------------------

# Keyed by test_name; last classification wins.
results_store: Dict[str, ClassificationResult] = {}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /evidence
# Bob calls this to retrieve structured evidence before classifying.
# ---------------------------------------------------------------------------

@app.post("/evidence", response_model=EvidencePayload, tags=["evidence"])
def evidence(req: EvidenceRequest) -> EvidencePayload:
    """
    Return structured evidence for the given file + test.

    Pass `demo_case=stale_test|regression|uncertain` to get a deterministic
    fixture response. Omit `demo_case` for live mode (not yet implemented).
    """
    return get_evidence(req)


# ---------------------------------------------------------------------------
# POST /classification-result
# Bob calls this after reasoning to submit the structured classification.
# ---------------------------------------------------------------------------

@app.post("/classification-result", tags=["classification"])
def classification_result(result: ClassificationResult):
    """
    Accept Bob's classification and store it for the React UI to display.
    Keyed by test_name — posting again for the same test overwrites the prior result.
    """
    results_store[result.test_name] = result
    logger.info(
        "Classification stored: test=%s classification=%s confidence=%.2f",
        result.test_name,
        result.classification,
        result.confidence,
    )
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# GET /results  +  GET /results/{test_name}
# React UI calls these to display classification results.
# ---------------------------------------------------------------------------

@app.get("/results", response_model=List[ClassificationResult], tags=["results"])
def list_results() -> List[ClassificationResult]:
    """Return all stored classification results since server start."""
    return list(results_store.values())


@app.get("/results/{test_name}", response_model=ClassificationResult, tags=["results"])
def get_result(test_name: str) -> ClassificationResult:
    """Return a single classification result by test name, or 404 if not found."""
    if test_name not in results_store:
        raise HTTPException(status_code=404, detail=f"No result found for test '{test_name}'")
    return results_store[test_name]


# ---------------------------------------------------------------------------
# POST /review-action
# Developer signals Accept / Reject / Flag from the React UI.
# ---------------------------------------------------------------------------

@app.post("/review-action", tags=["review"])
def review_action(req: ReviewActionRequest):
    """
    Record the developer's decision on a classification result.
    Stub implementation — logs the action. Persistent storage can be added later.
    """
    logger.info(
        "Review action received: test=%s action=%s",
        req.test_name,
        req.action,
    )
    return {"status": "ok"}
