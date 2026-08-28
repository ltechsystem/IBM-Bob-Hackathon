"""
scripts/test_diff.py — Manually trigger a diff for a named source member.

This script exercises the diff engine (sentinel/diff.py and sentinel/store.py)
without needing a compile event or the full watcher loop.

Usage
-----
# First run — seeds the snapshot (no diff produced):
    python scripts/test_diff.py --lib MYLIB --srcpf QRPGLESRC --mbr ORDCALC

# Second run — if source changed since first run, a diff is shown:
    python scripts/test_diff.py --lib MYLIB --srcpf QRPGLESRC --mbr ORDCALC

# Force re-seed (overwrite existing snapshot with current source):
    python scripts/test_diff.py --lib MYLIB --srcpf QRPGLESRC --mbr ORDCALC --seed

Works with IBMI_STUB=true — no real IBM i connection needed.
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from sentinel.diff import diff_member, commit_snapshot, seed_snapshot
from sentinel.store import load_snapshot, snapshot_exists

console = Console()


def main() -> None:
    parser = argparse.ArgumentParser(description="Manually diff a source member against its snapshot")
    parser.add_argument("--lib",   default="MYLIB",      help="IBM i library (default: MYLIB)")
    parser.add_argument("--srcpf", default="QRPGLESRC",  help="Source physical file (default: QRPGLESRC)")
    parser.add_argument("--mbr",   default="ORDCALC",    help="Member name (default: ORDCALC)")
    parser.add_argument("--seed",  action="store_true",  help="Force re-seed snapshot with current source")
    parser.add_argument("--commit",action="store_true",  help="Commit current source as new snapshot after diffing")
    args = parser.parse_args()

    lib, srcpf, mbr = args.lib.upper(), args.srcpf.upper(), args.mbr.upper()

    stub_mode = os.environ.get("IBMI_STUB", "false").strip().lower() in ("1", "true", "yes")
    mode_label = "[yellow](stub mode)[/yellow]" if stub_mode else "[green](real IBM i)[/green]"

    console.print(f"\n[bold blue]🛡 Sentinel Diff Tool[/bold blue] {mode_label}")
    console.print(f"   Member: [bold]{lib}/{srcpf}/{mbr}[/bold]\n")

    # --- Force re-seed if requested ---
    if args.seed:
        seed_snapshot(lib, srcpf, mbr)
        console.print(f"[yellow]  Snapshot forcibly re-seeded for {mbr}.[/yellow]")
        # Clear snapshot so diff_member sees it as new on this run
        from sentinel.store import save_snapshot
        from sentinel.ibmi import get_source_member
        source = get_source_member(lib, srcpf, mbr)
        save_snapshot(lib, srcpf, mbr, source)
        console.print(f"[dim]  Done — run again without --seed to see future diffs.[/dim]")
        return

    # --- Seed if first time ---
    if not snapshot_exists(lib, srcpf, mbr):
        seed_snapshot(lib, srcpf, mbr)
        console.print(
            Panel(
                Text(f"No snapshot found for {mbr}. Seeded from current source.\nRun again after making a change to see a diff.", style="yellow"),
                title="[yellow]FIRST RUN — SNAPSHOT SEEDED[/yellow]",
                border_style="yellow",
            )
        )
        return

    # --- Diff ---
    result = diff_member(lib, srcpf, mbr)

    if not result.has_changes:
        console.print(
            Panel(
                Text(f"Source for {mbr} is identical to snapshot — no changes detected.", style="dim"),
                title="[dim]NO CHANGES[/dim]",
                border_style="dim",
            )
        )
        return

    # Print stats
    lines = result.unified_diff.splitlines()
    added   = sum(1 for l in lines if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in lines if l.startswith("-") and not l.startswith("---"))

    console.print(
        Panel(
            f"[bold white]{mbr}[/bold white]  "
            f"[bold green]+{added}[/bold green] / [bold red]-{removed}[/bold red] lines",
            title="[green]DIFF DETECTED[/green]",
            border_style="green",
        )
    )

    # Print diff with colour
    for line in lines[:60]:
        if line.startswith("+") and not line.startswith("+++"):
            console.print(f"[green]{line}[/green]")
        elif line.startswith("-") and not line.startswith("---"):
            console.print(f"[red]{line}[/red]")
        elif line.startswith("@@"):
            console.print(f"[cyan]{line}[/cyan]")
        else:
            console.print(f"[dim]{line}[/dim]")

    if len(lines) > 60:
        console.print(f"[dim]  ... {len(lines) - 60} more lines[/dim]")

    # --- Optionally commit ---
    if args.commit:
        commit_snapshot(result)
        console.print(f"\n[green]  Snapshot committed — next diff will use this version as baseline.[/green]")
    else:
        console.print(f"\n[dim]  Snapshot NOT updated. Pass --commit to update baseline.[/dim]")


if __name__ == "__main__":
    main()
