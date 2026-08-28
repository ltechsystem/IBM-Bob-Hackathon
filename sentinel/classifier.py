"""
sentinel/classifier.py — Bob classifier for test failures.

Invokes Bob Shell non-interactively (bob -p "...") to classify each
TestFailure as STALE, REGRESSION, NEW_COVERAGE_NEEDED, or UNCERTAIN.

This is the right integration point: Bob is the reasoning engine, as
described in the project pitch.  We pass Bob the change diff, the
failing test, the last-passing test, and the assertion output, and ask
it to classify with a confidence score.

How it works
------------
Bob Shell is invoked as a subprocess:

    bob --auth-method api-key -p "<prompt>"

Authentication uses the BOBSHELL_API_KEY env var (Inference-scoped key
from the Bob web portal).

Response format expected from Bob
----------------------------------
VERDICT: <STALE|REGRESSION|NEW_COVERAGE_NEEDED>
CONFIDENCE: <0.0-1.0>
RATIONALE: <text>
PROPOSED_PATCH:
<unified diff or empty>

Stub mode
---------
Set SENTINEL_BOB_STUB=true to skip the Bob call entirely and return a
hardcoded Classification.  Control the stub verdict via:
    SENTINEL_BOB_STUB_VERDICT = stale | regression | new_coverage | uncertain
"""

from __future__ import annotations

import os
import re
import subprocess
import warnings
from pathlib import Path

from sentinel.models import Classification, TestFailure

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_PROMPT_TEMPLATE = (Path(__file__).parent / "prompts" / "classify.txt").read_text(encoding="utf-8")


def _confidence_threshold() -> float:
    return float(os.environ.get("SENTINEL_CONFIDENCE_THRESHOLD", "0.75"))


def _is_stub() -> bool:
    return os.environ.get("SENTINEL_BOB_STUB", "false").strip().lower() in ("1", "true", "yes")


# ---------------------------------------------------------------------------
# Stub classifications (demo scenarios)
# ---------------------------------------------------------------------------

_STUB_STALE = Classification(
    verdict="STALE",
    confidence=0.92,
    rationale=(
        "The rounding rule changed from 2 decimal places to 1 decimal place. "
        "The test still asserts the old value 9.99 — it needs updating to 10.0."
    ),
    proposed_patch="""\
--- ORDCALCT (previous)
+++ ORDCALCT (proposed)
@@ -12,7 +12,7 @@
 dcl-proc test_rounding;
   dcl-s result packed(11:2);
   result = calcTotal(3: 3.33: 0);
-  iEqual(9.99: result);
+  iEqual(10.0: result);
 end-proc;
""",
)

_STUB_REGRESSION = Classification(
    verdict="REGRESSION",
    confidence=0.95,
    rationale=(
        "The basic calculation test expects 50.00 but the change introduced "
        "an off-by-one error that produces 49.00. This is a genuine bug — "
        "fix the source code, not the test."
    ),
    proposed_patch="",
)

_STUB_NEW_COVERAGE = Classification(
    verdict="NEW_COVERAGE_NEEDED",
    confidence=0.88,
    rationale=(
        "A new premium discount branch (disc > 20) was added with no "
        "corresponding test procedure. A new test should be written."
    ),
    proposed_patch="""\
--- ORDCALCT (previous)
+++ ORDCALCT (proposed)
@@ -20,3 +20,10 @@
 dcl-proc test_rounding;
   dcl-s result packed(11:2);
   result = calcTotal(3: 3.33: 0);
   iEqual(9.99: result);
 end-proc;
+
+dcl-proc test_premiumDiscount;
+  dcl-s result packed(11:2);
+  result = calcTotal(10: 5.00: 25);
+  iEqual(37.50: result);
+end-proc;
""",
)

_STUB_UNCERTAIN = Classification(
    verdict="UNCERTAIN",
    confidence=0.45,
    rationale=(
        "The change modified both the rounding logic and the discount tier "
        "simultaneously. It is unclear whether the test failure reflects "
        "stale assertions or a genuine regression — human review needed."
    ),
    proposed_patch="",
)

_STUB_MAP = {
    "stale":        _STUB_STALE,
    "regression":   _STUB_REGRESSION,
    "new_coverage": _STUB_NEW_COVERAGE,
    "uncertain":    _STUB_UNCERTAIN,
}


def _stub_classification() -> Classification:
    key = os.environ.get("SENTINEL_BOB_STUB_VERDICT", "stale").lower()
    return _STUB_MAP.get(key, _STUB_STALE)


# ---------------------------------------------------------------------------
# Response parser
# ---------------------------------------------------------------------------

_VERDICT_RE    = re.compile(r"^VERDICT:\s*(.+)$", re.MULTILINE)
_CONFIDENCE_RE = re.compile(r"^CONFIDENCE:\s*([0-9.]+)$", re.MULTILINE)
_RATIONALE_RE  = re.compile(r"^RATIONALE:\s*(.+)$", re.MULTILINE)
_PATCH_RE      = re.compile(r"^PROPOSED_PATCH:\s*\n(.*)", re.MULTILINE | re.DOTALL)


