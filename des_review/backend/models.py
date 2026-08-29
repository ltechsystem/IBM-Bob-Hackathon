from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class Classification(str, Enum):
    STALE_TEST = "STALE_TEST"
    REGRESSION = "REGRESSION"
    UNCERTAIN = "UNCERTAIN"


class RecommendedAction(str, Enum):
    UPDATE_TEST = "UPDATE_TEST"
    FIX_CODE = "FIX_CODE"
    ASK_HUMAN = "ASK_HUMAN"
    ADD_TEST = "ADD_TEST"
    NO_ACTION = "NO_ACTION"


class ReviewAction(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    FLAG = "FLAG"


# ---------------------------------------------------------------------------
# POST /evidence — request
# ---------------------------------------------------------------------------

class EvidenceRequest(BaseModel):
    file: str = Field(..., description="Source file name, e.g. CUSTOMER.RPGLE")
    test_name: str = Field(..., description="RPGUnit test procedure name, e.g. test_customer_discount")
    demo_case: Optional[str] = Field(
        None,
        description="Load a deterministic fixture: stale_test | regression | uncertain. "
                    "Omit to use live diff/runner.",
    )


# ---------------------------------------------------------------------------
# POST /evidence — response (sent to Bob for reasoning)
# ---------------------------------------------------------------------------

class EvidencePayload(BaseModel):
    file: str = Field(..., description="Source file name")
    procedure: Optional[str] = Field(None, description="Procedure/function under test")
    test_name: str = Field(..., description="RPGUnit test procedure name")

    # Change context
    diff: Optional[str] = Field(None, description="Git diff of the changed source file")
    last_passing_code: Optional[str] = Field(None, description="Source of the procedure as of the last passing test run")
    last_passing_test: Optional[str] = Field(None, description="Test source as of the last passing test run")

    # Failure context
    test_source: Optional[str] = Field(None, description="Current failing test source")
    expected: Optional[str] = Field(None, description="Value the test expected")
    actual: Optional[str] = Field(None, description="Value the implementation produced")
    assertion_output: Optional[str] = Field(None, description="Full assertion output / RPGUnit failure detail")

    # Developer intent (optional — may not be available)
    developer_intent: Optional[str] = Field(None, description="Developer-supplied description of the change intent")

    # Coverage / metrics snapshot at time of failure
    coverage_before: Optional[float] = Field(None, ge=0.0, le=100.0, description="Test coverage percentage before this change (0–100)")
    tests_passing: Optional[int] = Field(None, ge=0, description="Number of passing tests before this change")
    tests_failing: Optional[int] = Field(None, ge=0, description="Number of failing tests after this change")


# ---------------------------------------------------------------------------
# POST /classification-result — request (submitted by Bob after reasoning)
# ---------------------------------------------------------------------------

class ClassificationResult(BaseModel):
    test_name: str = Field(..., description="RPGUnit test procedure name — matches the evidence request")

    classification: Classification = Field(..., description="STALE_TEST | REGRESSION | UNCERTAIN")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Bob's confidence in the classification (0–1)")
    reason: str = Field(..., description="Concise explanation of the classification decision")
    recommended_action: RecommendedAction = Field(..., description="What should happen next")

    proposed_diff: Optional[str] = Field(
        None,
        description="Reviewable test diff proposed by Bob. "
                    "Only allowed when classification=STALE_TEST and recommended_action=UPDATE_TEST. "
                    "Must be null for REGRESSION and UNCERTAIN.",
    )
    needs_human_review: bool = Field(
        False,
        description="Must be true for REGRESSION and UNCERTAIN, and for any confidence < 0.6.",
    )

    @model_validator(mode="after")
    def enforce_safety_invariants(self) -> "ClassificationResult":
        errors: list[str] = []

        # --- REGRESSION rules ---
        if self.classification == Classification.REGRESSION:
            if self.recommended_action == RecommendedAction.UPDATE_TEST:
                errors.append(
                    "REGRESSION must not use recommended_action=UPDATE_TEST. "
                    "The test is the contract; fix the code."
                )
            if self.proposed_diff is not None:
                errors.append(
                    "REGRESSION must not include a proposed_diff. "
                    "Do not propose a test change to paper over a real regression."
                )
            if not self.needs_human_review:
                errors.append(
                    "REGRESSION requires needs_human_review=true."
                )

        # --- UNCERTAIN rules ---
        if self.classification == Classification.UNCERTAIN:
            if self.recommended_action != RecommendedAction.ASK_HUMAN:
                errors.append(
                    "UNCERTAIN requires recommended_action=ASK_HUMAN."
                )
            if self.proposed_diff is not None:
                errors.append(
                    "UNCERTAIN must not include a proposed_diff."
                )
            if not self.needs_human_review:
                errors.append(
                    "UNCERTAIN requires needs_human_review=true."
                )

        # --- Low-confidence rule ---
        if self.confidence < 0.6 and not self.needs_human_review:
            errors.append(
                f"confidence={self.confidence:.2f} is below 0.60; needs_human_review must be true."
            )

        # --- proposed_diff gate ---
        if self.proposed_diff is not None:
            if not (
                self.classification == Classification.STALE_TEST
                and self.recommended_action == RecommendedAction.UPDATE_TEST
            ):
                errors.append(
                    "proposed_diff is only allowed when classification=STALE_TEST "
                    "and recommended_action=UPDATE_TEST."
                )

        if errors:
            raise ValueError("; ".join(errors))

        return self


# ---------------------------------------------------------------------------
# POST /review-action — request (developer decision on a classification)
# ---------------------------------------------------------------------------

class ReviewActionRequest(BaseModel):
    test_name: str = Field(..., description="RPGUnit test procedure name")
    action: ReviewAction = Field(..., description="ACCEPT | REJECT | FLAG")
