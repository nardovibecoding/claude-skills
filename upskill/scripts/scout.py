#!/usr/bin/env python3
"""
/upskill scout — lens-aware external candidate sweep via gh CLI.

Source plan: ~/.ship/upskill/goals/02-plan.md v2 §S2
Source spec: ~/.ship/upskill/goals/01-spec.md v2 §2 step 1, §5 R-Scout-Silent-Fail

Lens-aware (v2): consumes lens JSON from lens_resolve.py.
  - Standard mode: lens.keywords grouped (≤5 per gh search) + 1 call per gh_topic.
  - Menu mode (lens.menu_items present): one gh search per item, ≤5 items per call,
    priority-sorted (high before low).

Three valid outcomes per spec §5:
  - candidates returned (>=1)
  - scout_degraded=true (>=1 gh call failed, others may have succeeded)
  - scout_skipped="rate_limit_low"|"rate_limit_too_low" (pre-flight aborted)

Silent empty result is FORBIDDEN — always emit at least one of the above.

NO LLM. Rule-based filter only. Token budget <5K.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

RATE_LIMIT_MIN = 100  # v1 floor; v2 promotes to dynamic per-lens via 2x guard
KEYWORD_GROUP_SIZE = 5
MENU_ITEMS_PER_CALL = 5
SEARCH_LIMIT = 30
CANDIDATES_HARD_CAP = 200
SUMMARY_MAX = 200
INSTALLED_GLOB = os.path.expanduser("~/.claude/skills/*/SKILL.md")
GITHUB_URL_RE = re.compile(r"github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)")
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def run_gh(args: list[str], verbose: bool = False) -> tuple[int, str, str]:
    if verbose:
        print(f"[gh] {' '.join(args)}", file=sys.stderr)
    try:
        r = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=30)
        return r.returncode, r.stdout, r.stderr[:200]
    except subprocess.TimeoutExpired:
        return 124, "", "timeout 30s"
    except FileNotFoundError:
        return 127, "", "gh not found"


def load_installed_repos() -> set[str]:
    seen: set[str] = set()
    for fp in glob.glob(INSTALLED_GLOB):
        try:
            txt = Path(fp).read_text(errors="ignore")
        except Exception:
            continue
        for m in GITHUB_URL_RE.finditer(txt):
            owner, name = m.group(1).lower(), m.group(2).lower().rstrip(".git")
            seen.add(f"{owner}/{name}")
    return seen


def trunc(s: str | None, n: int = SUMMARY_MAX) -> str:
    if not s:
        return ""
    s = s.strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def chunked(lst: list, n: int) -> list[list]:
    return [lst[i : i + n] for i in range(0, len(lst), n)]


def match_keywords(text: str, keywords: list[str]) -> list[str]:
    """Case-insensitive substring match of keywords against text."""
    low = (text or "").lower()
    return [k for k in keywords if k.lower() in low]


def gh_search_repos(query: str, verbose: bool) -> tuple[int, list[dict], str]:
    """Returns (rc, rows, err_snippet)."""
    rc, out, err = run_gh(
        [
            "search",
            "repos",
            query,
            "--sort",
            "stars",
            "--limit",
            str(SEARCH_LIMIT),
            "--json",
            "fullName,description,stargazersCount,url,updatedAt,language",
        ],
        verbose,
    )
    if rc != 0:
        return rc, [], err.strip()
    try:
        rows = json.loads(out or "[]")
    except json.JSONDecodeError as e:
        return 1, [], f"json:{e}"
    return 0, rows, ""


def gh_search_topic(topic: str, verbose: bool) -> tuple[int, list[dict], str]:
    rc, out, err = run_gh(
        [
            "search",
            "repos",
            "--topic",
            topic,
            "--sort",
            "stars",
            "--limit",
            str(SEARCH_LIMIT),
            "--json",
            "fullName,description,stargazersCount,url,updatedAt,language",
        ],
        verbose,
    )
    if rc != 0:
        return rc, [], err.strip()
    try:
        rows = json.loads(out or "[]")
    except json.JSONDecodeError as e:
        return 1, [], f"json:{e}"
    return 0, rows, ""


def to_candidate(
    row: dict, keywords: list[str], source: str, topics_field: list[str] | None = None
) -> dict:
    full = row.get("fullName") or ""
    desc = row.get("description") or ""
    matched = match_keywords(f"{full} {desc}", keywords)
    return {
        "id": full.lower().replace("/", "-"),
        "name": full,
        "url": row.get("url"),
        "stars": row.get("stargazersCount", 0),
        "description": trunc(desc),
        "language": row.get("language"),
        "pushed_at": row.get("updatedAt"),
        "topics": topics_field or [],
        "matched_keywords": matched,
        "source": source,
    }


def preflight_rate_limit(verbose: bool) -> tuple[int | None, str]:
    """Return (remaining, err). remaining=None on failure."""
    rc, out, err = run_gh(["api", "rate_limit"], verbose)
    if rc != 0:
        return None, f"{rc}+{err.strip()}"
    try:
        body = json.loads(out)
    except json.JSONDecodeError as e:
        return None, f"json:{e}"
    # Search API has its own quota — use search.remaining since we use gh search.
    remaining = (
        body.get("resources", {}).get("search", {}).get("remaining")
    )
    if remaining is None:
        remaining = body.get("rate", {}).get("remaining", 0)
    return remaining, ""


def plan_standard(lens: dict) -> tuple[list[list[str]], list[str], int]:
    """Return (keyword_groups, gh_topics, expected_calls)."""
    keywords = list(lens.get("keywords", []))
    gh_topics = list(lens.get("gh_topics", []))
    groups = chunked(keywords, KEYWORD_GROUP_SIZE)
    expected = len(groups) + len(gh_topics)
    return groups, gh_topics, expected


def plan_menu(lens: dict) -> tuple[list[list[dict]], int]:
    """Return (item_batches sorted high→low priority, expected_calls)."""
    items = list(lens.get("menu_items", []))
    items.sort(key=lambda it: PRIORITY_ORDER.get(it.get("priority", "medium"), 1))
    batches = chunked(items, MENU_ITEMS_PER_CALL)
    return batches, math.ceil(len(items) / MENU_ITEMS_PER_CALL)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--lens",
        required=True,
        help="path to lens JSON file (output of lens_resolve.py)",
    )
    ap.add_argument("--out", required=True)
    ap.add_argument(
        "--mock-rate-limit",
        type=int,
        default=None,
        help="(test only) skip gh api rate_limit; use this remaining instead",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="skip gh search calls; emit empty candidates + reason='dry_run'",
    )
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    lens_path = Path(args.lens).expanduser()
    if not lens_path.exists():
        print(
            json.dumps({"error": f"lens file not found: {lens_path}"}),
            file=sys.stderr,
        )
        return 1
    lens = json.loads(lens_path.read_text())
    lens_name = lens.get("name", "unknown")
    is_menu_mode = bool(lens.get("menu_items"))

    out: dict[str, Any] = {
        "lens_name": lens_name,
        "candidates": [],
        "scout_degraded": False,
        "scout_skipped": None,
        "rate_limit_remaining": None,
        "calls_made": 0,
        "expected_calls": 0,
        "errors": [],
        "mode": "menu" if is_menu_mode else "standard",
    }

    # Plan
    if is_menu_mode:
        batches, expected = plan_menu(lens)
        out["expected_calls"] = expected
    else:
        groups, gh_topics, expected = plan_standard(lens)
        out["expected_calls"] = expected

    # Pre-flight rate-limit (BEFORE any gh search)
    if args.mock_rate_limit is not None:
        remaining = args.mock_rate_limit
    else:
        remaining, err = preflight_rate_limit(args.verbose)
        out["calls_made"] += 1
        if remaining is None:
            out["errors"].append({"source": "rate_limit", "error": err})
            out["scout_degraded"] = True
            remaining = 0
    out["rate_limit_remaining"] = remaining

    # Rate-limit guard
    if expected > 0 and remaining < expected:
        out["scout_skipped"] = "rate_limit_too_low"
        out["expected_calls"] = expected
        Path(args.out).expanduser().write_text(json.dumps(out, indent=2))
        print(
            json.dumps(
                {"skipped": "rate_limit_too_low", "remaining": remaining, "expected": expected}
            )
        )
        return 0

    halve = expected > 0 and remaining < (expected * 2)
    if halve:
        out["scout_skipped"] = "rate_limit_low"
        if is_menu_mode:
            half = max(1, math.ceil(len(batches) / 2))
            batches = batches[:half]
            out["expected_calls"] = sum(len(b) for b in [batches])  # placeholder
            out["expected_calls"] = len(batches)
        else:
            half_g = max(1, math.ceil(len(groups) / 2))
            groups = groups[:half_g]
            half_t = max(0, math.ceil(len(gh_topics) / 2))
            gh_topics = gh_topics[:half_t]
            out["expected_calls"] = len(groups) + len(gh_topics)

    if args.dry_run:
        out["scout_skipped"] = out["scout_skipped"] or "dry_run"
        Path(args.out).expanduser().write_text(json.dumps(out, indent=2))
        print(
            json.dumps(
                {
                    "candidates": 0,
                    "skipped": out["scout_skipped"],
                    "remaining": remaining,
                    "expected": out["expected_calls"],
                }
            )
        )
        return 0

    installed = load_installed_repos()
    keywords_for_match = list(lens.get("keywords", []))
    raw_candidates: list[dict] = []

    if is_menu_mode:
        # Menu mode: one gh search per BATCH of ≤5 items.
        # All items' keywords in the batch OR-joined into a single query.
        # Per spec §3: "Cap at 5 items per call (so 30-item menu = 6 calls)".
        for batch in batches:
            batch_keywords: list[str] = []
            ids: list[str] = []
            for item in batch:
                ks = item.get("keywords") or []
                batch_keywords.extend(ks)
                ids.append(str(item.get("id", item.get("name", "?"))))
            if not batch_keywords:
                continue
            # dedup preserving order
            seen_kw: set[str] = set()
            ordered = [k for k in batch_keywords if not (k in seen_kw or seen_kw.add(k))]
            query = " OR ".join(ordered)
            rc, rows, err = gh_search_repos(query, args.verbose)
            out["calls_made"] += 1
            src = f"menu_batch:{','.join(ids)[:60]}"
            if rc != 0:
                out["errors"].append({"source": src, "error": f"{rc}+{err}"})
                out["scout_degraded"] = True
                continue
            for r in rows:
                raw_candidates.append(
                    to_candidate(r, ordered + keywords_for_match, src)
                )
    else:
        for group in groups:
            if not group:
                continue
            query = " OR ".join(group)
            rc, rows, err = gh_search_repos(query, args.verbose)
            out["calls_made"] += 1
            src = f"keywords:{','.join(group)[:60]}"
            if rc != 0:
                out["errors"].append({"source": src, "error": f"{rc}+{err}"})
                out["scout_degraded"] = True
                continue
            for r in rows:
                raw_candidates.append(to_candidate(r, keywords_for_match, src))
        for topic in gh_topics:
            rc, rows, err = gh_search_topic(topic, args.verbose)
            out["calls_made"] += 1
            src = f"gh_topic:{topic}"
            if rc != 0:
                out["errors"].append({"source": src, "error": f"{rc}+{err}"})
                out["scout_degraded"] = True
                continue
            for r in rows:
                raw_candidates.append(to_candidate(r, keywords_for_match, src))

    # Dedup by name (case-insensitive), exclude installed.
    seen: dict[str, dict] = {}
    for c in raw_candidates:
        key = (c.get("name") or "").lower()
        if not key:
            continue
        if key in installed:
            continue
        if key in seen:
            # merge matched_keywords
            prev = seen[key]
            prev_set = set(prev.get("matched_keywords", []))
            prev_set.update(c.get("matched_keywords", []))
            prev["matched_keywords"] = sorted(prev_set)
            continue
        seen[key] = c

    candidates = list(seen.values())
    candidates = candidates[:CANDIDATES_HARD_CAP]
    out["candidates"] = candidates

    if out["errors"]:
        out["scout_degraded"] = True

    Path(args.out).expanduser().write_text(json.dumps(out, indent=2))
    print(
        json.dumps(
            {
                "lens_name": lens_name,
                "candidates": len(candidates),
                "degraded": out["scout_degraded"],
                "skipped": out["scout_skipped"],
                "rate_limit_remaining": remaining,
                "calls_made": out["calls_made"],
                "expected_calls": out["expected_calls"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
