import asyncio
import json
import logging
from typing import AsyncIterator, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from api.models import (
    ClassificationResult,
    EvidencePayload,
    EvidenceRequest,
    ReviewActionRequest,
    SentinelEvent,
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
    expose_headers=["Content-Type"],
)

# ---------------------------------------------------------------------------
# In-memory state (no database required for POC)
# ---------------------------------------------------------------------------

# Keyed by test_name; last classification wins.
results_store: Dict[str, ClassificationResult] = {}

# Ordered list of sentinel watcher lifecycle events.
sentinel_events: List[SentinelEvent] = []

# SSE subscriber queues — each connected UI client gets its own queue.
_sse_subscribers: List[asyncio.Queue] = []


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


# ---------------------------------------------------------------------------
# POST /sentinel/event
# sentinel/watcher.py (and proposals.py) call this to push lifecycle events.
# ---------------------------------------------------------------------------

@app.post("/sentinel/event", tags=["sentinel"])
async def sentinel_event(event: SentinelEvent):
    """
    Accept a lifecycle event from the Sentinel watcher and broadcast it to
    all connected SSE clients.

    Called by sentinel/watcher.py at each pipeline stage:
      WATCHER_STARTED → COMPILE_DETECTED → DIFF_READY → TESTS_RUNNING →
      TESTS_PASSED|TESTS_FAILED → CLASSIFYING → CLASSIFICATION_READY →
      SNAPSHOT_UPDATED (on pass) | no snapshot update (on fail)
    """
    sentinel_events.append(event)
    logger.info("Sentinel event: %s  member=%s", event.event_type, event.member)

    # Fan-out to all SSE subscribers
    payload = event.model_dump_json()
    for q in list(_sse_subscribers):
        await q.put(payload)

    return {"status": "ok"}


# ---------------------------------------------------------------------------
# GET /sentinel/events  — full history (REST poll fallback)
# ---------------------------------------------------------------------------

@app.get("/sentinel/events", response_model=List[SentinelEvent], tags=["sentinel"])
def list_sentinel_events(member: str | None = None):
    """Return all stored sentinel lifecycle events, optionally filtered by member."""
    if member:
        return [e for e in sentinel_events if e.member.upper() == member.upper()]
    return sentinel_events


# ---------------------------------------------------------------------------
# GET /sentinel/stream  — Server-Sent Events live stream
# ---------------------------------------------------------------------------

@app.get("/sentinel/stream", tags=["sentinel"])
async def sentinel_stream():
    """
    SSE endpoint.  The React UI connects here to receive real-time sentinel
    lifecycle events without polling.

    Each event is emitted as:
        data: <JSON>\n\n
    """
    queue: asyncio.Queue = asyncio.Queue()
    _sse_subscribers.append(queue)

    async def _generate() -> AsyncIterator[str]:
        # Replay existing events so a freshly-loaded page catches up
        for event in sentinel_events:
            yield f"data: {event.model_dump_json()}\n\n"
        try:
            while True:
                payload = await queue.get()
                yield f"data: {payload}\n\n"
        finally:
            _sse_subscribers.remove(queue)

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
