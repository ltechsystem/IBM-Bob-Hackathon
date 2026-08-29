"""
sentinel/diff.py — Source member diff engine.

Compares the current version of an IBM i source member against the
last-known-good snapshot stored by sentinel/store.py, and returns a
unified diff string suitable for feeding to the Bob classifier.

Typical flow
------------
1. A compile event is detected for MYLIB/QRPGLESRC/ORDCALC.
2. diff_member() fetches the live source via get_source_member().
3. It loads the stored snapshot from the store (if any).
4. It produces a unified diff.
5. If a diff exists, it returns the DiffResult to the caller.
6. The caller decides when to call commit_snapshot() — only after tests
   pass and any proposals are accepted.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field

from sentinel.ibmi import get_source_member
from sentinel.store import load_snapshot, save_snapshot, snapshot_exists


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class DiffResult:
    """The outcome of comparing a source member against its snapshot."""

    lib: str
    srcpf: str
    mbr: str

    # The unified diff string — empty if source is unchanged or member is new
    unified_diff: str

    # The live source text fetched from IBM i (or stub)
    current_source: str

    # The snapshot text (None if this is the first time we've seen this member)
    previous_source: str | None

    # True when the member has never been snapshotted before
    is_new: bool = field(init=False)

    def __post_init__(self) -> None:
        self.is_new = self.previous_source is None

    @property
    def has_changes(self) -> bool:
        """True when the source differs from the snapshot (or is brand new)."""
        return self.is_new or bool(self.unified_diff.strip())

    @property
    def changed_lines(self) -> int:
        """Count of added + removed lines in the diff."""
        count = 0
        for line in self.unified_diff.splitlines():
            if line.startswith(("+", "-")) and not line.startswith(("+++", "---")):
                count += 1
        return count


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def diff_member(lib: str, srcpf: str, mbr: str) -> DiffResult:
    """
    Fetch the current source member and diff it against the stored snapshot.

    Does NOT update the snapshot — call ``commit_snapshot()`` explicitly
    once the change has been validated.

    Args:
        lib:   Library name, e.g. ``"MYLIB"``
        srcpf: Source physical file, e.g. ``"QRPGLESRC"``
        mbr:   Member name, e.g. ``"ORDCALC"``

    Returns:
        A ``DiffResult`` describing what changed.
    """
    current = get_source_member(lib, srcpf, mbr)
    previous = load_snapshot(lib, srcpf, mbr)

    if previous is None:
        # First time we've seen this member — record it as new, no diff yet
        unified = ""
    else:
        prev_lines = previous.splitlines(keepends=True)
        curr_lines = current.splitlines(keepends=True)
        unified = "".join(
            difflib.unified_diff(
                prev_lines,
                curr_lines,
                fromfile=f"{lib}/{srcpf}/{mbr} (previous)",
                tofile=f"{lib}/{srcpf}/{mbr} (current)",
                lineterm="",
            )
        )

    return DiffResult(
        lib=lib,
        srcpf=srcpf,
        mbr=mbr,
        unified_diff=unified,
        current_source=current,
        previous_source=previous,
    )


def commit_snapshot(result: DiffResult) -> None:
    """
    Persist the current source from a DiffResult as the new snapshot.

    Call this after the change has been accepted (tests pass, proposals
    accepted) so the next diff is taken against the correct baseline.

    Args:
        result: A ``DiffResult`` previously returned by ``diff_member()``.
    """
    save_snapshot(result.lib, result.srcpf, result.mbr, result.current_source)


def seed_snapshot(lib: str, srcpf: str, mbr: str) -> None:
    """
    Seed the snapshot store with the current source for a member that has
    never been snapshotted before.

    This is a convenience helper for the first-run case: it simply fetches
    the source and stores it without producing a diff.

    Args:
        lib:   Library name
        srcpf: Source physical file
        mbr:   Member name
    """
    if not snapshot_exists(lib, srcpf, mbr):
        source = get_source_member(lib, srcpf, mbr)
        save_snapshot(lib, srcpf, mbr, source)
