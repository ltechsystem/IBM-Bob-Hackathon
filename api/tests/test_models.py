"""Tests for Pydantic models — validates schema and enum constraints."""

import pytest
from pydantic import ValidationError

from api.models import (
    Classification,
    RecommendedAction,
    ReviewAction,
    EvidenceRequest,
    EvidencePayload,
    ClassificationResult,
    ReviewActionRequest,
)


# ---------------------------------------------------------------------------
# Enum completeness
# ---------------------------------------------------------------------------

def test_classification_values():
    assert set(Classification) == {
        Classification.STALE_TEST,
        Classification.REGRESSION,
        Classification.UNCERTAIN,
    }


def test_recommended_action_values():
    assert set(RecommendedAction) == {
        RecommendedAction.UPDATE_TEST,
        RecommendedAction.FIX_CODE,
        RecommendedAction.ASK_HUMAN,
        RecommendedAction.ADD_TEST,
        RecommendedAction.NO_ACTION,
    }


def test_review_action_values():
    assert set(ReviewAction) == {
        ReviewAction.ACCEPT,
        ReviewAction.REJECT,
        ReviewAction.FLAG,
    }


# ---------------------------------------------------------------------------
# EvidenceRequest
# ---------------------------------------------------------------------------

def test_evidence_request_minimal():
    req = EvidenceRequest(file="CUSTOMER.RPGLE", test_name="test_customer_discount")
    assert req.demo_case is None


def test_evidence_request_with_demo_case():
    req = EvidenceRequest(file="CUSTOMER.RPGLE", test_name="test_customer_discount", demo_case="stale_test")
    assert req.demo_case == "stale_test"


def test_evidence_request_missing_required():
    with pytest.raises(ValidationError):
        EvidenceRequest(test_name="test_customer_discount")  # missing file

    with pytest.raises(ValidationError):
        EvidenceRequest(file="CUSTOMER.RPGLE")  # missing test_name


# ---------------------------------------------------------------------------
# ClassificationResult
# ---------------------------------------------------------------------------

def test_classification_result_valid():
    result = ClassificationResult(
        test_name="test_customer_discount",
        classification=Classification.STALE_TEST,
        confidence=0.92,
        reason="Behavior changed intentionally.",
        recommended_action=RecommendedAction.UPDATE_TEST,
        proposed_diff="- assert discount = 10\n+ assert discount = 20",
        needs_human_review=False,
    )
    assert result.classification == Classification.STALE_TEST
    assert result.needs_human_review is False


def test_classification_result_confidence_bounds():
    with pytest.raises(ValidationError):
        ClassificationResult(
            test_name="t",
            classification=Classification.REGRESSION,
            confidence=1.5,  # out of range
            reason="x",
            recommended_action=RecommendedAction.FIX_CODE,
        )

    with pytest.raises(ValidationError):
        ClassificationResult(
            test_name="t",
            classification=Classification.REGRESSION,
            confidence=-0.1,  # out of range
            reason="x",
            recommended_action=RecommendedAction.FIX_CODE,
        )


def test_classification_result_regression_valid():
    # REGRESSION: FIX_CODE + needs_human_review=True + no proposed_diff — the only valid shape
    result = ClassificationResult(
        test_name="test_customer_discount",
        classification=Classification.REGRESSION,
        confidence=0.89,
        reason="Off-by-one error.",
        recommended_action=RecommendedAction.FIX_CODE,
        needs_human_review=True,
    )
    assert result.proposed_diff is None
    assert result.needs_human_review is True


def test_classification_result_uncertain():
    result = ClassificationResult(
        test_name="test_customer_discount",
        classification=Classification.UNCERTAIN,
        confidence=0.41,
        reason="Insufficient evidence.",
        recommended_action=RecommendedAction.ASK_HUMAN,
        needs_human_review=True,
    )
    assert result.needs_human_review is True


def test_classification_result_missing_required():
    with pytest.raises(ValidationError):
        ClassificationResult(
            classification=Classification.STALE_TEST,
            confidence=0.9,
            reason="x",
            recommended_action=RecommendedAction.UPDATE_TEST,
        )  # missing test_name


# ---------------------------------------------------------------------------
# ReviewActionRequest
# ---------------------------------------------------------------------------

def test_review_action_request_valid():
    req = ReviewActionRequest(test_name="test_customer_discount", action=ReviewAction.ACCEPT)
    assert req.action == ReviewAction.ACCEPT


def test_review_action_request_invalid_action():
    with pytest.raises(ValidationError):
        ReviewActionRequest(test_name="test_customer_discount", action="APPROVE")  # not a valid enum value


# ---------------------------------------------------------------------------
# EvidencePayload bounds
# ---------------------------------------------------------------------------

def test_evidence_payload_coverage_bounds():
    with pytest.raises(ValidationError):
        EvidencePayload(file="F.RPGLE", test_name="t", coverage_before=101.0)
    with pytest.raises(ValidationError):
        EvidencePayload(file="F.RPGLE", test_name="t", coverage_before=-1.0)


def test_evidence_payload_tests_passing_negative():
    with pytest.raises(ValidationError):
        EvidencePayload(file="F.RPGLE", test_name="t", tests_passing=-1)


def test_evidence_payload_tests_failing_negative():
    with pytest.raises(ValidationError):
        EvidencePayload(file="F.RPGLE", test_name="t", tests_failing=-1)


def test_evidence_payload_valid_bounds():
    payload = EvidencePayload(
        file="CUSTOMER.RPGLE",
        test_name="test_t",
        coverage_before=0.0,
        tests_passing=0,
        tests_failing=0,
    )
    assert payload.coverage_before == 0.0


