"""
sentinel/models.py — Shared data models used across Sentinel modules.

Keeping dataclasses here prevents circular imports between runner, parser,
classifier, and proposals modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# RPGUnit test failure
# ---------------------------------------------------------------------------

@dataclass
class TestFailure:
    """
    A single RPGUnit test procedure that failed.

    Populated by sentinel/parser.py after running the test suite.
    """

    # Name of the test service program, e.g. "ORDCALCT"
    test_svcpgm: str

    # Name of the test procedure that failed, e.g. "test_rounding"
    procedure: str

    # Human-readable assertion description, e.g. "iEqual"
    assertion: str

    # Expected value as a string
    expected: str

    # Actual value as a string
    actual: str

    # Full raw output line(s) from RPGUnit for this failure
    raw_output: str

    @property
    def summary(self) -> str:
        return (
            f"{self.test_svcpgm}::{self.procedure} — "
            f"{self.assertion}  expected={self.expected!r}  actual={self.actual!r}"
        )


# ---------------------------------------------------------------------------
# Bob classification result
# ---------------------------------------------------------------------------

@dataclass
class Classification:
    """
    The result of asking Bob to classify a TestFailure.

    Populated by sentinel/classifier.py.
    """

    # One of: STALE | REGRESSION | NEW_COVERAGE_NEEDED | UNCERTAIN
    verdict: str

    # 0.0 – 1.0 confidence score returned by the model
    confidence: float

    # Plain-language rationale from the model
    rationale: str

    # Unified diff of the proposed test repair (empty for REGRESSION/UNCERTAIN)
    proposed_patch: str = ""

    @property
    def is_actionable(self) -> bool:
        """True when the verdict is not UNCERTAIN and a patch is available."""
        return self.verdict in ("STALE", "NEW_COVERAGE_NEEDED") and bool(self.proposed_patch)


# ---------------------------------------------------------------------------
# Coverage snapshot
# ---------------------------------------------------------------------------

@dataclass
class CoverageReport:
    """
    Procedure-level coverage figures for a service program.

    Populated by sentinel/coverage.py.
    """

    svcpgm: str
    procedures_total: int
    procedures_covered: int

    @property
    def pct(self) -> float:
        if self.procedures_total == 0:
            return 0.0
        return round(100.0 * self.procedures_covered / self.procedures_total, 1)

    def delta_str(self, other: "CoverageReport") -> str:
        """Return a '+X.X%' or '-X.X%' string vs another report."""
        diff = self.pct - other.pct
        sign = "+" if diff >= 0 else ""
        return f"{sign}{diff:.1f}%"
