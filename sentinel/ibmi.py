"""
sentinel/ibmi.py — IBM i connection layer.

Wraps itoolkit transport and exposes two primitives used by the rest of
Sentinel:

    run_cl(command)                      -> str   raw spool / output text
    get_source_member(lib, srcpf, mbr)   -> str   full source text

Connection parameters are read from environment variables (load .env before
importing this module, or call dotenv.load_dotenv() in your entry point):

    IBMI_HOST       hostname or IP of the IBM i partition
    IBMI_USER       user profile
    IBMI_PASSWORD   password
    IBMI_PORT       XMLSERVICE HTTP port (default: 80)

    IBMI_STUB       set to "true" to skip all real IBM i calls and return
                    deterministic fake data.  Safe for development when no
                    IBM i system is available yet.

Transport: itoolkit HttpTransport connecting to the XMLSERVICE CGI endpoint:
    http://<IBMI_HOST>:<IBMI_PORT>/cgi-bin/xmlcgi.pgm

This requires XMLSERVICE to be installed and the HTTP server started on the
IBM i partition.  No ODBC driver or Zend Server is needed.
"""

from __future__ import annotations

import os
import textwrap
from functools import lru_cache


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class ConfigurationError(RuntimeError):
    """Raised when required IBM i environment variables are missing."""


class IBMiError(RuntimeError):
    """Raised when an IBM i command or data-access call fails."""


# ---------------------------------------------------------------------------
# Stub helpers
# ---------------------------------------------------------------------------

def _is_stub() -> bool:
    """Return True when IBMI_STUB env var is set to a truthy value."""
    return os.environ.get("IBMI_STUB", "false").strip().lower() in ("1", "true", "yes")


# Fake source members returned in stub mode.
# ORDCALC  — the demo calculation module (initial clean version)
# ORDCALCT — corresponding RPGUnit test suite
_STUB_MEMBERS: dict[str, str] = {
    "ORDCALC": textwrap.dedent("""\
        **FREE
        // ORDCALC - Order calculation procedure (base)
        ctl-opt nomain;

        dcl-proc calcTotal export;
          dcl-pi *n packed(11:2);
            qty   packed(7:0) const;
            price packed(11:2) const;
            disc  packed(5:2) const;
          end-pi;

          dcl-s total packed(11:2);
          total = qty * price * (1 - disc / 100);
          total = %dech(total: 11: 2);  // round to 2 dp
          return total;
        end-proc;
    """),
    "ORDCALCT": textwrap.dedent("""\
        **FREE
        // ORDCALCT - RPGUnit tests for ORDCALC

        dcl-proc test_basicCalc;
          dcl-s result packed(11:2);
          result = calcTotal(10: 5.00: 0);
          iEqual(50.00: result);
        end-proc;

        dcl-proc test_discountApplied;
          dcl-s result packed(11:2);
          result = calcTotal(10: 5.00: 10);
          iEqual(45.00: result);
        end-proc;

        dcl-proc test_rounding;
          dcl-s result packed(11:2);
          result = calcTotal(3: 3.33: 0);
          iEqual(9.99: result);
        end-proc;
    """),
}

# Changed source variants — used when SENTINEL_STUB_SCENARIO is not all_pass.
# one_failure  → rounding rule changed to 1 dp (makes test_rounding stale)
# regression   → off-by-one in qty  (genuine bug in test_basicCalc)
_STUB_MEMBERS_CHANGED: dict[str, dict[str, str]] = {
    "one_failure": {
        "ORDCALC": textwrap.dedent("""\
            **FREE
            // ORDCALC - Order calculation procedure (step1: 1-dp rounding)
            ctl-opt nomain;

            dcl-proc calcTotal export;
              dcl-pi *n packed(11:2);
                qty   packed(7:0) const;
                price packed(11:2) const;
                disc  packed(5:2) const;
              end-pi;

              dcl-s total packed(11:2);
              total = qty * price * (1 - disc / 100);
              total = %dech(total: 11: 1);  // CHANGED: round to 1 dp
              return total;
            end-proc;
        """),
    },
    "regression": {
        "ORDCALC": textwrap.dedent("""\
            **FREE
            // ORDCALC - Order calculation procedure (step2: off-by-one bug)
            ctl-opt nomain;

            dcl-proc calcTotal export;
              dcl-pi *n packed(11:2);
                qty   packed(7:0) const;
                price packed(11:2) const;
                disc  packed(5:2) const;
              end-pi;

              dcl-s total packed(11:2);
              total = (qty - 1) * price * (1 - disc / 100);  // BUG: qty-1
              total = %dech(total: 11: 2);
              return total;
            end-proc;
        """),
    },
}

