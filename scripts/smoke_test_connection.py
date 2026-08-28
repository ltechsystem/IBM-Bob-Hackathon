"""
scripts/smoke_test_connection.py — verify IBM i connectivity.

Run this script after filling in your .env file to confirm that Sentinel
can reach the IBM i partition and execute a CL command.

When IBMI_STUB=true the script verifies the stub path works without a
real IBM i connection.

Usage:
    python scripts/smoke_test_connection.py

Expected output (real mode):
    [REAL] IBM i connection OK
    DSPJOB output: ...

Expected output (stub mode):
    [STUB] IBM i stub mode active — skipping real connection
    IBM i connection OK (stub)
"""

import sys
import os

# Allow running from the repo root without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

from sentinel.ibmi import run_cl, get_source_member, ConfigurationError, IBMiError

def main() -> None:
    stub_mode = os.environ.get("IBMI_STUB", "false").strip().lower() in ("1", "true", "yes")

    if stub_mode:
        print("[STUB] IBM i stub mode active — skipping real connection")
        output = run_cl("DSPJOB")
        assert output, "Stub run_cl returned empty output"
        source = get_source_member("MYLIB", "QRPGLESRC", "ORDCALC")
        assert source, "Stub get_source_member returned empty output"
        print("IBM i connection OK (stub)")
        print(f"Stub CL output : {output}")
        print(f"Stub member    : ORDCALC ({len(source.splitlines())} lines)")
        return

    try:
        output = run_cl("DSPJOB")
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)
    except IBMiError as exc:
        print(f"IBM i error: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        sys.exit(1)

    assert output, "DSPJOB returned empty output — connection may have failed silently"
    print("[REAL] IBM i connection OK")
    print(f"DSPJOB output: {output[:120]}")


if __name__ == "__main__":
    main()
