"""
scripts/test_runner.py — Manually invoke the RPGUnit runner and print parsed failures.

Exercises sentinel/runner.py and sentinel/parser.py without needing the
full watcher pipeline.

Usage
-----
# Run with stub output (default scenario: one_failure):
    python scripts/test_runner.py

# Run a specific stub scenario:
    python scripts/test_runner.py --scenario all_pass
    python scripts/test_runner.py --scenario regression

# Run against a real IBM i (IBMI_STUB=false in .env):
    python scripts/test_runner.py --lib MYLIB --mbr ORDCALC

Scenarios (stub mode)
---------------------
  one_failure   — test_rounding fails (stale test demo)
  all_pass      — all three tests pass
  regression    — test_basicCalc fails with wrong value (regression demo)
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from sentinel.runner import run_tests, test_suite_name
from sentinel.parser import parse_output, parse_summary

console = Console()


def main() -> None:
    parser = argparse.ArgumentParser(description="Manually run RPGUnit tests and show parsed failures")
    parser.add_argument("--lib",      default="MYLIB",      help="IBM i library (default: MYLIB)")
    parser.add_argument("--mbr",      default="ORDCALC",    help="Source member name (default: ORDCALC)")
    parser.add_argument("--scenario", default=None,
                        help="Stub scenario: one_failure | all_pass | regression (overrides SENTINEL_STUB_SCENARIO)")
    args = parser.parse_args()

    # Override stub scenario via env if --scenario passed
    if args.scenario:
        os.environ["SENTINEL_STUB_SCENARIO"] = args.scenario

    lib = args.lib.upper()
    mbr = args.mbr.upper()
    suite = test_suite_name(mbr)

    stub_mode = os.environ.get("IBMI_STUB", "false").strip().lower() in ("1", "true", "yes")
    mode_label = "[yellow](stub mode)[/yellow]" if stub_mode else "[green](real IBM i)[/green]"
    scenario = os.environ.get("SENTINEL_STUB_SCENARIO", "one_failure")

    console.print(f"\n[bold blue]🛡 Sentinel RPGUnit Runner[/bold blue] {mode_label}")
    console.print(f"   Suite : [bold]{lib}/{suite}[/bold]")
    if stub_mode:
        console.print(f"   Scenario: [bold]{scenario}[/bold]\n")

    # --- Run ---
    console.print("[dim]  Running tests...[/dim]")
    raw = run_tests(lib, suite)

    # --- Summary ---
    summary = parse_summary(raw)
    total    = summary["tests_run"]
    failures = summary["failures"]
    errors   = summary["errors"]
    passed   = total - failures - errors

    status_colour = "green" if failures == 0 and errors == 0 else "red"
    status_text   = "ALL PASS" if failures == 0 and errors == 0 else f"{failures} FAILURE(S)"

    console.print(
        Panel(
            f"[bold white]Tests run:[/bold white] {total}   "
            f"[bold green]Passed:[/bold green] {passed}   "
            f"[bold red]Failed:[/bold red] {failures}   "
            f"[bold yellow]Errors:[/bold yellow] {errors}",
            title=f"[bold {status_colour}]{status_text}[/bold {status_colour}]",
            border_style=status_colour,
        )
    )

    # --- Parse failures ---
    test_failures = parse_output(raw, suite)

    if not test_failures:
        console.print("[green]  ✓ No failures to report.[/green]\n")
        return

    # Display each failure in a table
    table = Table(title="Test Failures", border_style="red", show_lines=True)
    table.add_column("Procedure",  style="bold white",  no_wrap=True)
    table.add_column("Assertion",  style="cyan")
    table.add_column("Expected",   style="green")
    table.add_column("Actual",     style="red")

    for f in test_failures:
        table.add_row(f.procedure, f.assertion, f.expected, f.actual)

    console.print(table)

    # Raw output (collapsed)
    console.print("\n[dim]Raw RPGUnit output:[/dim]")
    for line in raw.splitlines():
        console.print(f"[dim]{line}[/dim]")


if __name__ == "__main__":
    main()
