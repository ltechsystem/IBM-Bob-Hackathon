"""
sentinel/parser.py — RPGUnit output parser.

Parses the plain-text output produced by RUCALLTST into a list of
TestFailure dataclasses.

Expected input format (one block per failing test):

    Test procedure . . : TEST_ROUNDING
    Status . . . . . . : *FAILURE
    Assertion  . . . . : iEqual
    Expected . . . . . : 9.99
    Actual . . . . . . : 10.00
    Error message  . . : Values are not equal.

Passing tests are recorded as:

    Test procedure . . : TEST_BASICALC
    Status . . . . . . : *SUCCESS

We extract only failures.  Passing tests are counted but not returned
as TestFailure objects.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sentinel.models import TestFailure


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

# Regex to extract key: value pairs from RPGUnit output lines
# Matches lines like:  "Test procedure . . : TEST_ROUNDING"
_KV_RE = re.compile(r"^[A-Za-z ]+\.*\s*:\s*(.+)$")

# Keys we care about (normalised to lowercase, spaces removed)
_KEY_PROCEDURE  = "testprocedure"
_KEY_STATUS     = "status"
_KEY_ASSERTION  = "assertion"
_KEY_EXPECTED   = "expected"
_KEY_ACTUAL     = "actual"
_KEY_ERROR_MSG  = "errormessage"


def _normalise_key(raw: str) -> str:
    """Strip dots, spaces and lowercase a key string."""
    return re.sub(r"[\s.]+", "", raw).lower()


def _parse_kv(line: str) -> tuple[str, str] | None:
    """
    Parse a 'Key . . : Value' line.

    Returns (normalised_key, value) or None if the line doesn't match.
    """
    # Split on the first ' : ' (with surrounding spaces)
    parts = re.split(r"\s*:\s*", line, maxsplit=1)
    if len(parts) != 2:
        return None
    key_raw, value = parts
    return _normalise_key(key_raw), value.strip()


@dataclass
class _Block:
    """Accumulator for one test procedure block."""
    procedure: str = ""
    status: str = ""
    assertion: str = ""
    expected: str = ""
    actual: str = ""
    error_msg: str = ""
    raw_lines: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.raw_lines is None:
            self.raw_lines = []

    @property
    def is_failure(self) -> bool:
        return self.status.upper() == "*FAILURE"


def parse_output(raw_output: str, test_svcpgm: str) -> list[TestFailure]:
    """
    Parse RPGUnit plain-text output into a list of TestFailure objects.

    Only failed test procedures are returned.  Passing tests are silently
    ignored.

    Args:
        raw_output:   The full text output from run_tests().
        test_svcpgm:  The test service program name (used to populate
                      TestFailure.test_svcpgm).

    Returns:
        A list of TestFailure — empty if all tests passed.
    """
    failures: list[TestFailure] = []
    current: _Block | None = None

    for line in raw_output.splitlines():
        line = line.rstrip()

        kv = _parse_kv(line)
        if kv is None:
            # Not a key-value line — could be a separator or summary
            if current is not None:
                current.raw_lines.append(line)
            continue

        key, value = kv

        if key == _KEY_PROCEDURE:
            # Start of a new test block — flush previous if it was a failure
            if current is not None and current.is_failure:
                failures.append(_block_to_failure(current, test_svcpgm))
            current = _Block(procedure=value)
            current.raw_lines.append(line)

        elif current is not None:
            current.raw_lines.append(line)
            if key == _KEY_STATUS:
                current.status = value
            elif key == _KEY_ASSERTION:
                current.assertion = value
            elif key == _KEY_EXPECTED:
                current.expected = value
            elif key == _KEY_ACTUAL:
                current.actual = value
            elif key == _KEY_ERROR_MSG:
                current.error_msg = value

    # Flush final block
    if current is not None and current.is_failure:
        failures.append(_block_to_failure(current, test_svcpgm))

    return failures


def _block_to_failure(block: _Block, test_svcpgm: str) -> TestFailure:
    """Convert a parsed _Block into a TestFailure dataclass."""
    return TestFailure(
        test_svcpgm=test_svcpgm,
        procedure=block.procedure,
        assertion=block.assertion or "unknown",
        expected=block.expected,
        actual=block.actual,
        raw_output="\n".join(block.raw_lines),
    )


def parse_summary(raw_output: str) -> dict[str, int]:
    """
    Extract the test summary counts from RPGUnit output.

    Returns a dict with keys: tests_run, failures, errors.
    Returns zeros if the summary section is not found.
    """
    summary = {"tests_run": 0, "failures": 0, "errors": 0}
    in_summary = False

    for line in raw_output.splitlines():
        if "Test summary" in line:
            in_summary = True
            continue
        if not in_summary:
            continue

        kv = _parse_kv(line)
        if kv is None:
            continue
        key, value = kv
        try:
            if "testsrun" in key or "run" in key:
                summary["tests_run"] = int(value)
            elif "failure" in key:
                summary["failures"] = int(value)
            elif "error" in key:
                summary["errors"] = int(value)
        except ValueError:
            pass

    return summary
