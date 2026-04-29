#!/usr/bin/env python3
"""
memo-v2 index builder + query engine.

Scans ~/telegram-claude-bot/memo/{pending,done}/*.md, parses frontmatter
into JSONL at ~/telegram-claude-bot/memo/_index.jsonl. Lock-guarded writes
via fcntl.flock (pattern: ~/NardoWorld/scripts/bigd/_lib/collector.py).

Slice S1 of memo-v2 ship. See ~/.ship/memo-v2/goals/01-spec.md.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
MEMO_ROOT = Path.home() / "telegram-claude-bot" / "memo"
PENDING_DIR = MEMO_ROOT / "pending"
DONE_DIR = MEMO_ROOT / "done"
INDEX_FILE = MEMO_ROOT / "_index.jsonl"
LOCK_FILE = MEMO_ROOT / ".index.lock"

# Filename schema: YYYY-MM-DD_HHMMSS[_<channel>].md
_FILENAME_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})_(?P<time>\d{6})(?:_(?P<channel>[a-z0-9_-]+))?\.md$"
)
_BODY_PREVIEW_LEN = 80


# --------------------------------------------------------------------------
# Frontmatter parsing
# --------------------------------------------------------------------------
def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split a memo file into (frontmatter_dict, body_text).

    Frontmatter is the YAML-ish block bounded by `---` lines at top of file.
    We support the subset used by _save_memo: scalar `key: value` pairs,
    plus list values written as `[a, b, c]`. Missing frontmatter -> ({}, text).
    """
    if not text.startswith("---"):
        return {}, text.strip()

    lines = text.splitlines()
    if len(lines) < 2:
        return {}, text.strip()

    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return {}, text.strip()

    fm: dict[str, Any] = {}
    for raw in lines[1:end_idx]:
        if ":" not in raw:
            continue
        k, _, v = raw.partition(":")
        k = k.strip()
        v = v.strip()
        if not k:
            continue
        # list value `[a, b, c]`
        if v.startswith("[") and v.endswith("]"):
            inner = v[1:-1].strip()
            if not inner:
                fm[k] = []
            else:
                fm[k] = [item.strip().strip("'\"") for item in inner.split(",") if item.strip()]
        else:
            fm[k] = v

    body = "\n".join(lines[end_idx + 1:]).strip()
    return fm, body


def _ts_from_filename(name: str) -> str | None:
    """Return ISO-ish ts string `YYYY-MM-DD HH:MM:SS` from filename, or None."""
    m = _FILENAME_RE.match(name)
    if not m:
        return None
    date = m.group("date")
    t = m.group("time")
    return f"{date} {t[0:2]}:{t[2:4]}:{t[4:6]}"


def _channel_from_filename(name: str) -> str | None:
    m = _FILENAME_RE.match(name)
    return m.group("channel") if m else None


