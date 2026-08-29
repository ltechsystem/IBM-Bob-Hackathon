"""
sentinel/watcher.py — Compile-event watcher and main polling loop.

Polls IBM i for successful compile events, then triggers the diff engine
and RPGUnit test runner for the compiled member.

Compile detection strategy
--------------------------
We poll the IBM i job log for CPF messages that indicate a successful
compile.  Specifically, we look for:

    CPC5D07 — *MODULE object <name> created in library <lib>.
    CPC5B05 — *PGM object <name> created in library <lib>.
    CPC5B06 — *SRVPGM object <name> created in library <lib>.

In stub mode (IBMI_STUB=true) we skip real polling and instead emit a
synthetic compile event every other poll cycle so the pipeline can be
exercised end-to-end without a live IBM i system.

Usage
-----
Run directly:
    python -m sentinel.watcher --lib MYLIB --srcpf QRPGLESRC --mbr ORDCALC

Or import and call watch() programmatically.
"""

from __future__ import annotations

import os
import time
import argparse
from dataclasses import dataclass

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from sentinel.ibmi import run_cl
from sentinel.diff import diff_member, commit_snapshot, seed_snapshot, DiffResult
from sentinel.runner import run_tests, test_suite_name
from sentinel.parser import parse_output, parse_summary
from sentinel.models import TestFailure, CoverageReport
from sentinel.classifier import classify
from sentinel.proposals import present_proposal
from sentinel.store import load_snapshot
from sentinel.coverage import get_coverage

load_dotenv()

console = Console()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def _poll_interval() -> float:
    return float(os.environ.get("SENTINEL_POLL_INTERVAL_SECS", "5"))


def _is_stub() -> bool:
    return os.environ.get("IBMI_STUB", "false").strip().lower() in ("1", "true", "yes")


# ---------------------------------------------------------------------------
# Compile event detection
# ---------------------------------------------------------------------------

@dataclass
class CompileEvent:
    lib: str
    srcpf: str
    mbr: str
    message_id: str  # e.g. CPC5D07


def _detect_compile_events_real(lib: str, srcpf: str, mbr: str) -> list[CompileEvent]:
    """
    Poll QHST for recent successful compile messages for this member.

    CPC5D07 = *MODULE created
    CPC5B05 = *PGM created
    CPC5B06 = *SRVPGM created
    """
    interval = int(_poll_interval())
    try:
        output = run_cl(
            f"DSPLOG LOG(QHST) "
            f"PERIOD((*LAST {interval} *SECONDS)) "
            f"OUTPUT(*OUTFILE) OUTFILE(QTEMP/SENTINEL)"
        )
    except Exception:
        return []

    events = []
    for msg_id in ("CPC5D07", "CPC5B05", "CPC5B06"):
        if msg_id in output and mbr.upper() in output.upper():
            events.append(CompileEvent(lib=lib, srcpf=srcpf, mbr=mbr, message_id=msg_id))
            break
    return events


_stub_tick = 0


def _detect_compile_events_stub(lib: str, srcpf: str, mbr: str) -> list[CompileEvent]:
    """Emit a synthetic compile event every second poll cycle in stub mode."""
    global _stub_tick
    _stub_tick += 1
    if _stub_tick % 2 == 0:
        return [CompileEvent(lib=lib, srcpf=srcpf, mbr=mbr, message_id="CPC5D07-STUB")]
    return []


def detect_compile_events(lib: str, srcpf: str, mbr: str) -> list[CompileEvent]:
    """Return compile events detected since the last poll."""
    if _is_stub():
        return _detect_compile_events_stub(lib, srcpf, mbr)
    return _detect_compile_events_real(lib, srcpf, mbr)


# ---------------------------------------------------------------------------
# Terminal rendering helpers
# ---------------------------------------------------------------------------

def _print_event(event: CompileEvent) -> None:
    console.print(
        f"[bold cyan]>>  Compile detected[/bold cyan] "
        f"[white]{event.lib}/{event.srcpf}/{event.mbr}[/white] "
        f"[dim]({event.message_id})[/dim]"
    )


def _print_diff_summary(result: DiffResult) -> None:
    if result.is_new:
        console.print(
            Panel(
                Text(f"New member — seeding snapshot for {result.lib}/{result.srcpf}/{result.mbr}", style="yellow"),
                title="[yellow]NEW MEMBER[/yellow]",
                border_style="yellow",
            )
        )
        return

    if not result.has_changes:
        console.print(f"[dim]  No source changes detected for {result.mbr}[/dim]")
        return

    lines = result.unified_diff.splitlines()
    added   = sum(1 for l in lines if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in lines if l.startswith("-") and not l.startswith("---"))

    console.print(
        Panel(
            f"[bold white]{result.mbr}[/bold white]  "
            f"[bold green]+{added}[/bold green] / [bold red]-{removed}[/bold red] lines changed",
            title="[green]DIFF[/green]",
            border_style="green",
        )
    )

    diff_lines = result.unified_diff.splitlines()
    for line in diff_lines[:40]:
        if line.startswith("+") and not line.startswith("+++"):
            console.print(f"[green]{line}[/green]")
        elif line.startswith("-") and not line.startswith("---"):
            console.print(f"[red]{line}[/red]")
        elif line.startswith("@@"):
            console.print(f"[cyan]{line}[/cyan]")
        else:
            console.print(f"[dim]{line}[/dim]")

    if len(diff_lines) > 40:
        console.print(f"[dim]  ... {len(diff_lines) - 40} more lines[/dim]")


