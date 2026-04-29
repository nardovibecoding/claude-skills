#!/usr/bin/env python3
"""
memo-v2 shared frontmatter writer.

Used by S4 (terminal scribble) and S5 (email poller) to write a memo file
into ~/telegram-claude-bot/memo/pending/ with the canonical frontmatter
shape. After write, calls index.update_index(path) so the JSONL index stays
fresh.

DO NOT redirect telegram-channel writes here — TG admin_bot owns that path
via memo_handler._save_memo. This helper is for terminal + email channels
that share the Mac-side write path.

Slice S4 of memo-v2 ship. See ~/.ship/memo-v2/goals/01-spec.md §4.3 +
goals/02-plan.md §6 Sh1.
"""
from __future__ import annotations

import fcntl
import os
import sys
from datetime import datetime
from pathlib import Path

# Reuse paths from index.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from index import PENDING_DIR, MEMO_ROOT, LOCK_FILE, update_index  # noqa: E402

# Channel suffix map. TG path stays in memo_handler._save_memo (no suffix).
CHANNEL_SUFFIX = {
    "terminal": "_terminal",
    "email": "_email",
    "telegram": "",  # reserved — TG bot owns this; do not call write_memo with channel='telegram'
}


def _format_tags(tags: list[str]) -> str:
    """Render `tags: [a, b, c]` (or `tags: []` when empty)."""
    if not tags:
        return "tags: []"
    inner = ", ".join(t.strip().lstrip("#").lower() for t in tags if t and t.strip())
    if not inner:
        return "tags: []"
    return f"tags: [{inner}]"


def _acquire_writer_lock():
    """Reuse index.py lock file to serialize writers vs indexers."""
    MEMO_ROOT.mkdir(parents=True, exist_ok=True)
    fd = open(LOCK_FILE, "w")
    fcntl.flock(fd, fcntl.LOCK_EX)
    return fd


def _release_writer_lock(fd) -> None:
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        fd.close()


def write_memo(
    body: str,
    *,
    channel: str,
    source: str = "",
    memo_type: str = "general",
    tags: list[str] | None = None,
) -> Path:
    """Write a memo file + update index. Returns the written Path.

    Args:
      body: memo body (already stripped of #tag tokens)
      channel: 'terminal' or 'email' — selects filename suffix
      source: optional sender (e.g. email From: address)
      memo_type: frontmatter `type:` field; defaults to 'general'
      tags: list of lowercase tag strings (no leading #)

    Filename: YYYY-MM-DD_HHMMSS_<suffix>.md (microsecond fallback if collision)
    Frontmatter: from / type / created / status / tags + optional source
    """
    if channel == "telegram":
        raise ValueError(
            "write_memo: channel='telegram' is owned by memo_handler._save_memo; "
            "do not redirect TG writes through this helper"
        )
    suffix = CHANNEL_SUFFIX.get(channel)
    if suffix is None:
        raise ValueError(f"write_memo: unknown channel {channel!r}")

    tags = tags or []
    PENDING_DIR.mkdir(parents=True, exist_ok=True)

    ts = datetime.now()
    base = ts.strftime("%Y-%m-%d_%H%M%S")
    fm_lines = [
        "---",
        f"from: {channel}",
        f"type: {memo_type}",
        f"created: {ts.strftime('%Y-%m-%d %H:%M')}",
        "status: pending",
        _format_tags(tags),
    ]
    if source:
        fm_lines.append(f"source: {source}")
    fm_lines.append("---")
    content = "\n".join(fm_lines) + "\n" + (body.rstrip() + "\n")

    # Filename collision-resolution must happen INSIDE the lock — otherwise
    # two concurrent writers can both check `not path.exists()` simultaneously
    # and clobber each other.
    lock_fd = _acquire_writer_lock()
    try:
        filename = f"{base}{suffix}.md"
        path = PENDING_DIR / filename
        if path.exists():
            # Microsecond suffix breaks intra-second collisions (R2 in spec).
            filename = f"{base}_{ts.strftime('%f')}{suffix}.md"
            path = PENDING_DIR / filename
            # Defensive: if even microsecond collides (vanishingly rare), use os.O_EXCL loop.
            attempt = 0
            while path.exists() and attempt < 100:
                attempt += 1
                filename = f"{base}_{ts.strftime('%f')}_{attempt}{suffix}.md"
                path = PENDING_DIR / filename
        # Use exclusive create to slam the door on any racy lookup we missed.
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
    finally:
        _release_writer_lock(lock_fd)

    # update_index has its own flock on the same LOCK_FILE; called outside our
    # lock window to avoid re-entrant flock. macOS LOCK_EX is per-fd so
    # re-acquiring from the same process would block.
    try:
        update_index(path)
    except Exception as e:
        sys.stderr.write(f"write_memo: update_index failed for {path}: {e}\n")

    return path


__all__ = ["write_memo", "CHANNEL_SUFFIX"]
