"""
scripts/test_coverage.py — Manual test for sentinel/coverage.py.

Calls get_coverage() for a named test service program and prints the
before/after delta to verify the coverage module works end-to-end.

Usage
-----
# Stub mode (default — no IBM i required):
    py scripts/test_coverage.py

# Override stub figures:
    SENTINEL_STUB_COVERAGE_BEFORE=1/4 SENTINEL_STUB_COVERAGE_AFTER=4/4 \\
        py scripts/test_coverage.py

# Real IBM i mode:
    IBMI_STUB=false py scripts/test_coverage.py --lib MYLIB --svcpgm ORDCALCT
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from rich.console import Console
from rich.panel import Panel

from sentinel.coverage import get_coverage

console = Console()


def _coverage_bar(report) -> str:
    """Return a simple ASCII bar: ##########  3/4 (75.0%)"""
    total = report.procedures_total
    if total == 0:
        return "[dim]coverage unavailable[/dim]"
    filled = round(10 * report.procedures_covered / total)
    bar = "#" * filled + "." * (10 - filled)
    return f"{bar}  {report.procedures_covered}/{total} ({report.pct}%)"


def main() -> None:
    parser = argparse.ArgumentParser(description="Test sentinel coverage module")
    parser.add_argument("--lib",    default="MYLIB",    help="Library name (default: MYLIB)")
    parser.add_argument("--svcpgm", default="ORDCALCT", help="Test service program (default: ORDCALCT)")
    args = parser.parse_args()

    stub = os.environ.get("IBMI_STUB", "true").strip().lower() in ("1", "true", "yes")
    mode_note = " [yellow](stub mode)[/yellow]" if stub else ""

    console.print(
        Panel(
            f"Library : [bold]{args.lib}[/bold]\n"
            f"Svcpgm  : [bold]{args.svcpgm}[/bold]{mode_note}",
            title="[bold blue]Sentinel - Coverage Test[/bold blue]",
            border_style="blue",
        )
    )

    console.print("[dim]  Fetching before-coverage...[/dim]")
    before = get_coverage(args.lib, args.svcpgm, after=False)

    console.print("[dim]  Fetching after-coverage...[/dim]")
    after = get_coverage(args.lib, args.svcpgm, after=True)

    if before.procedures_total == 0:
        console.print("[yellow]  Coverage data unavailable (RUCOVERAGE not supported or parse failed).[/yellow]")
        return

    delta = after.delta_str(before)
    delta_colour = "green" if not delta.startswith("-") else "red"

    console.print(
        Panel(
            f"Before  : {_coverage_bar(before)}\n"
            f"After   : {_coverage_bar(after)}\n"
            f"Delta   : [{delta_colour}][bold]{delta}[/bold][/{delta_colour}]",
            title="[bold green]Coverage Delta[/bold green]",
            border_style="green",
        )
    )


if __name__ == "__main__":
    main()
