"""Tests for classification-result, results, and review-action endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport

from api.main import app, results_store
from api.models import Classification, RecommendedAction


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

STALE_RESULT = {
    "test_name": "test_customer_discount",
    "classification": "STALE_TEST",
    "confidence": 0.92,
    "reason": "Implementation intentionally changed VIP discount from 10% to 20%. Test still asserts old value.",
    "recommended_action": "UPDATE_TEST",
    "proposed_diff": "- iEqual(90: result);\n+ iEqual(80: result);",
    "needs_human_review": False,
}

REGRESSION_RESULT = {
    "test_name": "test_discount_tier_boundary",
    "classification": "REGRESSION",
    "confidence": 0.89,
    "reason": "Off-by-one error applies a discount to sub-threshold orders. Test is correct; code is broken.",
    "recommended_action": "FIX_CODE",
    "proposed_diff": None,
    "needs_human_review": True,
}

UNCERTAIN_RESULT = {
    "test_name": "test_customer_discount_standard",
    "classification": "UNCERTAIN",
    "confidence": 0.41,
    "reason": "Rate table refactor may have changed behaviour. Cannot determine intent from diff alone.",
    "recommended_action": "ASK_HUMAN",
    "proposed_diff": None,
    "needs_human_review": True,
}


@pytest.fixture(autouse=True)
def clear_results_store():
    """Ensure results_store is empty before each test."""
    results_store.clear()
    yield
    results_store.clear()


# ---------------------------------------------------------------------------
# POST /classification-result
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_classification_result_stale():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/classification-result", json=STALE_RESULT)
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert "test_customer_discount" in results_store


@pytest.mark.asyncio
async def test_post_classification_result_regression():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/classification-result", json=REGRESSION_RESULT)
    assert resp.status_code == 200
    stored = results_store["test_discount_tier_boundary"]
    assert stored.classification == Classification.REGRESSION
    assert stored.needs_human_review is True
    assert stored.proposed_diff is None  # regressions must NOT have a proposed test fix


@pytest.mark.asyncio
async def test_post_classification_result_uncertain():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/classification-result", json=UNCERTAIN_RESULT)
    assert resp.status_code == 200
    stored = results_store["test_customer_discount_standard"]
    assert stored.classification == Classification.UNCERTAIN
    assert stored.recommended_action == RecommendedAction.ASK_HUMAN
    assert stored.needs_human_review is True


@pytest.mark.asyncio
async def test_post_classification_result_overwrites_previous():
    """Posting a second result for the same test_name replaces the first."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/classification-result", json=STALE_RESULT)
        updated = {**STALE_RESULT, "confidence": 0.75, "reason": "Updated reasoning."}
        await client.post("/classification-result", json=updated)
    assert results_store["test_customer_discount"].confidence == 0.75


@pytest.mark.asyncio
async def test_post_classification_result_invalid_confidence():
    bad = {**STALE_RESULT, "confidence": 1.5}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/classification-result", json=bad)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_post_classification_result_invalid_classification():
    bad = {**STALE_RESULT, "classification": "MAYBE"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/classification-result", json=bad)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /results
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_results_empty():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/results")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_results_returns_all():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/classification-result", json=STALE_RESULT)
        await client.post("/classification-result", json=REGRESSION_RESULT)
        resp = await client.get("/results")
    assert resp.status_code == 200
    names = {r["test_name"] for r in resp.json()}
    assert names == {"test_customer_discount", "test_discount_tier_boundary"}


# ---------------------------------------------------------------------------
# GET /results/{test_name}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_result_by_name():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/classification-result", json=STALE_RESULT)
        resp = await client.get("/results/test_customer_discount")
    assert resp.status_code == 200
    body = resp.json()
    assert body["classification"] == "STALE_TEST"
    assert body["confidence"] == 0.92


@pytest.mark.asyncio
async def test_get_result_by_name_not_found():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/results/nonexistent_test")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /review-action
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_review_action_accept():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/review-action", json={
            "test_name": "test_customer_discount",
            "action": "ACCEPT",
        })
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_review_action_reject():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/review-action", json={
            "test_name": "test_customer_discount",
            "action": "REJECT",
        })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_review_action_flag():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/review-action", json={
            "test_name": "test_customer_discount",
            "action": "FLAG",
        })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_review_action_invalid():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/review-action", json={
            "test_name": "test_customer_discount",
            "action": "APPROVE",  # not a valid ReviewAction
        })
    assert resp.status_code == 422