# ---------------------------------------------------------------------------
# ClassificationResult — REGRESSION invariants
# ---------------------------------------------------------------------------

def test_regression_rejects_update_test_action():
    with pytest.raises(ValidationError, match="UPDATE_TEST"):
        ClassificationResult(
            test_name="t",
            classification=Classification.REGRESSION,
            confidence=0.89,
            reason="x",
            recommended_action=RecommendedAction.UPDATE_TEST,  # forbidden
            needs_human_review=True,
        )


def test_regression_rejects_proposed_diff():
    with pytest.raises(ValidationError, match="proposed_diff"):
        ClassificationResult(
            test_name="t",
            classification=Classification.REGRESSION,
            confidence=0.89,
            reason="x",
            recommended_action=RecommendedAction.FIX_CODE,
            proposed_diff="- iEqual(0: result);\n+ iEqual(2: result);",  # forbidden
            needs_human_review=True,
        )


def test_regression_requires_human_review():
    with pytest.raises(ValidationError, match="needs_human_review"):
        ClassificationResult(
            test_name="t",
            classification=Classification.REGRESSION,
            confidence=0.89,
            reason="x",
            recommended_action=RecommendedAction.FIX_CODE,
            needs_human_review=False,  # forbidden
        )


# ---------------------------------------------------------------------------
# ClassificationResult — UNCERTAIN invariants
# ---------------------------------------------------------------------------

def test_uncertain_requires_ask_human_action():
    with pytest.raises(ValidationError, match="ASK_HUMAN"):
        ClassificationResult(
            test_name="t",
            classification=Classification.UNCERTAIN,
            confidence=0.41,
            reason="x",
            recommended_action=RecommendedAction.FIX_CODE,  # forbidden
            needs_human_review=True,
        )


def test_uncertain_rejects_proposed_diff():
    with pytest.raises(ValidationError, match="proposed_diff"):
        ClassificationResult(
            test_name="t",
            classification=Classification.UNCERTAIN,
            confidence=0.41,
            reason="x",
            recommended_action=RecommendedAction.ASK_HUMAN,
            proposed_diff="some diff",  # forbidden
            needs_human_review=True,
        )


def test_uncertain_requires_human_review():
    with pytest.raises(ValidationError, match="needs_human_review"):
        ClassificationResult(
            test_name="t",
            classification=Classification.UNCERTAIN,
            confidence=0.41,
            reason="x",
            recommended_action=RecommendedAction.ASK_HUMAN,
            needs_human_review=False,  # forbidden
        )


# ---------------------------------------------------------------------------
# ClassificationResult — low-confidence invariant
# ---------------------------------------------------------------------------

def test_low_confidence_requires_human_review():
    with pytest.raises(ValidationError, match="0.60"):
        ClassificationResult(
            test_name="t",
            classification=Classification.STALE_TEST,
            confidence=0.59,
            reason="x",
            recommended_action=RecommendedAction.UPDATE_TEST,
            needs_human_review=False,  # forbidden when confidence < 0.6
        )


def test_confidence_exactly_at_threshold_requires_human_review():
    # 0.59 is below 0.60 — must fail
    with pytest.raises(ValidationError):
        ClassificationResult(
            test_name="t",
            classification=Classification.STALE_TEST,
            confidence=0.599,
            reason="x",
            recommended_action=RecommendedAction.UPDATE_TEST,
            needs_human_review=False,
        )


def test_confidence_at_threshold_with_review_flag_passes():
    # Low confidence is allowed if needs_human_review=True
    result = ClassificationResult(
        test_name="t",
        classification=Classification.STALE_TEST,
        confidence=0.55,
        reason="Low confidence stale test.",
        recommended_action=RecommendedAction.UPDATE_TEST,
        needs_human_review=True,  # correctly flagged
    )
    assert result.needs_human_review is True


# ---------------------------------------------------------------------------
# ClassificationResult — proposed_diff gate
# ---------------------------------------------------------------------------

def test_proposed_diff_allowed_only_for_stale_update_test():
    # Valid: STALE_TEST + UPDATE_TEST
    result = ClassificationResult(
        test_name="t",
        classification=Classification.STALE_TEST,
        confidence=0.92,
        reason="x",
        recommended_action=RecommendedAction.UPDATE_TEST,
        proposed_diff="- old\n+ new",
        needs_human_review=False,
    )
    assert result.proposed_diff is not None


def test_proposed_diff_rejected_for_stale_with_non_update_action():
    # STALE_TEST but action is ADD_TEST — proposed_diff still forbidden
    with pytest.raises(ValidationError, match="proposed_diff"):
        ClassificationResult(
            test_name="t",
            classification=Classification.STALE_TEST,
            confidence=0.92,
            reason="x",
            recommended_action=RecommendedAction.ADD_TEST,
            proposed_diff="- old\n+ new",  # forbidden: action is not UPDATE_TEST
            needs_human_review=False,
        )


# ---------------------------------------------------------------------------
# ClassificationResult — multiple violations reported together
# ---------------------------------------------------------------------------

def test_multiple_violations_reported_together():
    # REGRESSION + UPDATE_TEST + proposed_diff + needs_human_review=False
    # All four rules fire; error message should mention all of them
    with pytest.raises(ValidationError) as exc_info:
        ClassificationResult(
            test_name="t",
            classification=Classification.REGRESSION,
            confidence=0.89,
            reason="x",
            recommended_action=RecommendedAction.UPDATE_TEST,
            proposed_diff="some diff",
            needs_human_review=False,
        )
    msg = str(exc_info.value)
    assert "UPDATE_TEST" in msg
    assert "proposed_diff" in msg
    assert "needs_human_review" in msg
