"""
sentinel/store.py — Snapshot store for last-known-good source member text.

Snapshots are saved as plain text files under .sentinel_store/ in the repo
root, keyed by library, source physical file, and member name:

    .sentinel_store/<LIB>__<SRCPF>__<MBR>.rpgle

This lets the diff engine compare the current source member against the
version that was last recorded as clean (i.e. compiled successfully and
had all tests passing).
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Store location
# ---------------------------------------------------------------------------

_DEFAULT_STORE_DIR = Path(".sentinel_store")


def _store_dir() -> Path:
    """Return the store directory, creating it if it does not exist."""
    d = Path(os.environ.get("SENTINEL_STORE_DIR", str(_DEFAULT_STORE_DIR)))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _key(lib: str, srcpf: str, mbr: str) -> Path:
    """Return the file path for a given lib/srcpf/mbr triple."""
    filename = f"{lib.upper()}__{srcpf.upper()}__{mbr.upper()}.rpgle"
    return _store_dir() / filename


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_snapshot(lib: str, srcpf: str, mbr: str) -> str | None:
    """
    Return the stored snapshot text for a source member, or None if no
    snapshot exists yet.

    Args:
        lib:   Library name, e.g. ``"MYLIB"``
        srcpf: Source physical file, e.g. ``"QRPGLESRC"``
        mbr:   Member name, e.g. ``"ORDCALC"``

    Returns:
        The stored source text, or ``None`` if this member has never been
        snapshotted.
    """
    path = _key(lib, srcpf, mbr)
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def save_snapshot(lib: str, srcpf: str, mbr: str, source: str) -> None:
    """
    Save (or overwrite) the snapshot for a source member.

    Args:
        lib:    Library name
        srcpf:  Source physical file
        mbr:    Member name
        source: Full source text to store
    """
    path = _key(lib, srcpf, mbr)
    path.write_text(source, encoding="utf-8")


def snapshot_exists(lib: str, srcpf: str, mbr: str) -> bool:
    """Return True if a snapshot already exists for this member."""
    return _key(lib, srcpf, mbr).exists()


def list_snapshots() -> list[dict[str, str]]:
    """
    Return a list of all stored snapshots as dicts with keys
    ``lib``, ``srcpf``, ``mbr``.
    """
    results = []
    for path in sorted(_store_dir().glob("*.rpgle")):
        parts = path.stem.split("__")
        if len(parts) == 3:
            results.append({"lib": parts[0], "srcpf": parts[1], "mbr": parts[2]})
    return results