def _print_coverage_delta(before: CoverageReport, after: CoverageReport) -> None:
    """Print a before → after coverage delta panel."""
    if before.procedures_total == 0:
        console.print("[dim]  Coverage data unavailable (RUCOVERAGE not supported on this system).[/dim]")
        return

    delta = after.delta_str(before)
    delta_colour = "green" if not delta.startswith("-") else "red"

    def _bar(report: CoverageReport) -> str:
        filled = round(10 * report.procedures_covered / report.procedures_total)
        return "#" * filled + "." * (10 - filled)

    console.print(
        Panel(
            f"Before  : {_bar(before)}  {before.procedures_covered}/{before.procedures_total} ({before.pct}%)\n"
            f"After   : {_bar(after)}  {after.procedures_covered}/{after.procedures_total} ({after.pct}%)\n"
            f"Delta   : [{delta_colour}][bold]{delta}[/bold][/{delta_colour}]",
            title="[bold cyan]Coverage[/bold cyan]",
            border_style="cyan",
        )
    )


# ---------------------------------------------------------------------------
# Main watch loop
# ---------------------------------------------------------------------------

def watch(lib: str, srcpf: str, mbr: str, once: bool = False) -> DiffResult | None:
    """
    Poll for compile events for a given member, trigger diffs and run tests.

    Args:
        lib:   Library name
        srcpf: Source physical file
        mbr:   Member name
        once:  If True, run one poll cycle and return.
               If False, loop forever until Ctrl+C.

    Returns:
        The most recent DiffResult (only meaningful when once=True).
    """
    interval = _poll_interval()
    stub_note = " [yellow](stub mode)[/yellow]" if _is_stub() else ""

    console.print(
        Panel(
            f"Watching [bold]{lib}/{srcpf}/{mbr}[/bold]{stub_note}\n"
            f"Poll interval: [bold]{interval}s[/bold]  ·  Press Ctrl+C to stop",
            title="[bold blue]Sentinel Watcher[/bold blue]",
            border_style="blue",
        )
    )

    # Seed snapshot on first run if member not yet known
    try:
        seed_snapshot(lib, srcpf, mbr)
        console.print(f"[dim]  Snapshot seeded for {mbr}[/dim]")
    except Exception as exc:
        console.print(f"[yellow]  Warning: could not seed snapshot — {exc}[/yellow]")

    last_result: DiffResult | None = None

    while True:
        try:
            events = detect_compile_events(lib, srcpf, mbr)

            for event in events:
                _print_event(event)

                # 1. Diff
                result = diff_member(lib, srcpf, mbr)
                _print_diff_summary(result)
                last_result = result

                if not result.has_changes:
                    continue

                # 2. Coverage — before
                suite = test_suite_name(result.mbr)
                coverage_before = get_coverage(result.lib, suite)

                # 3. Run tests
                console.print(f"[dim]  Running test suite {suite}...[/dim]")
                raw = run_tests(result.lib, suite)
                summary = parse_summary(raw)
                failures = parse_output(raw, suite)

                total    = summary["tests_run"]
                fail_cnt = summary["failures"]
                passed   = total - fail_cnt - summary["errors"]

                if fail_cnt == 0:
                    console.print(f"[green]  All {total} test(s) passed.[/green]")
                    commit_snapshot(result)
                    console.print("[dim]  Snapshot updated.[/dim]")
                else:
                    console.print(
                        Panel(
                            f"[bold red]{fail_cnt} failure(s)[/bold red] in [bold]{suite}[/bold]  "
                            f"({passed}/{total} passed)\n"
                            + "\n".join(f"  • {f.summary}" for f in failures),
                            title="[red]TEST FAILURES — snapshot NOT updated[/red]",
                            border_style="red",
                        )
                    )

                    # Load the last-known-good test snapshot so Bob has context
                    last_good_test = load_snapshot(result.lib, result.srcpf, suite) or ""

                    # Classify and propose fixes for each failure
                    for failure in failures:
                        console.print(
                            f"[dim]  Classifying failure: {failure.procedure or failure.summary}...[/dim]"
                        )
                        try:
                            classification = classify(
                                result.unified_diff,
                                failure,
                                last_good_test,
                            )
                        except Exception as exc:
                            console.print(f"[red]  Classifier error: {exc}[/red]")
                            continue

                        present_proposal(classification, result.mbr)

                # 4. Coverage — after, print delta
                _print_coverage_delta(coverage_before, get_coverage(result.lib, suite, after=True))

        except KeyboardInterrupt:
            console.print("\n[dim]Sentinel stopped.[/dim]")
            break
        except Exception as exc:
            console.print(f"[red]  Watcher error: {exc}[/red]")

        if once:
            if last_result is not None:
                return last_result
            # Stub emits events on even ticks only — poll once more before giving up
            time.sleep(0)
            continue

        time.sleep(interval)

    return last_result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sentinel source member watcher")
    parser.add_argument("--lib",   required=True, help="IBM i library, e.g. MYLIB")
    parser.add_argument("--srcpf", required=True, help="Source physical file, e.g. QRPGLESRC")
    parser.add_argument("--mbr",   required=True, help="Member name, e.g. ORDCALC")
    parser.add_argument("--once",  action="store_true", help="Run one poll cycle and exit")
    args = parser.parse_args()

    watch(lib=args.lib, srcpf=args.srcpf, mbr=args.mbr, once=args.once)
