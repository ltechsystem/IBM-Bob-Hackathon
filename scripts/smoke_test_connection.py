"""
scripts/smoke_test_connection.py — verify IBM i connectivity.

Run this script after filling in your .env file to confirm that Sentinel
can reach the IBM i partition and execute a CL command.

Usage:
    python scripts/smoke_test_connection.py

Expected output on success:
    IBM i connection OK
    DSPJOB output: +++ success DSPJOB
"""

import sys
import os

# Allow running from the repo root without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()  # reads .env from the current working directory

from sentinel.ibmi import run_cl, ConfigurationError, IBMiError

def main() -> None:
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
    print("IBM i connection OK")
    print(f"DSPJOB output: {output[:120]}")


if __name__ == "__main__":
    main()
