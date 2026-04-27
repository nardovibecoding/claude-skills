#!/usr/bin/env python3
"""
/upskill scout — external candidate sweep via gh CLI.

Source plan: ~/.ship/upskill/goals/02-plan.md §S4
Source spec: ~/.ship/upskill/goals/01-spec.md §2 step 1, §5 R-Scout-Silent-Fail

Three valid outcomes per spec §5:
  - candidates returned (>=1)
  - scout_degraded=true (>=1 gh call failed, others may have succeeded)
  - scout_skipped="rate_limit_low" (pre-flight aborted)

Silent empty result is FORBIDDEN — always emit at least one of the above.

NO LLM in v1. Rule-based filter only. Token budget <5K.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_TOPICS = ["claude-code", "ai-agent", "mcp", "llm-cli"]
RATE_LIMIT_MIN = 100
TOPIC_LIMIT = 10
SUMMARY_MAX = 200
INSTALLED_GLOB = os.path.expanduser("~/.claude/skills/*/SKILL.md")
GITHUB_URL_RE = re.compile(r"github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)")


def run_gh(args: list[str], verbose: bool = False) -> tuple[int, str, str]:
    """Run gh; return (rc, stdout, stderr_snippet)."""
    if verbose:
        print(f"[gh] {' '.join(args)}", file=sys.stderr)
    try:
        r = subprocess.run(
            ["gh", *args], capture_output=True, text=True, timeout=20
        )
        return r.returncode, r.stdout, r.stderr[:200]
    except subprocess.TimeoutExpired:
        return 124, "", "timeout 20s"
    except FileNotFoundError:
        return 127, "", "gh not found"


def load_installed_repos() -> set[str]:
    """Set of 'owner/name' lowercase strings already referenced in installed SKILL.md files."""
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


def scout_topic(
    topic: str, installed: set[str], errors: list[dict], verbose: bool
) -> tuple[list[dict], int]:
    """Return (candidates, call_count) for one topic."""
    src = f"github_topic_{topic}"
    rc, out, err = run_gh(
        [
            "search",
            "repos",
            "--topic",
            topic,
            "--sort",
            "stars",
            "--limit",
            str(TOPIC_LIMIT),
            "--json",
            "fullName,description,stargazersCount,url,updatedAt",
        ],
        verbose,
    )
    if rc != 0:
        errors.append({"source": src, "error": f"{rc}+{err.strip()}"})
        return [], 1
    try:
        rows = json.loads(out or "[]")
    except json.JSONDecodeError as e:
        errors.append({"source": src, "error": f"json:{e}"})
        return [], 1
    cands = []
    for r in rows:
        full = (r.get("fullName") or "").lower()
        if full in installed:
            continue
        cands.append(
            {
                "source": src,
                "name": r.get("fullName"),
                "url": r.get("url"),
                "stars": r.get("stargazersCount", 0),
                "updated_at": r.get("updatedAt"),
                "summary": trunc(r.get("description")),
            }
        )
    return cands, 1


def scout_anthropic_releases(
    errors: list[dict], verbose: bool
) -> tuple[list[dict], int]:
    src = "anthropic_releases"
    rc, out, err = run_gh(
        [
            "api",
            "repos/anthropics/claude-code/releases?per_page=5",
            "--jq",
            ".[]|{tag:.tag_name,name:.name,published_at:.published_at,url:.html_url}",
        ],
        verbose,
    )
    if rc != 0:
        errors.append({"source": src, "error": f"{rc}+{err.strip()}"})
        return [], 1
    cands = []
    for line in (out or "").strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rel = json.loads(line)
        except json.JSONDecodeError:
            continue
        cands.append(
            {
                "source": src,
                "name": f"anthropics/claude-code@{rel.get('tag')}",
                "url": rel.get("url"),
                "stars": 0,
                "updated_at": rel.get("published_at"),
                "summary": trunc(rel.get("name")),
            }
        )
    return cands, 1


def scout_awesome_skills(
    installed: set[str], errors: list[dict], verbose: bool
) -> tuple[list[dict], int]:
    src = "awesome_skills"
    rc, out, err = run_gh(
        [
            "api",
            "repos/anthropics/skills/contents/skills",
            "--jq",
            ".[]|{name:.name,url:.html_url,type:.type}",
        ],
        verbose,
    )
    if rc != 0:
        errors.append({"source": src, "error": f"{rc}+{err.strip()}"})
        return [], 1
    cands = []
    for line in (out or "").strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            it = json.loads(line)
        except json.JSONDecodeError:
            continue
        if it.get("type") != "dir":
            continue
        full = f"anthropics/skills#{it.get('name', '').lower()}"
        if full in installed:
            continue
        cands.append(
            {
                "source": src,
                "name": f"anthropics/skills/{it.get('name')}",
                "url": it.get("url"),
                "stars": 0,
                "updated_at": None,
                "summary": trunc(f"Anthropic catalog skill: {it.get('name')}"),
            }
        )
    return cands, 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry-run", action="store_true",
                    help="run only first topic + skip releases/awesome")
    ap.add_argument("--topics", default=",".join(DEFAULT_TOPICS))
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    out: dict[str, Any] = {
        "rate_limit_remaining": None,
        "scout_skipped": None,
        "scout_degraded": False,
        "candidates": [],
        "errors": [],
        "call_count": 0,
        "sources": [],
    }

    # Pre-flight rate limit
    rc, body, err = run_gh(["api", "rate_limit"], args.verbose)
    out["call_count"] += 1
    if rc != 0:
        out["errors"].append({"source": "rate_limit", "error": f"{rc}+{err.strip()}"})
        out["scout_degraded"] = True
        out["rate_limit_remaining"] = -1
    else:
        try:
            rl = json.loads(body)
            remaining = (
                rl.get("resources", {}).get("core", {}).get("remaining")
                or rl.get("rate", {}).get("remaining")
                or 0
            )
            out["rate_limit_remaining"] = remaining
            if remaining < RATE_LIMIT_MIN:
                out["scout_skipped"] = "rate_limit_low"
                Path(args.out).write_text(json.dumps(out, indent=2))
                print(json.dumps({"skipped": True, "remaining": remaining}))
                return 0
        except json.JSONDecodeError as e:
            out["errors"].append({"source": "rate_limit", "error": f"json:{e}"})
            out["scout_degraded"] = True

    topics = [t.strip() for t in args.topics.split(",") if t.strip()]
    if args.dry_run:
        topics = topics[:1]

    installed = load_installed_repos()

    # Topic searches
    for t in topics:
        out["sources"].append(f"github_topic_{t}")
        cands, n = scout_topic(t, installed, out["errors"], args.verbose)
        out["candidates"].extend(cands)
        out["call_count"] += n

    # Anthropic releases (skip in dry-run)
    if not args.dry_run:
        out["sources"].append("anthropic_releases")
        cands, n = scout_anthropic_releases(out["errors"], args.verbose)
        out["candidates"].extend(cands)
        out["call_count"] += n

        out["sources"].append("awesome_skills")
        cands, n = scout_awesome_skills(installed, out["errors"], args.verbose)
        out["candidates"].extend(cands)
        out["call_count"] += n

    if out["errors"]:
        out["scout_degraded"] = True

    Path(args.out).write_text(json.dumps(out, indent=2))
    print(
        json.dumps(
            {
                "candidates": len(out["candidates"]),
                "degraded": out["scout_degraded"],
                "rate_limit_remaining": out["rate_limit_remaining"],
                "call_count": out["call_count"],
                "errors": len(out["errors"]),
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
