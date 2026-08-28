"""
sentinel/proposals.py — Proposal engine and CLI review layer.

Takes a Classification from the Bob classifier and presents it to the
developer as a coloured, git-style diff in the terminal.  The developer
can accept, reject, or edit each proposal.  Nothing is auto-committed.

Verdict render paths
--------------------
STALE / NEW_COVERAGE_NEEDED
    Show the proposed patch as a coloured unified diff.
    Prompt: [A]ccept / [R]eject / [E]dit
    Accept → save to ./proposals/<timestamp>_<member>.patch
    Reject → save to ./proposals/<timestamp>_<member>.rejected
    Edit   → open patch in $EDITOR, re-read, save as accepted

REGRESSION
    Red banner: REGRESSION DETECTED — no patch proposed.
    Developer must fix the source code manually.

UNCERTAIN
    Yellow banner showing Bob's rationale and confidence.
    Prompt developer to classify manually:
    [S]tale / [R]egression / [N]ew coverage / [K]ip
    Routes to the appropriate path based on their answer.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.prompt import Prompt
from rich.rule import Rule

from sentinel.models import Classification

console = Console()

# ---------------------------------------------------------------------------
# Proposals directory
# ---------------------------------------------------------------------------

def _proposals_dir() -> Path:
    d = Path(os.environ.get("SENTINEL_PROPOSALS_DIR", "proposals"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _patch_path(member: str, suffix: str) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return _proposals_dir() / f"{ts}_{member.upper()}.{suffix}"


# ---------------------------------------------------------------------------
# Diff rendering
# ---------------------------------------------------------------------------

def _render_diff(patch: str, title: str, border_colour: str) -> None:
    """Print a coloured unified diff inside a rich Panel."""
    if not patch.strip():
        console.print("[dim]  (no patch)[/dim]")
        return

    console.print(
        Panel(
            Syntax(patch, "diff", theme="monokai", line_numbers=False),
            title=title,
            border_style=border_colour,
            padding=(0, 1),
        )
    )


# ---------------------------------------------------------------------------
# Editor integration
# ---------------------------------------------------------------------------

def _open_in_editor(content: str) -> str:
    """
    Write content to a temp file, open it in $EDITOR, return edited content.
    Falls back to notepad on Windows if $EDITOR is not set.
    """
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL")
    if not editor:
        editor = "notepad" if os.name == "nt" else "vi"

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".patch", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        tmp_path = f.name

    try:
        subprocess.run([editor, tmp_path], check=False)
        return Path(tmp_path).read_text(encoding="utf-8")
    finally:
        Path(tmp_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Save helpers
# ---------------------------------------------------------------------------

def _save_accepted(member: str, patch: str) -> Path:
    path = _patch_path(member, "patch")
    path.write_text(patch, encoding="utf-8")
    console.print(f"[green]  ✓ Patch saved → {path}[/green]")
    return path


def _save_rejected(member: str, patch: str, reason: str = "") -> Path:
    path = _patch_path(member, "rejected")
    content = f"# Rejected\n# Reason: {reason}\n\n{patch}"
    path.write_text(content, encoding="utf-8")
    console.print(f"[dim]  Proposal rejected → {path}[/dim]")
    return path


# ---------------------------------------------------------------------------
# Render paths
# ---------------------------------------------------------------------------

def _handle_stale_or_new(classification: Classification, member: str) -> str:
    """Show diff, prompt accept / reject / edit."""
    verdict_label = (
        "STALE TEST — update to match new behaviour"
        if classification.verdict == "STALE"
        else "NEW COVERAGE NEEDED — add test for new branch"
    )
    border = "yellow" if classification.verdict == "STALE" else "blue"

    console.print(
        Panel(
            f"[bold white]Verdict:[/bold white] [{border}]{classification.verdict}[/{border}]\n"
            f"[bold white]Confidence:[/bold white] {classification.confidence:.0%}\n\n"
            f"[white]{classification.rationale}[/white]",
            title=f"[bold {border}]{verdict_label}[/bold {border}]",
            border_style=border,
        )
    )

    _render_diff(classification.proposed_patch, "Proposed patch", border)

    console.print(
        "\n  [bold][A][/bold]ccept   [bold][R][/bold]eject   [bold][E][/bold]dit in editor\n"
    )

    choice = Prompt.ask(
        "  Your choice",
        choices=["a", "r", "e"],
        default="a",
        show_choices=False,
        show_default=True,
        console=console,
    ).lower()

    if choice == "a":
        _save_accepted(member, classification.proposed_patch)
        return "accepted"
    elif choice == "r":
        _save_rejected(member, classification.proposed_patch, reason="developer rejected")
        return "rejected"
    else:
        console.print("[dim]  Opening patch in editor...[/dim]")
        edited = _open_in_editor(classification.proposed_patch)
        if edited.strip() == classification.proposed_patch.strip():
            console.print("[dim]  No changes made in editor.[/dim]")
        _save_accepted(member, edited)
        return "edited"


def _handle_regression(classification: Classification, member: str) -> str:
    """Show red regression banner. No patch offered."""
    console.print(
        Panel(
            f"[bold white]Confidence:[/bold white] {classification.confidence:.0%}\n\n"
            f"[white]{classification.rationale}[/white]\n\n"
            "[bold red]The test is correct. Fix the source code, not the test.[/bold red]",
            title="[bold red]⛔  REGRESSION DETECTED — manual review required[/bold red]",
            border_style="red",
        )
    )
    console.print("[red]  Snapshot NOT updated. Pipeline halted for this member.[/red]")
    return "regression"


def _handle_uncertain(classification: Classification, member: str) -> str:
    """Show uncertainty banner, ask developer to classify manually."""
    threshold = float(os.environ.get("SENTINEL_CONFIDENCE_THRESHOLD", "0.75"))

    console.print(
        Panel(
            f"[bold white]Confidence:[/bold white] {classification.confidence:.0%}  "
            f"[dim](below {threshold:.0%} threshold)[/dim]\n\n"
            f"[white]{classification.rationale}[/white]",
            title="[bold yellow]❓  UNCERTAIN — Bob could not classify with enough confidence[/bold yellow]",
            border_style="yellow",
        )
    )

    console.print(
        "\n  Bob is unsure. Please classify this failure:\n"
        "  [yellow][S][/yellow] Stale    — code changed intentionally, test needs updating\n"
        "  [red][R][/red] Regression — genuine bug, do not update the test\n"
        "  [blue][N][/blue] New test   — new branch added, write a new test\n"
        "  [dim][K][/dim] Skip       — deal with this later\n"
    )

    choice = Prompt.ask(
        "  Your classification",
        choices=["s", "r", "n", "k"],
        default="k",
        show_choices=False,
        show_default=True,
        console=console,
    ).lower()

    if choice == "s":
        console.print("[dim]  Opening editor for manual patch authoring...[/dim]")
        edited = _open_in_editor(
            "# Write your test patch here (unified diff format)\n"
            "# --- ORDCALCT (previous)\n"
            "# +++ ORDCALCT (proposed)\n"
            "# @@ ... @@\n"
        )
        if not edited.strip() or edited.strip().startswith("#"):
            console.print("[dim]  No patch written. Skipping.[/dim]")
            return "skipped"
        _save_accepted(member, edited)
        return "accepted"

    elif choice == "r":
        console.print("[red]  Marked as REGRESSION. Fix the source code.[/red]")
        return "regression"

    elif choice == "n":
        console.print("[dim]  Opening editor for new test authoring...[/dim]")
        edited = _open_in_editor(
            "# Write your new test procedure here (unified diff format)\n"
            "# +dcl-proc test_yourNewTest;\n"
            "# +  ...\n"
            "# +end-proc;\n"
        )
        if not edited.strip() or edited.strip().startswith("#"):
            console.print("[dim]  No patch written. Skipping.[/dim]")
            return "skipped"
        _save_accepted(member, edited)
        return "accepted"

    else:
        console.print("[dim]  Skipped. Revisit in ./proposals/[/dim]")
        return "skipped"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def present_proposal(classification: Classification, member: str) -> str:
    """
    Present a classification result to the developer and handle their response.

    Called by watcher.py after the Bob classifier returns a result for
    each failing test.

    Args:
        classification: The Classification from sentinel/classifier.py
        member:         Source member name (e.g. "ORDCALC") used for
                        naming saved patch files.

    Returns:
        One of: 'accepted' | 'rejected' | 'edited' | 'regression' |
                'skipped' | 'no_patch'
    """
    console.print(Rule(f"[bold]Sentinel Proposal — {member.upper()}[/bold]", style="blue"))

    if classification.verdict in ("STALE", "NEW_COVERAGE_NEEDED"):
        if not classification.proposed_patch.strip():
            console.print(
                f"[yellow]  Bob classified as {classification.verdict} but provided no patch.[/yellow]"
            )
            return "no_patch"
        return _handle_stale_or_new(classification, member)

    elif classification.verdict == "REGRESSION":
        return _handle_regression(classification, member)

    else:  # UNCERTAIN
        return _handle_uncertain(classification, member)
