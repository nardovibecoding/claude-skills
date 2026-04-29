#!/usr/bin/env python3
"""score.py — /upskill v2 intrinsic ROI ranker (replaces v1 rank.py).

Spec: ~/.ship/upskill/goals/01-spec.md §3 (locked).
Inputs: scout JSON (from scout.py) + lens JSON (from lens_resolve.py).
Output: ranked candidates JSON + stdout table.

Formula (verbatim from spec:107-126):
  impact = stars_tier*w_stars + recency*w_recency + kw_fit*w_kw_fit + lang_match*w_lang
  cost   = base_cost[lens.integration_cost_model]    # multipliers=1.0 in v2 (deferred to v3)
  ROI    = impact / cost
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Base costs (hours) — spec:124-127. v2 multipliers=1.0; v3 will calibrate.
BASE_COST_HOURS = {
    "skills": 2,
    "code":   4,
    "infra":  8,
}

CO_TIED_WINDOW = 0.10  # spec:129 — top-2 within 10% → co_tied_top: true


def _stars_tier(stars) -> int:
    """Carry-over from v1 rank.py:254-262 (`_stars_tier`).

    impact tier: 3 if stars>5000, 2 if stars>1000, else 1.
    """
    if not isinstance(stars, (int, float)):
        return 1
    if stars > 5_000:
        return 3
    if stars > 1_000:
        return 2
    return 1


def _recency_score(pushed_at: str | None, now: datetime) -> float:
    """1.0 if <30d, 0.5 if <180d, 0.1 else. Spec:111."""
    if not pushed_at:
        return 0.1
    try:
        ts = pushed_at.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return 0.1
    days = (now - dt).total_seconds() / 86400.0
    if days < 30:
        return 1.0
    if days < 180:
        return 0.5
    return 0.1


def _keyword_fit(matched: list, total_keywords: int) -> float:
    if total_keywords <= 0:
        return 0.0
    score = len(matched) / total_keywords
    return min(score, 1.0)


def _language_match(candidate_lang: str | None, lens_lang: str | None) -> float:
    """1.0 if match, 0.3 otherwise. If lens has no lang → 1.0 (no penalty). Spec:113."""
    if not lens_lang:
        return 1.0
    if not candidate_lang:
        return 0.3
    allowed = {x.strip().lower() for x in lens_lang.split("|") if x.strip()}
    return 1.0 if candidate_lang.lower() in allowed else 0.3


def _ia_category(candidate: dict) -> str:
    """Carry from v1 rank.py:_norm_scout (lines 275-286).

    All scout-sourced candidates → ADOPT-EXT in v1 (only category for external repos).
    v2 candidates all come from scout, so all are ADOPT-EXT.
    """
    return "ADOPT-EXT"


def _load_json(path: str) -> dict:
    p = Path(path).expanduser()
    if not p.exists():
        print(f"score: ERROR: {path} not found", file=sys.stderr)
        sys.exit(1)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"score: ERROR: failed to parse {path}: {exc}", file=sys.stderr)
        sys.exit(1)


def _validate_lens(lens: dict) -> None:
    for key in ("name", "keywords", "scoring_weights", "integration_cost_model"):
        if key not in lens:
            print(f"score: ERROR: lens missing key '{key}'", file=sys.stderr)
            sys.exit(1)
    if lens["integration_cost_model"] not in BASE_COST_HOURS:
        print(
            f"score: ERROR: integration_cost_model='{lens['integration_cost_model']}' "
            f"not in {sorted(BASE_COST_HOURS)}",
            file=sys.stderr,
        )
        sys.exit(1)


def _validate_scout(scout: dict) -> None:
    if "candidates" not in scout:
        print("score: ERROR: scout missing 'candidates'", file=sys.stderr)
        sys.exit(1)
    if not isinstance(scout["candidates"], list):
        print("score: ERROR: scout.candidates must be list", file=sys.stderr)
        sys.exit(1)


def score(scout: dict, lens: dict, top_n: int, now: datetime | None = None) -> dict:
    if now is None:
        now = datetime.now(timezone.utc)
    weights = lens["scoring_weights"]
    w_stars = float(weights["stars"])
    w_recency = float(weights["recency"])
    w_kw = float(weights["keyword_fit"])
    w_lang = float(weights["language_match"])
    total_keywords = len(lens.get("keywords", []))
    lens_lang = lens.get("lang")
    cost_model = lens["integration_cost_model"]
    cost_hours = BASE_COST_HOURS[cost_model]

    ranked = []
    for c in scout.get("candidates", []):
        if not isinstance(c, dict):
            continue
        stars = c.get("stars") or 0
        st_tier = _stars_tier(stars)
        rec = _recency_score(c.get("pushed_at"), now)
        kw_fit = _keyword_fit(c.get("matched_keywords", []) or [], total_keywords)
        lang = _language_match(c.get("language"), lens_lang)
        impact = (st_tier * w_stars + rec * w_recency + kw_fit * w_kw + lang * w_lang)
        roi = impact / cost_hours

        ranked.append({
            "id": c.get("id") or c.get("name") or c.get("url") or "unknown",
            "name": c.get("name") or "",
            "url": c.get("url") or "",
            "stars": stars,
            "stars_tier": st_tier,
            "recency_score": round(rec, 4),
            "keyword_fit_score": round(kw_fit, 4),
            "language_match": round(lang, 4),
            "impact": round(impact, 4),
            "integration_cost_hours": cost_hours,
            "roi": round(roi, 6),
            "ia_category": _ia_category(c),
            "matched_keywords": list(c.get("matched_keywords", []) or []),
        })

    # Deterministic sort: ROI desc, then impact desc, then id asc (tiebreak).
    ranked.sort(key=lambda r: (-r["roi"], -r["impact"], r["id"]))

    co_tied = False
    if len(ranked) >= 2:
        r0 = ranked[0]["roi"]
        r1 = ranked[1]["roi"]
        if r0 > 0 and (r0 - r1) / r0 < CO_TIED_WINDOW:
            co_tied = True

    by_category: dict[str, int] = {}
    for r in ranked:
        cat = r["ia_category"]
        by_category[cat] = by_category.get(cat, 0) + 1

    top = ranked[:max(1, top_n)]

    return {
        "lens_name": lens.get("name", "unknown"),
        "ranked": top,
        "total_candidates": len(ranked),
        "co_tied_top": co_tied,
        "by_category": by_category,
    }


def print_table(report: dict) -> None:
    ranked = report.get("ranked", [])
    if not ranked:
        print("(no candidates)")
        return
    for i, r in enumerate(ranked, 1):
        print(
            f"[{i}] [{r['ia_category']}] {r['id']} — "
            f"ROI={r['roi']} (impact={r['impact']}, cost={r['integration_cost_hours']}h, "
            f"stars={r['stars']}, kw={r['keyword_fit_score']})"
        )
    if report.get("co_tied_top"):
        print("(co_tied_top: top-2 within 10% ROI)")


def main() -> int:
    ap = argparse.ArgumentParser(description="/upskill v2 intrinsic ROI ranker")
    ap.add_argument("--scout", required=True, help="scout JSON path")
    ap.add_argument("--lens", required=True, help="lens JSON path")
    ap.add_argument("--out", required=True, help="output JSON path")
    ap.add_argument("--top", type=int, default=5, help="top-N (max 20)")
    args = ap.parse_args()

    top_n = max(1, min(args.top, 20))

    scout = _load_json(args.scout)
    lens = _load_json(args.lens)
    _validate_scout(scout)
    _validate_lens(lens)

    report = score(scout, lens, top_n)

    out_path = Path(args.out).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    print_table(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
