"""Tests for POST /evidence — fixture loading and validation."""

import pytest
from httpx import AsyncClient, ASGITransport

from api.main import app


@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_evidence_stale_test():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/evidence", json={
            "file": "CUSTOMER.RPGLE",
            "test_name": "test_customer_discount",
            "demo_case": "stale_test",
        })
    assert resp.status_code == 200
    body = resp.json()
    assert body["file"] == "CUSTOMER.RPGLE"
    assert body["procedure"] == "calculateDiscount"
    assert body["test_name"] == "test_customer_discount"
    assert body["expected"] == "90.00"
    assert body["actual"] == "80.00"
    assert body["developer_intent"] is not None
    assert "diff" in body


@pytest.mark.asyncio
async def test_evidence_regression():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/evidence", json={
            "file": "CUSTOMER.RPGLE",
            "test_name": "test_discount_tier_boundary",
            "demo_case": "regression",
        })
    assert resp.status_code == 200
    body = resp.json()
    assert body["test_name"] == "test_discount_tier_boundary"
    assert body["expected"] == "0.00"
    assert body["actual"] == "2.50"
    assert body["developer_intent"] is None  # unintentional bug — no intent supplied


@pytest.mark.asyncio
async def test_evidence_uncertain():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/evidence", json={
            "file": "CUSTOMER.RPGLE",
            "test_name": "test_customer_discount_standard",
            "demo_case": "uncertain",
        })
    assert resp.status_code == 200
    body = resp.json()
    assert body["test_name"] == "test_customer_discount_standard"
    assert body["expected"] == "50.00"
    assert body["actual"] == "45.00"


@pytest.mark.asyncio
async def test_evidence_unknown_demo_case():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/evidence", json={
            "file": "CUSTOMER.RPGLE",
            "test_name": "test_foo",
            "demo_case": "does_not_exist",
        })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_evidence_no_demo_case_returns_501():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/evidence", json={
            "file": "CUSTOMER.RPGLE",
            "test_name": "test_foo",
        })
    assert resp.status_code == 501


@pytest.mark.asyncio
async def test_evidence_missing_required_fields():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/evidence", json={"demo_case": "stale_test"})
    assert resp.status_code == 422  # Pydantic validation error
