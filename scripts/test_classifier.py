"""
scripts/test_classifier.py — Manually test the Bob classifier.

Sends a hardcoded diff + TestFailure to the classifier and prints the
Classification result.  Works in both stub mode and real watsonx mode.

Usage
-----
# Stub mode (default):
    python scripts/test_classifier.py

# Try different stub verdicts:
    python scripts/test_classifier.py --verdict regression
    python scripts/test_classifier.py --verdict new_coverage
    python scripts/test_classifier.py --verdict uncertain

# Real watsonx call (requires WATSONX_* env vars and SENTINEL_BOB_STUB=false):
    python scripts/test_classifier.py --real
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

from sentinel.models import TestFailure
from sentinel.classifier import classify

console = Console()

# ---------------------------------------------------------------------------
# Hardcoded demo inputs (mirror the demo RPG module)
# ---------------------------------------------------------------------------

DEMO_DIFF = """\
--- ORDCALC (previous)
+++ ORDCALC (current)
@@ -10,7 +10,7 @@
   dcl-s total packed(11:2);
   total = qty * price * (1 - disc / 100);
-  total = %dech(total: 11: 2);
+  total = %dech(total: 11: 1);
   return total;
"""

DEMO_FAILURE = TestFailure(
    test_svcpgm="ORDCALCT",
    procedure="TEST_ROUNDING",
    assertion="iEqual",
    expected="9.99",
    actual="10.0",
    raw_output=(
        "Test procedure . . : TEST_ROUNDING\n"
        "Status . . . . . . : *FAILURE\n"
        "Assertion  . . . . : iEqual\n"
        "Expected . . . . . : 9.99\n"
        "Actual . . . . . . : 10.0\n"
        "Error message  . . : Values are not equal."
    ),
)

DEMO_LAST_GOOD_TEST = """\
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
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Test the Sentinel Bob classifier")
    parser.add_argument(
        "--verdict",
        default=None,
        choices=["stale", "regression", "new_coverage", "uncertain"],
        help="Stub verdict to simulate (sets SENTINEL_BOB_STUB_VERDICT)",
    )
    parser.add_argument(
        "--real",
        action="store_true",
        help="Disable stub mode and make a real watsonx API call",
    )
    args = parser.parse_args()

    if args.real:
        os.environ["SENTINEL_BOB_STUB"] = "false"
    else:
        os.environ.setdefault("SENTINEL_BOB_STUB", "true")

    if args.verdict:
        os.environ["SENTINEL_BOB_STUB_VERDICT"] = args.verdict

    stub_mode = os.environ.get("SENTINEL_BOB_STUB", "true").strip().lower() in ("1", "true", "yes")
    mode_label = "[yellow](stub mode)[/yellow]" if stub_mode else "[green](real watsonx)[/green]"
    verdict_label = os.environ.get("SENTINEL_BOB_STUB_VERDICT", "stale") if stub_mode else "live"

    console.print(f"\n[bold blue]🛡 Sentinel Classifier Test[/bold blue] {mode_label}")
    if stub_mode:
        console.print(f"   Stub verdict: [bold]{verdict_label}[/bold]")
    console.print(f"   Failure: [bold]{DEMO_FAILURE.summary}[/bold]\n")

    # Show the diff being sent
    console.print("[dim]Source diff:[/dim]")
    console.print(Syntax(DEMO_DIFF, "diff", theme="monokai", line_numbers=False))

    console.print("\n[dim]Calling classifier...[/dim]")

    result = classify(
        diff=DEMO_DIFF,
        failure=DEMO_FAILURE,
        last_good_test=DEMO_LAST_GOOD_TEST,
    )

    # Verdict colour
    colour_map = {
        "STALE":                "yellow",
        "REGRESSION":           "red",
        "NEW_COVERAGE_NEEDED":  "blue",
        "UNCERTAIN":            "magenta",
    }
    colour = colour_map.get(result.verdict, "white")

    console.print(
        Panel(
            f"[bold {colour}]VERDICT: {result.verdict}[/bold {colour}]\n"
            f"[white]Confidence:[/white] {result.confidence:.0%}\n\n"
            f"[white]Rationale:[/white]\n{result.rationale}",
            title=f"[bold {colour}]Classification Result[/bold {colour}]",
            border_style=colour,
        )
    )

    if result.proposed_patch:
        console.print("\n[dim]Proposed patch:[/dim]")
        console.print(Syntax(result.proposed_patch, "diff", theme="monokai", line_numbers=False))
    elif result.verdict == "REGRESSION":
        console.print("\n[red bold]  ⛔ REGRESSION — no patch proposed. Fix the source code.[/red bold]")
    elif result.verdict == "UNCERTAIN":
        console.print("\n[magenta]  ❓ UNCERTAIN — confidence too low to auto-classify. Human review needed.[/magenta]")


if __name__ == "__main__":
    main()
