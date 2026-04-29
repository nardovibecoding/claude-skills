#!/usr/bin/env python3
"""
memo-v2 terminal scribble entry point.

Usage:
  python3 scribble.py <body words...>

Parses #tag tokens (regex (?:^|\\s)#[a-z][a-z0-9-]{2,30}(?:$|\\s)), strips
them from body, calls _writer.write_memo(channel='terminal'). URL fragments
like https://x.com/foo#bar are NOT parsed as tags because the regex requires
whitespace boundary on the left.

Slice S4 of memo-v2. See ~/.ship/memo-v2/goals/01-spec.md §4.3.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _writer import write_memo  # noqa: E402

# Tag regex: leading boundary must be start-of-string OR whitespace.
# This excludes URL fragments where '#' follows non-whitespace (e.g. /page#frag).
# Tag itself: lowercase letter then 2-30 of [a-z0-9-], trailing boundary.
_TAG_RE = re.compile(r"(?:^|\s)#([a-z][a-z0-9-]{2,30})(?=\s|$)")


def _extract_tags(text: str) -> tuple[str, list[str]]:
    """Return (body_with_tags_removed, [tags...]).

    Tags must:
      - sit at line start or after whitespace
      - start with `#`, then lowercase letter, then 2-30 chars [a-z0-9-]
      - end at whitespace or end-of-string
    Multiple occurrences supported. Order preserved, dedup keeps first.
    """
    tags: list[str] = []
    seen: set[str] = set()
    for m in _TAG_RE.finditer(text):
        t = m.group(1)
        if t not in seen:
            seen.add(t)
            tags.append(t)

    # Strip the matched tag tokens (with the leading whitespace they consumed,
    # if any). We rebuild the body in one pass to avoid double-replacement
    # collisions when the same tag repeats.
    def _sub(match: re.Match) -> str:
        # Preserve any whitespace char that was in the leading boundary group
        # — re_TAG matches `(?:^|\s)#tag`. If the boundary was \s we keep one
        # space to avoid mashing words together; if start-of-string, drop entirely.
        leading = match.group(0)[: match.start(1) - match.start() - 1]  # chars before '#'
        return " " if leading else ""

    cleaned = _TAG_RE.sub(_sub, text)
    # Collapse multiple spaces created by removal, strip ends.
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip()
    return cleaned, tags


def main(argv: list[str]) -> int:
    if not argv:
        sys.stderr.write("usage: scribble.py <body...>\n")
        return 2
    raw_body = " ".join(argv).strip()
    if not raw_body:
        sys.stderr.write("scribble: empty body\n")
        return 2

    body, tags = _extract_tags(raw_body)
    if not body:
        # Body was 100% tag tokens. Keep them as the body so the memo isn't empty.
        body = raw_body

    path = write_memo(body=body, channel="terminal", tags=tags)

    # Confirmation line
    preview = body if len(body) <= 60 else body[:57] + "..."
    if tags:
        tag_str = " ".join(f"#{t}" for t in tags)
        print(f"memo saved: {preview}  [tags: {tag_str}]")
    else:
        print(f"memo saved: {preview}")
    print(f"  -> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
