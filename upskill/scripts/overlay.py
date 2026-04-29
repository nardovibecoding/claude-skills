#!/usr/bin/env python3
"""overlay.py — /upskill v2 SOP step 4 (S4 slice).

Optional bigd-context overlay. Reads scored JSON (from score.py) + lens JSON
(from lens_resolve.py); if `lens.overlay_sources` is non-empty AND the
referenced bigd JSON(s) are available, walks the top-N candidates and
appends `context_tags: ["<source>:<finding-id>", ...]` where the candidate's
keywords/name overlap with the bigd finding's title/keywords.

Spec: ~/.ship/upskill/goals/01-spec.md §1 step 4 (lines 32) + acceptance
A1/A4/A5 (200-237). Overlay is decoration — bigd-absent path is the default
happy path; overlay.py MUST exit 0 with `overlay_applied: false` when no
bigd data exists. NEVER raises FileNotFoundError on missing bigd input.

CLI:
  python3 overlay.py --scored <scored.json> --lens <lens.json> --out <path>
                     [--top 3] [--skip-bigd] [--date YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

HKT = ZoneInfo("Asia/Hong_Kong")
SCRIPTS_DIR = Path(__file__).parent.resolve()

# Map overlay-source name -> reader script. v2 supports the two shipped readers;
# unknown sources log a skip reason + continue (per spec A1 — never crash).
READER_MAP = {
    "bigd-gaps": SCRIPTS_DIR / "gaps_read.py",
    "bigd-perf": SCRIPTS_DIR / "bottleneck_read.py",
}


def _today_hkt() -> str:
    return datetime.now(HKT).strftime("%Y-%m-%d")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _invoke_reader(script: Path, date: str) -> dict | None:
    """Run a v1 reader (gaps_read.py / bottleneck_read.py) into a tempfile.
    Both readers exit 0 on missing data (empty findings) — we treat any
    non-zero exit OR empty findings as "no overlay data available"."""
    if not script.exists():
        return None
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        tmp = Path(tf.name)
    try:
        proc = subprocess.run(
            ["python3", str(script), "--date", date, "--out", str(tmp)],
            capture_output=True, text=True, timeout=180,
        )
        if proc.returncode != 0:
            return None
        return _load_json(tmp)
    except Exception:
        return None
    finally:
        try:
            tmp.unlink()
        except Exception:
            pass


def _has_data(source: str, payload: dict | None) -> bool:
    """True if the reader returned actual findings (not just empty scaffolding)."""
    if not payload:
        return False
    if source == "bigd-gaps":
        return bool(payload.get("findings"))
    if source == "bigd-perf":
        # perf reader runs in-process detectors even with no pending files;
        # consider it "has data" if dis_score has rows or token_spend > 0
        if payload.get("dis_score"):
            return True
        ts = (payload.get("token_spend_recent_7d") or {}).get("total_tokens", 0)
        if ts and ts > 0:
            return True
        if payload.get("ctx_growth"):
            return True
        return False
    return False


def _candidate_terms(cand: dict) -> set[str]:
    """Lower-cased term-bag for a scored candidate."""
    bag: list[str] = []
    for k in ("name", "id"):
        v = cand.get(k) or ""
        if isinstance(v, str):
            bag.append(v)
    for kw in cand.get("matched_keywords") or []:
        if isinstance(kw, str):
            bag.append(kw)
    # split on non-word chars; keep tokens >=3 chars to avoid noise
    out: set[str] = set()
    import re
    for s in bag:
        for tok in re.split(r"[^a-zA-Z0-9]+", s.lower()):
            if len(tok) >= 3:
                out.add(tok)
    return out


def _gaps_findings_iter(payload: dict):
    """Yield (finding_id, term_bag) for bigd-gaps."""
    for f in payload.get("findings") or []:
        fid = f.get("id") or ""
        title = f.get("title") or ""
        sev = f.get("severity") or ""
        terms = _candidate_terms({"name": title, "matched_keywords": [sev]})
        # also add finding-id tokens (e.g. G-skill-stale-debug → skill, stale, debug)
        terms |= _candidate_terms({"name": fid})
        if fid:
            yield fid, terms


def _perf_findings_iter(payload: dict):
    """Yield (finding_id, term_bag) for bigd-perf. Manufactures synthetic IDs
    from dis_score skill names + ctx_growth alerts (real bigd-perf findings
    don't carry stable G-style IDs)."""
    for row in payload.get("dis_score") or []:
        skill = row.get("skill") or ""
        if not skill:
            continue
        fid = f"dis-score-{skill}"
        terms = _candidate_terms({"name": skill, "matched_keywords": ["disuse", "skill"]})
        yield fid, terms
    for cg in payload.get("ctx_growth") or []:
        host = cg.get("host") or "unknown"
        fid = f"ctx-growth-{host}"
        terms = _candidate_terms({
            "name": cg.get("title") or "context growth",
            "matched_keywords": ["context", "growth", "tokens"],
        })
        yield fid, terms
    # token_spend → one synthetic finding for top model
    ts = payload.get("token_spend_recent_7d") or {}
    if ts.get("total_tokens", 0) > 0:
        yield "token-spend-7d", _candidate_terms({
            "name": "token spend",
            "matched_keywords": ["tokens", "cost", "cache", "performance"],
        })


def _findings_iter(source: str, payload: dict):
    if source == "bigd-gaps":
        yield from _gaps_findings_iter(payload)
    elif source == "bigd-perf":
        yield from _perf_findings_iter(payload)


def apply_overlay(scored: dict, lens: dict, *, top_n: int, date: str,
                  skip_bigd: bool) -> dict:
    out = dict(scored)  # shallow copy preserves all input keys
    out["overlay_applied"] = False
    out["overlay_sources_used"] = []
    out["overlay_sources_missing"] = []

    sources = list(lens.get("overlay_sources") or [])
    if not sources or skip_bigd:
        return out

    payloads: dict[str, dict] = {}
    for src in sources:
        if src not in READER_MAP:
            out["overlay_sources_missing"].append(f"{src}:not_implemented")
            continue
        payload = _invoke_reader(READER_MAP[src], date)
        if payload is None or not _has_data(src, payload):
            out["overlay_sources_missing"].append(src)
            continue
        payloads[src] = payload

    if not payloads:
        return out

    ranked = list(out.get("ranked") or [])
    n = max(0, min(top_n, len(ranked)))
    for i in range(n):
        cand = dict(ranked[i])
        cand_terms = _candidate_terms(cand)
        tags: list[str] = list(cand.get("context_tags") or [])
        for src, payload in payloads.items():
            for fid, fterms in _findings_iter(src, payload):
                if cand_terms & fterms:
                    tag = f"{src}:{fid}"
                    if tag not in tags:
                        tags.append(tag)
        cand["context_tags"] = tags
        ranked[i] = cand
    out["ranked"] = ranked
    out["overlay_applied"] = True
    out["overlay_sources_used"] = sorted(payloads.keys())
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="/upskill v2 bigd-context overlay (S4)")
    ap.add_argument("--scored", required=True, help="scored JSON path (from score.py)")
    ap.add_argument("--lens",   required=True, help="lens JSON path (from lens_resolve.py)")
    ap.add_argument("--out",    required=True, help="output JSON path")
    ap.add_argument("--top",    type=int, default=3, help="overlay top-N (default 3)")
    ap.add_argument("--date",   default=None, help="YYYY-MM-DD (default: today HKT)")
    ap.add_argument("--skip-bigd", action="store_true",
                    help="skip overlay entirely (test A5 path explicitly)")
    args = ap.parse_args()

    scored = _load_json(Path(args.scored).expanduser())
    lens   = _load_json(Path(args.lens).expanduser())
    date   = args.date or _today_hkt()

    report = apply_overlay(scored, lens, top_n=args.top, date=date,
                           skip_bigd=args.skip_bigd)

    out_path = Path(args.out).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