def _parse_response(text: str, threshold: float) -> Classification:
    """
    Parse Bob's structured response into a Classification.

    If any required field is missing or unparseable, returns UNCERTAIN
    with a warning rather than crashing — matches the design principle
    that the tool should be honest about its limits.
    """
    verdict_m    = _VERDICT_RE.search(text)
    confidence_m = _CONFIDENCE_RE.search(text)
    rationale_m  = _RATIONALE_RE.search(text)
    patch_m      = _PATCH_RE.search(text)

    if not verdict_m or not confidence_m or not rationale_m:
        warnings.warn(
            "Bob response did not match expected format — returning UNCERTAIN.\n"
            f"Raw response:\n{text[:500]}"
        )
        return Classification(
            verdict="UNCERTAIN",
            confidence=0.0,
            rationale="Bob's response could not be parsed. Review manually.",
        )

    verdict   = verdict_m.group(1).strip().upper()
    rationale = rationale_m.group(1).strip()
    patch     = patch_m.group(1).strip() if patch_m else ""

    try:
        confidence = float(confidence_m.group(1).strip())
    except ValueError:
        confidence = 0.0

    # Validate verdict value
    valid_verdicts = {"STALE", "REGRESSION", "NEW_COVERAGE_NEEDED"}
    if verdict not in valid_verdicts:
        verdict = "UNCERTAIN"
        confidence = 0.0

    # Confidence gate — below threshold, surface both interpretations to developer
    if confidence < threshold:
        return Classification(
            verdict="UNCERTAIN",
            confidence=confidence,
            rationale=(
                f"{rationale}\n\n"
                f"(Confidence {confidence:.0%} is below the {threshold:.0%} threshold — "
                "human classification required.)"
            ),
            proposed_patch="",
        )

    return Classification(
        verdict=verdict,
        confidence=confidence,
        rationale=rationale,
        proposed_patch=patch if verdict != "REGRESSION" else "",
    )


# ---------------------------------------------------------------------------
# Bob Shell invocation
# ---------------------------------------------------------------------------

def _call_bob(prompt: str) -> str:
    """
    Invoke Bob Shell non-interactively and return its text response.

    The prompt is written to a temp file and piped to Bob Shell:
        cat <tmp> | bob --auth-method api-key --chat-mode rpg-test-classifier
                        --approval-mode auto_edit --hide-intermediary-output

    Why temp file + pipe instead of -p "...":
    - Bob docs recommend piping for multi-line prompts
    - Avoids OS argument-length limits and shell quoting edge cases
    - Matches: cat prompt.txt | bob

    The custom mode 'rpg-test-classifier' (defined in .bob/custom_modes.yaml)
    carries the roleDefinition and customInstructions so the prompt itself
    only needs to supply the variable context.

    Auth: BOBSHELL_API_KEY environment variable (Inference-scoped key
          from the Bob web portal at bob.ibm.com).

    Raises:
        EnvironmentError: if BOBSHELL_API_KEY is not set.
        RuntimeError: if the bob subprocess exits with a non-zero code.
    """
    import tempfile

    api_key = os.environ.get("BOBSHELL_API_KEY", "")
    if not api_key:
        raise EnvironmentError(
            "BOBSHELL_API_KEY is not set. "
            "Create an Inference-scoped API key at bob.ibm.com and set it, "
            "or set SENTINEL_BOB_STUB=true to skip the real Bob call."
        )

    env = {**os.environ, "BOBSHELL_API_KEY": api_key}

    # Write prompt to a temp file — Bob docs recommend piping for multi-line prompts
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(prompt)
        tmp_path = f.name

    try:
        with open(tmp_path, "r", encoding="utf-8") as prompt_file:
            result = subprocess.run(
                [
                    "bob",
                    "--auth-method", "api-key",
                    "--chat-mode", "rpg-test-classifier",   # custom mode from .bob/custom_modes.yaml
                    "--approval-mode", "auto_edit",          # no interactive tool approvals
                    "--hide-intermediary-output",            # only emit final answer, not tool calls
                ],
                stdin=prompt_file,
                capture_output=True,
                text=True,
                env=env,
                timeout=120,  # 2 min max — flag Bob latency as demo risk if exceeded
            )
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    if result.returncode != 0:
        raise RuntimeError(
            f"Bob Shell exited with code {result.returncode}.\n"
            f"stderr: {result.stderr[:500]}"
        )

    return result.stdout


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify(
    diff: str,
    failure: TestFailure,
    last_good_test: str,
) -> Classification:
    """
    Ask Bob to classify a test failure as STALE, REGRESSION,
    NEW_COVERAGE_NEEDED, or UNCERTAIN.

    Bob receives:
      - The unified diff of the source change
      - The current failing test source
      - The last-passing test snapshot
      - The assertion failure output (procedure, assertion, expected, actual)

    Args:
        diff:           Unified diff of the source change (from diff_member).
        failure:        The TestFailure to classify.
        last_good_test: Source text of the test suite before changes
                        (loaded from the snapshot store).

    Returns:
        A Classification with verdict, confidence, rationale, and an
        optional proposed_patch diff.
    """
    if _is_stub():
        return _stub_classification()

    threshold = _confidence_threshold()

    prompt = _PROMPT_TEMPLATE.format(
        diff=diff or "(no diff — new member)",
        failing_test=failure.raw_output,
        last_good_test=last_good_test or "(no previous snapshot)",
        assertion_output=(
            f"Procedure : {failure.procedure}\n"
            f"Assertion : {failure.assertion}\n"
            f"Expected  : {failure.expected}\n"
            f"Actual    : {failure.actual}"
        ),
    )

    raw_response = _call_bob(prompt)
    return _parse_response(raw_response, threshold)
