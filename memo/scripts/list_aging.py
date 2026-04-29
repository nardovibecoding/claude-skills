#!/usr/bin/env python3
"""
memo-v2 S6: list aging memos for /daemons OPEN SCRIBBLES render.

Returns memos with status=pending, no #resolved tag, age > threshold_days.
Sorted oldest-first (most aged surfaces first), capped at limit.

Consumed by ~/.claude/hooks/inbox_hook.py:_format_bundle_digest via subprocess
(NOT direct import — keeps hook lean and lets us swap memo backend later).

Slice S6 of memo-v2 ship. See ~/.ship/memo-v2/goals/01-spec.md §6.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Make sibling index module importable when run as script
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import index  # noqa: E402  — sibling module after sys.path injection


_DEFAULT_THRESHOLD_DAYS = 7
_DEFAULT_LIMIT = 10
_PREVIEW_LEN = 60


def _parse_ts(ts: str) -> datetime | None:
    """Parse 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD HH:MM' → datetime; None on fail."""
    if not ts:
        return None
    s = ts.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def list_aging(
    threshold_days: int = _DEFAULT_THRESHOLD_DAYS,
    limit: int = _DEFAULT_LIMIT,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Return memos older than threshold_days, status=pending, not resolved.

    Each entry: {file, ts_age_days, tags, body_preview}
    Sorted oldest-first; capped at `limit`.

    The full count (pre-cap) is returned in the row dict via attribute on the
    list — callers wanting "+N more" should call list_aging_with_total instead.
    """
    rows, _total = list_aging_with_total(threshold_days, limit, now)
    return rows


def list_aging_with_total(
    threshold_days: int = _DEFAULT_THRESHOLD_DAYS,
    limit: int = _DEFAULT_LIMIT,
    now: datetime | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Same as list_aging but also returns total qualifying count (pre-cap).

    Returns (capped_rows, total_qualifying).
    """
    now = now or datetime.now()
    try:
        all_rows = index.load_index()
    except Exception:
        return [], 0

    qualifying: list[tuple[float, dict[str, Any]]] = []
    for r in all_rows:
        # Status filter — parent dir is ground truth (S1 §5.5)
        if r.get("status") != "pending":
            continue
        # Resolved filter — case-insensitive, lstripped of '#' by S1 normalizer
        tags_raw = r.get("tags") or []
        tags_lower = {str(t).lower().lstrip("#") for t in tags_raw}
        if "resolved" in tags_lower:
            continue
        # Age filter
        ts_dt = _parse_ts(r.get("ts") or "")
        if ts_dt is None:
            continue
        age = (now - ts_dt).total_seconds() / 86400.0
        if age <= threshold_days:
            continue
        qualifying.append((age, r))

    # Oldest-first: largest age first
    qualifying.sort(key=lambda pair: pair[0], reverse=True)
    total = len(qualifying)

    out: list[dict[str, Any]] = []
    for age, r in qualifying[:limit]:
        primary_tag = ""
        for t in (r.get("tags") or []):
            if t:
                primary_tag = str(t).lstrip("#").lower()
                break
        body_preview = (r.get("body_preview") or "")[:_PREVIEW_LEN].strip()
        out.append({
            "file": r.get("file", ""),
            "ts_age_days": int(age),
            "tags": list(r.get("tags") or []),
            "primary_tag": primary_tag,
            "body_preview": body_preview,
        })
    return out, total


def _main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="list aging memos as JSON")
    p.add_argument("--threshold", type=int, default=_DEFAULT_THRESHOLD_DAYS,
                   help=f"age threshold in days (default {_DEFAULT_THRESHOLD_DAYS})")
    p.add_argument("--limit", type=int, default=_DEFAULT_LIMIT,
                   help=f"max rows (default {_DEFAULT_LIMIT})")
    p.add_argument("--with-total", action="store_true",
                   help="emit {rows, total} envelope for +N-more rendering")
    args = p.parse_args(argv)

    rows, total = list_aging_with_total(args.threshold, args.limit)
    if args.with_total:
        print(json.dumps({"rows": rows, "total": total}, ensure_ascii=False))
    else:
        print(json.dumps(rows, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
