"""
sentinel/runner.py — RPGUnit test runner invocation.

Invokes the RPGUnit test suite for a given service program on IBM i and
returns the raw output text for parsing by sentinel/parser.py.

RPGUnit CL command
------------------
We use RUCALLTST (Run Unit Tests), which is the standard RPGUnit command:

    RUCALLTST TSTPGM(<lib>/<svcpgm>)
              TSTPRC(*ALL)
              OUTPUT(*ALLWAYS)
              DETAIL(*BASIC)

Output format
-------------
We request plain-text output (OUTPUT(*ALLWAYS) DETAIL(*BASIC)).  This
produces a spool file with lines like:

    Test procedure . . : TEST_ROUNDING
    Assertion  . . . . : iEqual
    Expected . . . . . : 9.99
    Actual . . . . . . : 10.00
    Error message  . . : Values are not equal.

    Test summary:
      Tests run  . . . : 3
      Failures . . . . : 1

We capture this via the QTEMP spooled file approach:
    RUCALLTST ... OUTPUT(*OUTFILE) OUTFILE(QTEMP/RURESULT)
    CPYTOIMPF FROMFILE(QTEMP/RURESULT) TOSTMF('/tmp/sentinel_ru.txt')

In stub mode (IBMI_STUB=true) we return a hard-coded RPGUnit output
string with configurable failure/pass scenarios.

Naming convention
-----------------
Given source member ORDCALC, the test suite member is ORDCALCT.
This is controlled by the SENTINEL_TEST_SUFFIX env var (default: T).
"""

from __future__ import annotations

import os

from sentinel.ibmi import run_cl


# ---------------------------------------------------------------------------
# Naming convention
# ---------------------------------------------------------------------------

def test_suite_name(mbr: str) -> str:
    """
    Return the test suite member name for a given source member.

    Uses the SENTINEL_TEST_SUFFIX env var (default 'T').
    IBM i member names are max 10 characters — truncates if needed.

    Examples:
        ORDCALC  -> ORDCALCT
        LONGNAME -> LONGNAMET   (10 chars, fine)
        VERYLONGNAME -> VERYLONG (truncated to 8) + T = VERYLONGT
    """
    suffix = os.environ.get("SENTINEL_TEST_SUFFIX", "T").upper()
    base = mbr.upper()
    max_len = 10 - len(suffix)
    return base[:max_len] + suffix


# ---------------------------------------------------------------------------
# Stub output
# ---------------------------------------------------------------------------

def _is_stub() -> bool:
    return os.environ.get("IBMI_STUB", "false").strip().lower() in ("1", "true", "yes")


# Realistic RPGUnit plain-text output used in stub mode.
# Includes one failure (test_rounding) and two passes so the classifier
# has something meaningful to work with.
_STUB_OUTPUT_ONE_FAILURE = """\
Running test suite: ORDCALCT
-------------------------------
Test procedure . . : TEST_BASICALC
Status . . . . . . : *SUCCESS

Test procedure . . : TEST_DISCOUNTAPPLIED
Status . . . . . . : *SUCCESS

Test procedure . . : TEST_ROUNDING
Status . . . . . . : *FAILURE
Assertion  . . . . : iEqual
Expected . . . . . : 9.99
Actual . . . . . . : 10.00
Error message  . . : Values are not equal.

-------------------------------
Test summary:
  Tests run  . . . : 3
  Failures . . . . : 1
  Errors . . . . . : 0
"""

_STUB_OUTPUT_ALL_PASS = """\
Running test suite: ORDCALCT
-------------------------------
Test procedure . . : TEST_BASICALC
Status . . . . . . : *SUCCESS

Test procedure . . : TEST_DISCOUNTAPPLIED
Status . . . . . . : *SUCCESS

Test procedure . . : TEST_ROUNDING
Status . . . . . . : *SUCCESS

-------------------------------
Test summary:
  Tests run  . . . : 3
  Failures . . . . : 0
  Errors . . . . . : 0
"""

_STUB_OUTPUT_REGRESSION = """\
Running test suite: ORDCALCT
-------------------------------
Test procedure . . : TEST_BASICALC
Status . . . . . . : *FAILURE
Assertion  . . . . : iEqual
Expected . . . . . : 50.00
Actual . . . . . . : 49.00
Error message  . . : Values are not equal.

Test procedure . . : TEST_DISCOUNTAPPLIED
Status . . . . . . : *SUCCESS

Test procedure . . : TEST_ROUNDING
Status . . . . . . : *SUCCESS

-------------------------------
Test summary:
  Tests run  . . . : 3
  Failures . . . . : 1
  Errors . . . . . : 0
"""

# Map scenario name -> output string for stub mode
_STUB_SCENARIOS: dict[str, str] = {
    "one_failure":  _STUB_OUTPUT_ONE_FAILURE,
    "all_pass":     _STUB_OUTPUT_ALL_PASS,
    "regression":   _STUB_OUTPUT_REGRESSION,
}


def _stub_output() -> str:
    """Return stub output based on SENTINEL_STUB_SCENARIO env var."""
    scenario = os.environ.get("SENTINEL_STUB_SCENARIO", "one_failure")
    return _STUB_SCENARIOS.get(scenario, _STUB_OUTPUT_ONE_FAILURE)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_tests(lib: str, test_svcpgm: str) -> str:
    """
    Run an RPGUnit test suite and return the raw output text.

    In real mode: invokes RUCALLTST on IBM i, captures the spool output
    via QSH and returns it as a string.

    In stub mode: returns a hard-coded output string controlled by
    SENTINEL_STUB_SCENARIO (one_failure | all_pass | regression).

    Args:
        lib:          Library containing the test service program
        test_svcpgm:  Test service program name, e.g. "ORDCALCT"

    Returns:
        Raw RPGUnit output text.
    """
    if _is_stub():
        return _stub_output()

    # Real IBM i path:
    # 1. Run RUCALLTST, writing results to a stream file in /tmp
    # 2. Cat the stream file back
    tmp_path = f"/tmp/sentinel_ru_{test_svcpgm.lower()}.txt"

    run_cl(
        f"RUCALLTST TSTPGM({lib}/{test_svcpgm}) "
        f"TSTPRC(*ALL) "
        f"OUTPUT(*ALLWAYS) "
        f"DETAIL(*BASIC) "
        f"RPTTYPE(*TEXT) "
        f"RPTSTMF('{tmp_path}')"
    )

    raw = run_cl(f"QSH CMD('cat {tmp_path}')")
    return raw