def parse_memo(path: Path) -> dict[str, Any]:
    """Parse a single memo file into a dict.

    Returns: {file, ts, from, type, tags, status, body, body_preview, path, channel}
    Backward compat: missing `tags` -> []. Tags are normalized to lowercase.
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    fm, body = _parse_frontmatter(text)

    # ts: prefer frontmatter `created`, fallback to filename
    ts = fm.get("created") or _ts_from_filename(path.name) or ""

    # tags normalization
    raw_tags = fm.get("tags", [])
    if isinstance(raw_tags, str):
        # tolerate `tags: drift` (single string)
        raw_tags = [raw_tags]
    if not isinstance(raw_tags, list):
        raw_tags = []
    tags = [str(t).strip().lstrip("#").lower() for t in raw_tags if str(t).strip()]

    channel = fm.get("channel") or _channel_from_filename(path.name) or ""

    body_preview = body[:_BODY_PREVIEW_LEN].replace("\n", " ")

    return {
        "file": path.name,
        "path": str(path),
        "ts": ts,
        "from": fm.get("from", ""),
        "type": fm.get("type", ""),
        "tags": tags,
        "status": fm.get("status", "pending" if path.parent.name == "pending" else "done"),
        "channel": channel,
        "source": fm.get("source", ""),
        "body": body,
        "body_preview": body_preview,
    }


# --------------------------------------------------------------------------
# Index builder + updater
# --------------------------------------------------------------------------
def _iter_memo_files() -> Iterable[Path]:
    for d in (PENDING_DIR, DONE_DIR):
        if not d.exists():
            continue
        for p in sorted(d.glob("*.md")):
            yield p


def _to_index_dict(parsed: dict[str, Any]) -> dict[str, Any]:
    """Drop heavy `body` field for index storage; keep body_preview."""
    out = dict(parsed)
    out.pop("body", None)
    return out


def _acquire_lock():
    """Open + flock LOCK_FILE EX. Caller must close fd."""
    MEMO_ROOT.mkdir(parents=True, exist_ok=True)
    fd = open(LOCK_FILE, "w")
    fcntl.flock(fd, fcntl.LOCK_EX)
    return fd


def _release_lock(fd) -> None:
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        fd.close()


def build_index() -> Path:
    """Full rebuild: scan all memos, write fresh JSONL atomically."""
    MEMO_ROOT.mkdir(parents=True, exist_ok=True)
    lock_fd = _acquire_lock()
    try:
        tmp = INDEX_FILE.with_suffix(".jsonl.tmp")
        with tmp.open("w", encoding="utf-8") as f:
            for path in _iter_memo_files():
                try:
                    parsed = parse_memo(path)
                except Exception as e:
                    sys.stderr.write(f"parse failed: {path}: {e}\n")
                    continue
                f.write(json.dumps(_to_index_dict(parsed), ensure_ascii=False) + "\n")
        os.replace(tmp, INDEX_FILE)
    finally:
        _release_lock(lock_fd)
    return INDEX_FILE


def update_index(memo_path: Path) -> None:
    """Append a single memo's parsed dict to the index JSONL.

    Lock-guarded. If index does not exist, falls back to build_index().
    """
    memo_path = Path(memo_path)
    if not INDEX_FILE.exists():
        build_index()
        return
    parsed = parse_memo(memo_path)
    line = json.dumps(_to_index_dict(parsed), ensure_ascii=False) + "\n"
    lock_fd = _acquire_lock()
    try:
        with INDEX_FILE.open("a", encoding="utf-8") as f:
            f.write(line)
    finally:
        _release_lock(lock_fd)


def load_index() -> list[dict[str, Any]]:
    """Read _index.jsonl. Lazy-init via build_index() if missing."""
    if not INDEX_FILE.exists():
        build_index()
    rows: list[dict[str, Any]] = []
    if not INDEX_FILE.exists():
        return rows
    with INDEX_FILE.open("r", encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            try:
                rows.append(json.loads(ln))
            except json.JSONDecodeError:
                continue
    return rows


# --------------------------------------------------------------------------
# Query
# --------------------------------------------------------------------------
def _ts_key(row: dict[str, Any]) -> str:
    return row.get("ts") or ""


def query_index(
    tags: list[str] | None = None,
    since: str | None = None,
    search: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Filter the index. Newest-first.

    - tags: list of lowercase tags; row matches if any tag is in row['tags'].
    - since: ISO-ish ts string `YYYY-MM-DD HH:MM:SS` (or prefix); row.ts >= since.
    - search: case-insensitive substring match against body_preview OR from.
    - limit: max rows.
    """
    rows = load_index()
    tag_set = {t.lower() for t in tags} if tags else None
    needle = search.lower() if search else None

    out: list[dict[str, Any]] = []
    for r in rows:
        if tag_set is not None:
            row_tags = {str(t).lower() for t in (r.get("tags") or [])}
            if not (tag_set & row_tags):
                continue
        if since is not None:
            if (r.get("ts") or "") < since:
                continue
        if needle is not None:
            haystack = (r.get("body_preview", "") + " " + r.get("from", "")).lower()
            if needle not in haystack:
                continue
        out.append(r)

    out.sort(key=_ts_key, reverse=True)
    return out[:limit]


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def _main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="memo-v2 index builder/query")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--build", action="store_true", help="full rebuild of _index.jsonl")
    g.add_argument("--update", metavar="PATH", help="append one memo file to index")
    g.add_argument("--query", action="store_true", help="run a query (use --tag/--search/--since/--limit)")
    p.add_argument("--tag", action="append", default=[], help="filter by tag (repeatable)")
    p.add_argument("--search", default=None, help="substring search")
    p.add_argument("--since", default=None, help="ts prefix YYYY-MM-DD[ HH:MM:SS]")
    p.add_argument("--limit", type=int, default=5)
    args = p.parse_args(argv)

    if args.build:
        out = build_index()
        rows = load_index()
        print(f"built {out} ({len(rows)} memos)")
        return 0
    if args.update:
        update_index(Path(args.update))
        print(f"appended {args.update}")
        return 0
    if args.query:
        results = query_index(
            tags=args.tag or None,
            since=args.since,
            search=args.search,
            limit=args.limit,
        )
        for r in results:
            print(json.dumps(r, ensure_ascii=False))
        return 0
    p.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
