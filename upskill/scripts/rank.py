#!/usr/bin/env python3
"""
rank.py — /upskill SOP step 4 (S5 slice)

Aggregates outputs of S2 (gaps), S3 (bottleneck), S4 (scout) into a unified
ranked candidate list by ROI = impact / expected_token_spend.

ROI is a SORT HINT not a verdict — base_costs uncalibrated in v1. Co-tied
top-2 within 10% are flagged via co_tied_top.

Refs:
  ~/.claude/skills/upskill/references/roi-formula.md  (base_costs, multipliers)
  ~/.claude/skills/upskill/references/ia-categories.md (5 IA labels)
  ~/.ship/upskill/goals/01-spec.md §3, §4.5

CLI:
  rank.py --gaps GAPS.json --bottleneck PERF.json --scout SCOUT.json --out OUT.json [--top-n N]

Exits 0 on success; 1 on arg-parse / IO failure.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

HKT = ZoneInfo("Asia/Hong_Kong")

# ROI base-cost map (refs/roi-formula.md). Token spend per category.
BASE_COSTS = {
    "FIX-DRIFT":   50_000,
    "FIX-PERF":    30_000,
    "ADOPT-EXT":  120_000,
    "TRIM-SKILL":  15_000,
    "CLEAN-HOUSE": 25_000,
}

CALIBRATION_WARNING = (
    "ROI is a SORT HINT not a verdict — base_costs uncalibrated in v1. "
    "Use --calibrate (Phase-2) once 30d of accept/ignore feedback exists."
)

CO_TIED_WINDOW = 0.10  # top-2 within 10% ROI


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return s[:80] or "anon"


def _safe_load(path: str | None) -> dict:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        print(f"[rank] WARN: {path} not found, treating as empty", file=sys.stderr)
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[rank] WARN: failed to parse {path}: {exc}", file=sys.stderr)
        return {}


# ---- Normalizers --------------------------------------------------------

def _norm_gaps(gaps_json: dict) -> list[dict]:
    """Map gap findings → unified candidate shape. Severity → IA + impact."""
    out: list[dict] = []
    findings = gaps_json.get("findings") or []
    sev_counts = gaps_json.get("findings_by_severity") or {}

    if findings:
        for f in findings:
            sev = (f.get("severity") or "low").lower()
            if sev in ("critical",):
                impact = 5
            elif sev in ("high",):
                impact = 4
            elif sev in ("medium",):
                impact = 3
            elif sev in ("low",):
                impact = 2
            else:
                impact = 1
            host = f.get("host")
            title = f.get("title") or f.get("id") or "gap"
            fid = f.get("id") or _slugify(title)
            out.append({
                "ia_category": "FIX-DRIFT",
                "source":      "gaps",
                "id":          f"gap-{_slugify(fid)}",
                "title":       title,
                "summary":     f"[{sev}] {title} (host={host or 'n/a'})",
                "host":        host,
                "impact":      impact,
                "raw":         f,
            })
    else:
        # No per-finding records — synthesize from severity counts so the
        # signal is not lost. Each non-zero bucket = 1 aggregate candidate.
        for sev, n in sev_counts.items():
            if not isinstance(n, int) or n <= 0:
                continue
            sev = sev.lower()
            if sev == "critical":
                impact = 5
            elif sev == "high":
                impact = 4
            elif sev == "medium":
                impact = 3
            elif sev == "low":
                impact = 2
            else:
                impact = 1
            out.append({
                "ia_category": "FIX-DRIFT",
                "source":      "gaps",
                "id":          f"gap-bucket-{sev}",
                "title":       f"{n} {sev}-severity gap finding(s)",
                "summary":     f"{n} bigd-gaps finding(s) at severity={sev} (no per-finding detail in bundle)",
                "host":        None,
                "impact":      impact,
                "raw":         {"bucket": sev, "count": n},
            })
    return out


def _norm_bottleneck(perf_json: dict) -> list[dict]:
    """Map bottleneck records → FIX-PERF candidates."""
    out: list[dict] = []

    # cache_hit_rate
    cache_hit = perf_json.get("cache_hit_rate_recent_7d")
    if isinstance(cache_hit, (int, float)) and cache_hit < 0.9:
        out.append({
            "ia_category": "FIX-PERF",
            "source":      "cache_hit_rate",
            "id":          "perf-cache-hit-low",
            "title":       f"Cache hit rate {cache_hit:.3f} below 0.9",
            "summary":     f"7d cache hit rate = {cache_hit:.3f}; sub-0.9 means cold prompts/wasted tokens.",
            "host":        None,
            "impact":      4,
            "raw":         {"cache_hit_rate": cache_hit},
        })

    # token spend (>50M / 7d)
    ts = perf_json.get("token_spend_recent_7d") or {}
    total = ts.get("total_tokens") or 0
    if isinstance(total, (int, float)) and total > 50_000_000:
        out.append({
            "ia_category": "FIX-PERF",
            "source":      "token_spend",
            "id":          "perf-token-spend-high",
            "title":       f"Token spend 7d = {int(total):,}",
            "summary":     f"7d token spend {int(total):,} > 50M threshold; investigate hot loops / context bloat.",
            "host":        None,
            "impact":      4,
            "raw":         {"total_tokens": total},
        })

    # dis_score (low total = wasted skill surface)
    for ds in perf_json.get("dis_score") or []:
        if not isinstance(ds, dict):
            continue
        score_total = ds.get("total")
        if not isinstance(score_total, (int, float)):
            continue
        # Only surface clearly-low (≤2) — those are TRIM-SKILL candidates.
        if score_total <= 2:
            skill_name = ds.get("skill") or "unknown"
            # Skip pseudo-entries like .git / .ruff_cache (not real skills).
            if skill_name.startswith("."):
                continue
            out.append({
                "ia_category": "TRIM-SKILL",
                "source":      "dis_score",
                "id":          f"trim-{_slugify(skill_name)}",
                "title":       f"Skill '{skill_name}' D+I+S total={score_total}",
                "summary":     ds.get("message") or f"Skill {skill_name} low DIS score; candidate for retire.",
                "host":        None,
                "impact":      2,
                "raw":         ds,
            })

    # dis_score for impact-3 FIX-PERF: scores 3-4 are "meaningful" perf signals
    for ds in perf_json.get("dis_score") or []:
        if not isinstance(ds, dict):
            continue
        score_total = ds.get("total")
        if not isinstance(score_total, (int, float)):
            continue
        if 3 <= score_total <= 5:
            skill_name = ds.get("skill") or "unknown"
            if skill_name.startswith("."):
                continue
            # Higher score → higher severity (3=meaningful, 4=high)
            impact = 3 if score_total <= 4 else 4
            out.append({
                "ia_category": "FIX-PERF",
                "source":      "dis_score",
                "id":          f"perf-disscore-{_slugify(skill_name)}",
                "title":       f"Skill '{skill_name}' DIS={score_total}",
                "summary":     ds.get("message") or f"Skill {skill_name} DIS score {score_total} suggests perf attention.",
                "host":        None,
                "impact":      impact,
                "raw":         ds,
            })

    # ctx_growth >20%/wk
    for ctx in perf_json.get("ctx_growth") or []:
        if not isinstance(ctx, dict):
            continue
        gp = ctx.get("growth_pct")
        thr = ctx.get("threshold_pct") or 20
        if isinstance(gp, (int, float)) and gp > thr:
            out.append({
                "ia_category": "FIX-PERF",
                "source":      "ctx_growth",
                "id":          f"perf-ctx-growth-{int(gp)}",
                "title":       f"Context growth {gp:.1f}% above {thr}% threshold",
                "summary":     f"Weekly context growth {gp:.1f}% exceeds {thr}% threshold.",
                "host":        None,
                "impact":      3,
                "raw":         ctx,
            })

    # host_metrics (down/critical → impact 4)
    hm = perf_json.get("host_metrics") or {}
    if isinstance(hm, dict):
        for host, metrics in hm.items():
            if not isinstance(metrics, dict):
                continue
            status = (metrics.get("status") or "").lower()
            if status in ("critical", "down"):
                out.append({
                    "ia_category": "FIX-PERF",
                    "source":      "host_metrics",
                    "id":          f"perf-host-{_slugify(host)}",
                    "title":       f"Host {host} status={status}",
                    "summary":     f"Host {host} reporting {status}: {metrics}",
                    "host":        host,
                    "impact":      4,
                    "raw":         metrics,
                })

    return out


def _stars_tier(stars: int | float | None) -> int:
    """impact 3 if >5K, 2 if >1K, else 1."""
    if not isinstance(stars, (int, float)):
        return 1
    if stars > 5_000:
        return 3
    if stars > 1_000:
        return 2
    return 1


def _norm_scout(scout_json: dict) -> list[dict]:
    out: list[dict] = []
    for c in scout_json.get("candidates") or []:
        if not isinstance(c, dict):
            continue
        src = c.get("source") or "unknown"
        name = c.get("name") or c.get("url") or "unknown"
        url = c.get("url") or ""
        stars = c.get("stars") or 0

        if src == "anthropic_releases":
            ia = "ADOPT-EXT"
            impact = 4  # model bumps / CLI updates compound
        elif src.startswith("github_topic"):
            ia = "ADOPT-EXT"
            impact = _stars_tier(stars)
        elif src == "awesome_skills":
            ia = "ADOPT-EXT"
            impact = 2
        else:
            ia = "ADOPT-EXT"
            impact = 1

        out.append({
            "ia_category": ia,
            "source":      src,
            "id":          f"adopt-{_slugify(name)}",
            "title":       name,
            "summary":     c.get("summary") or "",
            "host":        None,
            "impact":      impact,
            "raw":         c,
            "_url":        url,
            "_stars":      stars,
            "_updated_at": c.get("updated_at"),
        })
    return out


# ---- ROI compute --------------------------------------------------------

def _expected_cost(cand: dict) -> int:
    base = BASE_COSTS.get(cand["ia_category"], 50_000)
    if cand.get("host"):
        # Single host, no multiplier. Cross-host detection is N/A in v1
        # since the gap finding only carries one host. Hook left for later.
        pass
    return int(base)


def _roi(cand: dict) -> float:
    cost = max(_expected_cost(cand), 1)
    return cand["impact"] / cost * 1_000_000.0


def _build_unified(gaps: dict, perf: dict, scout: dict) -> list[dict]:
    cands = _norm_gaps(gaps) + _norm_bottleneck(perf) + _norm_scout(scout)
    for c in cands:
        c["expected_token_spend"] = _expected_cost(c)
        c["roi"] = round(_roi(c), 4)
    return cands


def _by_category(cands: list[dict]) -> dict:
    out = {k: 0 for k in BASE_COSTS.keys()}
    for c in cands:
        cat = c.get("ia_category")
        if cat in out:
            out[cat] += 1
    return out


def _sort_and_tied(cands: list[dict]) -> tuple[list[dict], bool]:
    """Sort desc by ROI; tiebreak by impact desc, expected_token_spend asc,
    then updated_at desc (None last). Mark co_tied flag if top-2 within 10%."""
    def _key(c: dict):
        ts = c.get("_updated_at") or ""
        return (-c["roi"], -c["impact"], c["expected_token_spend"], -len(ts), ts)

    cands_sorted = sorted(cands, key=_key)

    co_tied = False
    if len(cands_sorted) >= 2:
        r0, r1 = cands_sorted[0]["roi"], cands_sorted[1]["roi"]
        if r0 > 0 and abs(r0 - r1) / r0 <= CO_TIED_WINDOW:
            co_tied = True
            cands_sorted[0]["co_tied"] = True
            cands_sorted[1]["co_tied"] = True
    return cands_sorted, co_tied


# ---- main ---------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="/upskill ranker (S5)")
    ap.add_argument("--gaps",       required=True)
    ap.add_argument("--bottleneck", required=True)
    ap.add_argument("--scout",      required=True)
    ap.add_argument("--out",        required=True)
    ap.add_argument("--top-n",      type=int, default=5)
    args = ap.parse_args()

    gaps  = _safe_load(args.gaps)
    perf  = _safe_load(args.bottleneck)
    scout = _safe_load(args.scout)

    unified = _build_unified(gaps, perf, scout)
    ranked, co_tied = _sort_and_tied(unified)
    top = ranked[: max(args.top_n, 1)]

    report = {
        "ts":                  datetime.now(HKT).isoformat(),
        "ranked":              top,
        "all_count":           len(unified),
        "total_candidates":    len(unified),
        "by_category":         _by_category(unified),
        "co_tied_top":         co_tied,
        "calibration_warning": CALIBRATION_WARNING,
        "sources": {
            "gaps":       args.gaps,
            "bottleneck": args.bottleneck,
            "scout":      args.scout,
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