_STUB_DEFAULT_SOURCE = textwrap.dedent("""\
    **FREE
    // Stub source member — set IBMI_STUB=false and provide real IBM i
    // credentials to read actual source members.
    ctl-opt nomain;
    dcl-proc stubProc export;
      return;
    end-proc;
""")

_STUB_CL_OUTPUT = "+++ success"


# ---------------------------------------------------------------------------
# Internal helpers (real IBM i path)
# ---------------------------------------------------------------------------

def _require_env(name: str) -> str:
    """Return the value of *name* or raise ConfigurationError."""
    value = os.environ.get(name)
    if not value:
        raise ConfigurationError(
            f"Required environment variable {name!r} is not set. "
            "Copy .env.example to .env and fill in your IBM i credentials, "
            "or set IBMI_STUB=true to run without a real IBM i connection."
        )
    return value


@lru_cache(maxsize=1)
def _transport():
    """
    Build and cache one HttpTransport for the lifetime of the process.

    Call _transport.cache_clear() in tests to reset between cases.
    """
    from itoolkit.transport import HttpTransport

    host = _require_env("IBMI_HOST")
    user = _require_env("IBMI_USER")
    password = _require_env("IBMI_PASSWORD")
    port = int(os.environ.get("IBMI_PORT", "80"))
    url = f"http://{host}:{port}/cgi-bin/xmlcgi.pgm"
    return HttpTransport(url, user, password)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_cl(command: str) -> str:
    """
    Run a CL command on IBM i and return the output as a string.

    When IBMI_STUB=true, returns a fixed success string without contacting
    any IBM i system.

    Args:
        command: CL command string, e.g. ``"DSPJOB"``

    Returns:
        Textual output of the command.

    Raises:
        ConfigurationError: if IBM i env vars are missing (real mode only).
        IBMiError: if XMLSERVICE reports a command error (real mode only).
    """
    if _is_stub():
        return _STUB_CL_OUTPUT

    from itoolkit import iToolKit, iCmd

    itk = iToolKit(iret=0, ids=1, irow=0)
    itk.add(iCmd("cmd", command))
    itk.call(_transport())

    result = itk["cmd"]

    if isinstance(result, dict):
        success_flag = str(result.get("success", ""))
        error_flag = result.get("error", result.get("xmlerrmsg", ""))

        if error_flag:
            raise IBMiError(
                f"CL command failed — command: {command!r}  error: {error_flag}"
            )

        rows = result.get("row", [])
        if isinstance(rows, list):
            return "\n".join(str(r) for r in rows)
        if rows:
            return str(rows)
        return success_flag

    return str(result)


def get_source_member(lib: str, srcpf: str, mbr: str) -> str:
    """
    Retrieve the full text of an IBM i source member.

    When IBMI_STUB=true, returns stub RPG source for known demo members
    (ORDCALC, ORDCALCT) and a generic stub for anything else.

    In real mode, reads via IFS path:
        /QSYS.LIB/<LIB>.LIB/<SRCPF>.FILE/<MBR>.MBR

    Args:
        lib:   Library name, e.g. ``"MYLIB"``
        srcpf: Source physical file, e.g. ``"QRPGLESRC"``
        mbr:   Member name, e.g. ``"ORDCALC"``

    Returns:
        The raw source text of the member.

    Raises:
        ConfigurationError: if IBM i env vars are missing (real mode only).
        IBMiError: if the member cannot be read (real mode only).
    """
    if _is_stub():
        scenario = os.environ.get("SENTINEL_STUB_SCENARIO", "one_failure")
        changed = _STUB_MEMBERS_CHANGED.get(scenario, {})
        source = changed.get(mbr.upper()) or _STUB_MEMBERS.get(mbr.upper(), _STUB_DEFAULT_SOURCE)
        return source

    ifs_path = (
        f"/QSYS.LIB/{lib.upper()}.LIB/{srcpf.upper()}.FILE/{mbr.upper()}.MBR"
    )
    raw = run_cl(f"QSH CMD('cat {ifs_path}')")

    if not raw or not raw.strip():
        raise IBMiError(
            f"Source member {lib}/{srcpf}/{mbr} returned empty content. "
            "Verify the member exists and the user has *USE authority to the file."
        )
    return raw
