#!/usr/bin/env python3
"""
memo-v2 diff renderer — `/memo --since N` 3-bucket activity view.

Buckets (per spec §5 + plan §2.7):
  - NEW: memos created in window with no prior memo sharing same body-fingerprint or any tag
  - RECURRING: memos in window that share >=1 tag with a memo created BEFORE window
  - RESOLVED: memos in window with `resolved` in tags

Per OQ3 (plan §2.7): include both pending/ AND done/ (diff is about activity, not status).

Slice S7 of memo-v2 ship. See ~/.ship/memo-v2/goals/01-spec.md §5 + 02-plan.md §2.7.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from index import load_index, build_index, INDEX_FILE  # noqa: E402


# --------------------------------------------------------------------------
# Body fingerprint (collapse whitespace/punctuation/URLs, lowercase, first 80)
# --------------------------------------------------------------------------
_URL_RE = re.compile(r"https?://\S+")
_NONALNUM_RE = re.compile(r"[^a-z0-9]+")


def _fingerprint(body: str) -> str:
    if not body:
        return ""
    s = _URL_RE.sub("", body.lower())
    s = _NONALNUM_RE.sub("", s)
    return s[:80]


# --------------------------------------------------------------------------
# ts parser — index ts is `YYYY-MM-DD HH:MM` (16 chars) per S1 output
# --------------------------------------------------------------------------
def _parse_ts_safe(ts: str) -> datetime | None:
    """Try 19-char then 16-char ISO-ish parse."""
    if not ts:
        return None
    s = ts.strip()
    try:
        return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        pass
    try:
        return datetime.strptime(s[:16], "%Y-%m-%d %H:%M")
    except ValueError:
        return None


# --------------------------------------------------------------------------
# Core
# --------------------------------------------------------------------------
def since_diff(days: int, include_archived: bool = True) -> dict:
    """Return {'new': [...], 'recurring': [...], 'resolved': [...]}.

    `days` = window size (positive int). `include_archived=True` keeps done/ memos.
    Each list is newest-first, full row dicts as stored in _index.jsonl.
    """
    if not INDEX_FILE.exists():
        build_index()

    rows = load_index()
    if not include_archived:
        rows = [r for r in rows if r.get("status") != "done"]

    cutoff = datetime.utcnow() - timedelta(days=days)

    in_window: list[dict] = []
    before_window: list[dict] = []
    for r in rows:
        dt = _parse_ts_safe(r.get("ts") or "")
        if dt is None:
            continue
        if dt >= cutoff:
            in_window.append(r)
        else:
            before_window.append(r)

    # Tag set + fingerprint set seen BEFORE window
    prior_tags: set[str] = set()
    prior_fps: set[str] = set()
    for r in before_window:
        for t in r.get("tags") or []:
            if t:
                prior_tags.add(str(t).lower())
        fp = _fingerprint(r.get("body_preview") or "")
        if fp:
            prior_fps.add(fp)

    new_bucket: list[dict] = []
    recurring_bucket: list[dict] = []
    resolved_bucket: list[dict] = []

    for r in in_window:
        tags = {str(t).lower() for t in (r.get("tags") or []) if t}
        if "resolved" in tags:
            resolved_bucket.append(r)
            continue
        # RECURRING if any tag matches a prior tag
        if tags & prior_tags:
            recurring_bucket.append(r)
            continue
        # Otherwise NEW (also check fingerprint not seen before — duplicate body
        # means the topic is recurring even without tag overlap)
        fp = _fingerprint(r.get("body_preview") or "")
        if fp and fp in prior_fps:
            recurring_bucket.append(r)
        else:
            new_bucket.append(r)

    # newest-first within each bucket
    def _ts_key(r: dict) -> str:
        return r.get("ts") or ""

    for b in (new_bucket, recurring_bucket, resolved_bucket):
        b.sort(key=_ts_key, reverse=True)

    return {"new": new_bucket, "recurring": recurring_bucket, "resolved": resolved_bucket}


# --------------------------------------------------------------------------
# Render
# --------------------------------------------------------------------------
def _hkt(ts: str) -> str:
    dt = _parse_ts_safe(ts)
    if dt is None:
        return ts[:16]
    dt += timedelta(hours=8)
    return dt.strftime("%m-%d %H:%M")


def _render_row(r: dict) -> str:
    when = _hkt(r.get("ts") or "")
    status = "PENDING" if r.get("status") == "pending" else "done"
    tags = ",".join(f"#{t}" for t in r.get("tags") or [])
    body = (r.get("body_preview") or "").replace("|", "\\|")[:60]
    return f"| {when:<12} | {status:<7} | {tags:<20} | {body} |"


def render(buckets: dict, days: int) -> str:
    lines: list[str] = []
    lines.append(f"## /memo --since {days}d  (HKT)")
    lines.append("")
    for label_key, header in (("new", "NEW"), ("recurring", "RECURRING"), ("resolved", "RESOLVED")):
        rows = buckets.get(label_key) or []
        lines.append(f"### {header} ({len(rows)})")
        if not rows:
            lines.append("(none)")
        else:
            lines.append("| When (HKT)   | Status  | Tags                 | Content |")
            lines.append("|--------------|---------|----------------------|---------|")
            for r in rows:
                lines.append(_render_row(r))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def _parse_days(raw: str) -> int:
    s = raw.strip().lower().rstrip("d")
    if not s:
        raise ValueError("empty days")
    if not s.isdigit():
        raise ValueError(f"not numeric: {raw!r}")
    n = int(s)
    if n <= 0:
        raise ValueError(f"days must be > 0 (got {n})")
    return n


def _main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="memo-v2 --since N diff renderer")
    p.add_argument("--since", default="7d", help="window in days (e.g. 7d, 30, 14d). Default 7d.")
    p.add_argument("--no-archived", action="store_true", help="exclude done/ memos (default: include)")
    args = p.parse_args(argv)

    try:
        days = _parse_days(args.since)
    except ValueError as e:
        sys.stderr.write(f"error: invalid --since value: {e}\n")
        sys.stderr.write("usage: /memo --since 7d   (or --since 30d)\n")
        return 2

    buckets = since_diff(days=days, include_archived=not args.no_archived)
    sys.stdout.write(render(buckets, days))
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
