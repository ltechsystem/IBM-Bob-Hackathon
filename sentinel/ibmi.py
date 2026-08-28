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

Transport: itoolkit HttpTransport connecting to the XMLSERVICE CGI endpoint:
    http://<IBMI_HOST>:<IBMI_PORT>/cgi-bin/xmlcgi.pgm

This requires XMLSERVICE to be installed and the HTTP server started on the
IBM i partition.  No ODBC driver or Zend Server is needed.
"""

from __future__ import annotations

import os
from functools import lru_cache

from itoolkit import iToolKit, iCmd
from itoolkit.transport import HttpTransport


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class ConfigurationError(RuntimeError):
    """Raised when required IBM i environment variables are missing."""


class IBMiError(RuntimeError):
    """Raised when an IBM i command or data-access call fails."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _require_env(name: str) -> str:
    """Return the value of *name* or raise ConfigurationError."""
    value = os.environ.get(name)
    if not value:
        raise ConfigurationError(
            f"Required environment variable {name!r} is not set. "
            "Copy .env.example to .env and fill in your IBM i credentials."
        )
    return value


@lru_cache(maxsize=1)
def _transport() -> HttpTransport:
    """
    Build and cache one HttpTransport for the lifetime of the process.

    The cache is keyed on the function itself (no args), so the first call
    reads env vars and constructs the transport; every subsequent call returns
    the same object.  Call _transport.cache_clear() in tests to reset it.
    """
    host = _require_env("IBMI_HOST")
    user = _require_env("IBMI_USER")
    password = _require_env("IBMI_PASSWORD")
    port = int(os.environ.get("IBMI_PORT", "80"))
    url = f"http://{host}:{port}/cgi-bin/xmlcgi.pgm"
    return HttpTransport(url, user, password)


def _run_itk(itk: iToolKit) -> None:
    """Execute *itk* against the cached transport."""
    itk.call(_transport())


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_cl(command: str) -> str:
    """
    Run a CL command on IBM i and return the output as a string.

    The command is sent via XMLSERVICE iCmd.  itoolkit parses the XML
    response; any text rows are joined with newlines and returned.  If
    XMLSERVICE reports an error the raw error string is raised as IBMiError.

    Args:
        command: CL command string, e.g. ``"DSPJOB"`` or
                 ``"DSPMSGD MSGID(CPF0000) MSGF(QCPFMSG)"``

    Returns:
        Textual output of the command (may be empty for commands that produce
        no spooled output).

    Raises:
        ConfigurationError: if IBM i env vars are missing.
        IBMiError: if XMLSERVICE reports a command error.
    """
    itk = iToolKit(iprod=0, iret=0, ids=1, irow=0)
    itk.add(iCmd("cmd", command))
    _run_itk(itk)

    result = itk["cmd"]

    # itoolkit returns the parsed response as a dict.
    # A successful iCmd response contains '+++ success' in the 'success' key.
    if isinstance(result, dict):
        success_flag = str(result.get("success", ""))
        error_flag = result.get("error", result.get("xmlerrmsg", ""))

        if error_flag:
            raise IBMiError(
                f"CL command failed — command: {command!r}  error: {error_flag}"
            )

        # Collect output rows if present
        rows = result.get("row", [])
        if isinstance(rows, list):
            return "\n".join(str(r) for r in rows)
        if rows:
            return str(rows)
        # No rows — return the success text so callers can assert non-empty
        return success_flag

    # Fallback: stringify whatever itoolkit returned
    return str(result)


def get_source_member(lib: str, srcpf: str, mbr: str) -> str:
    """
    Retrieve the full text of an IBM i source member.

    Reads the member via its IFS path:
        /QSYS.LIB/<LIB>.LIB/<SRCPF>.FILE/<MBR>.MBR

    Uses ``QSH CMD('cat <path>')`` so no ODBC or special authority beyond
    read access to the source file is needed.  Available on V7R1 and later.

    Sequence numbers and date stamps (columns 1-12 of a fixed-format SRCPF
    record) are **not** stripped here — callers that need clean source should
    strip them themselves.  The diff engine in ``sentinel/diff.py`` handles
    this.

    Args:
        lib:   Library name, e.g. ``"MYLIB"``
        srcpf: Source physical file, e.g. ``"QRPGLESRC"``
        mbr:   Member name, e.g. ``"ORDCALC"``

    Returns:
        The raw source text of the member (lines joined with newlines).

    Raises:
        ConfigurationError: if IBM i env vars are missing.
        IBMiError: if the member cannot be read or returns empty content.
    """
    ifs_path = (
        f"/QSYS.LIB/{lib.upper()}.LIB/{srcpf.upper()}.FILE/{mbr.upper()}.MBR"
    )
    # QSH cat is the simplest portable way to stream a source member as text
    raw = run_cl(f"QSH CMD('cat {ifs_path}')")

    if not raw or not raw.strip():
        raise IBMiError(
            f"Source member {lib}/{srcpf}/{mbr} returned empty content. "
            "Verify the member exists and the user has *USE authority to the file."
        )
    return raw
