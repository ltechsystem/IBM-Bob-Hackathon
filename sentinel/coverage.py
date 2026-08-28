"""
sentinel/coverage.py — RPGUnit procedure-coverage reporting.

Invokes the RPGUnit coverage command for a test service program and returns
a CoverageReport with the number of procedures covered vs total.

RPGUnit coverage command
------------------------
RPGUnit v4+ ships the RUCOVERAGE command:

    RUCOVERAGE TSTPGM(<lib>/<svcpgm>)
               COVERAGETYPE(*PROCEDURE)
               OUTPUT(*OUTFILE)
               OUTFILE(QTEMP/RUCOV)

We then CPYTOIMPF or DSPF the outfile to a stream file and parse the
procedure-covered / procedure-total fields.

If the installed RPGUnit version does not support RUCOVERAGE, the command
will fail.  We catch that, emit a warning, and return a stub report so the
pipeline can continue.  The watcher marks stub reports visually.

Stub mode
---------
Set IBMI_STUB=true to skip the real coverage call entirely.  The stub
returns configurable before/after figures controlled by:

    SENTINEL_STUB_COVERAGE_BEFORE  (default "2/4")  — "covered/total"
    SENTINEL_STUB_COVERAGE_AFTER   (default "3/4")

These simulate "coverage improved by one procedure" as a result of
accepting a NEW_COVERAGE_NEEDED proposal.

Format of the RUCOVERAGE stream-file output
-------------------------------------------
Each line:  <procedure_name>;<covered_flag>
    CALCTOTAL;1
    APPLYDISCOUNT;1
    ROUNDPRICE;0
    PREMIUMDISCOUNT;0

covered_flag is 1 (covered) or 0 (not covered).
"""

from __future__ import annotations

import os
import warnings

from sentinel.ibmi import run_cl
from sentinel.models import CoverageReport


# ---------------------------------------------------------------------------
# Stub helpers
# ---------------------------------------------------------------------------

def _is_stub() -> bool:
    return os.environ.get("IBMI_STUB", "false").strip().lower() in ("1", "true", "yes")


def _parse_fraction(env_var: str, default: str) -> tuple[int, int]:
    """
    Parse a 'covered/total' string from an env var.
    Returns (covered, total).  Falls back to default on parse error.
    """
    raw = os.environ.get(env_var, default).strip()
    try:
        covered_s, total_s = raw.split("/")
        return int(covered_s.strip()), int(total_s.strip())
    except (ValueError, AttributeError):
        covered_s, total_s = default.split("/")
        return int(covered_s), int(total_s)


def _stub_before(svcpgm: str) -> CoverageReport:
    covered, total = _parse_fraction("SENTINEL_STUB_COVERAGE_BEFORE", "2/4")
    return CoverageReport(svcpgm=svcpgm, procedures_total=total, procedures_covered=covered)


def _stub_after(svcpgm: str) -> CoverageReport:
    covered, total = _parse_fraction("SENTINEL_STUB_COVERAGE_AFTER", "3/4")
    return CoverageReport(svcpgm=svcpgm, procedures_total=total, procedures_covered=covered)


# ---------------------------------------------------------------------------
# Real coverage parsing
# ---------------------------------------------------------------------------

def _parse_coverage_output(text: str, svcpgm: str) -> CoverageReport:
    """
    Parse the RUCOVERAGE stream-file output into a CoverageReport.

    Expected format — one procedure per line:
        <procedure_name>;<covered_flag>   (covered_flag: 1=covered, 0=not)

    Falls back to UNCERTAIN (0/0) if the text cannot be parsed, so the
    calling code receives a report it can check for ``procedures_total == 0``.
    """
    total = 0
    covered = 0
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(";")
        if len(parts) >= 2:
            total += 1
            try:
                if int(parts[1].strip()) >= 1:
                    covered += 1
            except ValueError:
                pass

    if total == 0:
        warnings.warn(
            f"RUCOVERAGE output for {svcpgm!r} could not be parsed "
            f"(no valid lines found). Coverage will show as 0/0.\n"
            f"Raw output snippet:\n{text[:300]}"
        )

    return CoverageReport(svcpgm=svcpgm, procedures_total=total, procedures_covered=covered)


# ---------------------------------------------------------------------------
# IBM i invocation
# ---------------------------------------------------------------------------

def _run_coverage_real(lib: str, svcpgm: str) -> CoverageReport:
    """
    Invoke RUCOVERAGE on IBM i and return a parsed CoverageReport.

    If RUCOVERAGE is not available (older RPGUnit), catches the error,
    warns, and returns a zero report so the pipeline can continue.
    """
    tmp_path = f"/tmp/sentinel_cov_{svcpgm.lower()}.csv"
    try:
        run_cl(
            f"RUCOVERAGE TSTPGM({lib}/{svcpgm}) "
            f"COVERAGETYPE(*PROCEDURE) "
            f"RPTTYPE(*TEXT) "
            f"RPTSTMF('{tmp_path}')"
        )
        raw = run_cl(f"QSH CMD('cat {tmp_path}')")
    except Exception as exc:
        warnings.warn(
            f"RUCOVERAGE failed for {lib}/{svcpgm} — "
            f"RPGUnit may not support coverage on this system.\n"
            f"Error: {exc}\n"
            "Coverage will be shown as unavailable."
        )
        return CoverageReport(svcpgm=svcpgm, procedures_total=0, procedures_covered=0)

    return _parse_coverage_output(raw, svcpgm)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_coverage(lib: str, svcpgm: str, *, after: bool = False) -> CoverageReport:
    """
    Return a CoverageReport for a test service program.

    In stub mode the result is driven by env vars:
        SENTINEL_STUB_COVERAGE_BEFORE  (default "2/4")
        SENTINEL_STUB_COVERAGE_AFTER   (default "3/4")

    Pass ``after=True`` to retrieve the post-proposal figure in stub mode.

    Args:
        lib:      Library name, e.g. "MYLIB"
        svcpgm:   Test service program name, e.g. "ORDCALCT"
        after:    When True in stub mode, return the 'after' stub figure.

    Returns:
        CoverageReport with procedures_total, procedures_covered, and pct.
    """
    if _is_stub():
        return _stub_after(svcpgm) if after else _stub_before(svcpgm)
    return _run_coverage_real(lib, svcpgm)
