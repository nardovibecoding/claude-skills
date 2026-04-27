#!/usr/bin/env python3
"""
bottleneck_read.py — /upskill SOP step 3 (S3 slice)

READ-ONLY bottleneck telemetry reader. Aggregates bigd-performance + the
bigd-upgrade `dis_score_assess` slice (per spec §1: only dis_score_assess —
NOT promote_lessons / internal_study / skill_consolidation) and emits a
normalized JSON for the S5 ROI ranker.

Resolution order (cache-first, mirrors S2 gaps_read.py):
  1. consumed bundle: ~/inbox/_summaries/consumed/<DATE>_bundle.json
     - if exists AND mtime <6h, use it (cache hit)
  2. pending per-host:  ~/inbox/_summaries/pending/<DATE>/{performance,upgrade}_<host>.json
     - read all available; cold_fired stays False
  3. cold-fire fallback: invoke ~/NardoWorld/scripts/bigd/performance/daemon.py
     - SKIPPED if KILLSWITCH file present → emits cold_fire_skipped reason
     - on success, re-reads pending dir

Token-spend + cache-hit-rate + dis_score are NOT carried in the SHIP-phase
pending summaries (only `info`-severity findings live in detector briefs +
registries). To guarantee the S5 ranker gets concrete numbers, we ALSO call
the detectors directly in-process (token_spend.run / cache_hit_rate.run /
ctx_growth.run / dis_score_assess.run). These detectors are pure read-only
filesystem scans, so in-process invocation is safe and adds no I/O overhead
beyond what cron does.

Output JSON shape (matches plan §S3 line 154-155 + spec §S5 input contract):
  {
    "token_spend_recent_7d": {"total_tokens": int, "by_model": {...}, "raw": {...}},
    "cache_hit_rate_recent_7d": float (0.0-1.0),
    "ctx_growth": [{growth_pct, threshold, ...}],
    "host_metrics": {...},     # from pending if available
    "dis_score": [...],         # from in-process dis_score_assess.run()
    "source_files": [...],
    "cold_fired": bool,
    "stale_age_hours": float,
    "cold_fire_skipped": "killswitch" | absent,
  }

CLI:
  python3 bottleneck_read.py [--date YYYY-MM-DD] [--out PATH]

Exits 0 on any non-crash outcome (empty data is a valid outcome). Exits 1
only on argument-parse error or write failure.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

HKT = ZoneInfo("Asia/Hong_Kong")

INBOX_SUMMARIES   = Path.home() / "inbox" / "_summaries"
CONSUMED_DIR      = INBOX_SUMMARIES / "consumed"
PENDING_DIR       = INBOX_SUMMARIES / "pending"
KILLSWITCH_PATH   = Path.home() / "NardoWorld" / "meta" / "big_systemd" / "KILLSWITCH"
PERF_DAEMON_PATH  = Path.home() / "NardoWorld" / "scripts" / "bigd" / "performance" / "daemon.py"
RULES_DIR         = Path.home() / "NardoWorld" / "meta" / "big_systemd" / "rules"

CACHE_FRESH_HOURS = 6.0
HOSTS             = ("mac", "hel", "london")


def _today_hkt() -> str:
    return datetime.now(HKT).strftime("%Y-%m-%d")


# ---------- pending / consumed readers ----------

def _read_consumed_bundle(date: str) -> tuple[dict | None, float, Path | None]:
    path = CONSUMED_DIR / f"{date}_bundle.json"
    if not path.exists():
        return None, float("inf"), None
    age_h = (time.time() - path.stat().st_mtime) / 3600.0
    try:
        return json.loads(path.read_text(encoding="utf-8")), age_h, path
    except Exception as exc:
        print(f"[bottleneck_read] WARN: failed to parse {path}: {exc}", file=sys.stderr)
        return None, age_h, path


def _read_pending(date: str, daemon: str) -> tuple[dict[str, dict], list[Path]]:
    out: dict[str, dict] = {}
    paths: list[Path] = []
    date_dir = PENDING_DIR / date
    if not date_dir.exists():
        return out, paths
    for host in HOSTS:
        p = date_dir / f"{daemon}_{host}.json"
        if not p.exists():
            continue
        try:
            out[host] = json.loads(p.read_text(encoding="utf-8"))
            paths.append(p)
        except Exception as exc:
            print(f"[bottleneck_read] WARN: failed to parse {p}: {exc}", file=sys.stderr)
    return out, paths


def _extract_perf_proposed_actions(by_host: dict[str, dict]) -> dict:
    """Pull host_metrics + ctx_growth signals from proposed_actions titles
    (the only place these surface in pending SHIP-phase summaries)."""
    host_metrics: dict = {}
    ctx_alerts: list[dict] = []
    for host, ds in by_host.items():
        for action in (ds or {}).get("proposed_actions") or []:
            if not isinstance(action, dict):
                continue
            title = action.get("title", "") or ""
            reason = action.get("reason", "") or ""
            if "ctx_growth" in reason or "context growth" in title.lower():
                ctx_alerts.append({"host": host, "title": title, "reason": reason})
            if "RSS" in title or "host_rss" in reason or "disk" in reason:
                host_metrics.setdefault(host, []).append({"title": title, "reason": reason})
    return {"host_metrics": host_metrics, "ctx_growth_alerts": ctx_alerts}


# ---------- in-process detector calls ----------

def _import_detector(module_path: str, name: str):
    """Lazy-load a detector module by file path."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, module_path)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    except Exception as exc:
        print(f"[bottleneck_read] WARN: import {name} failed: {exc}", file=sys.stderr)
        return None
    return mod


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        # bigd_common loads via the common helper; we mirror minimal yaml read.
        import yaml  # type: ignore
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _run_detectors_inproc() -> dict:
    """Invoke token_spend, cache_hit_rate, ctx_growth, dis_score_assess
    detectors in-process. Returns a dict with the raw findings keyed by
    detector name. Pure filesystem reads; safe to call ad-hoc."""
    perf_dir = Path.home() / "NardoWorld" / "scripts" / "bigd" / "performance" / "detectors"
    upgrade_dir = Path.home() / "NardoWorld" / "scripts" / "bigd" / "upgrade" / "detectors"

    common_cfg = _load_yaml(RULES_DIR / "common.yaml")
    perf_cfg   = _load_yaml(RULES_DIR / "performance.yaml")
    upgrade_cfg = _load_yaml(RULES_DIR / "upgrade.yaml")

    results: dict[str, list] = {
        "token_spend": [],
        "cache_hit_rate": [],
        "ctx_growth": [],
        "dis_score_assess": [],
    }

    for name, cfg, det_dir in (
        ("token_spend", perf_cfg, perf_dir),
        ("cache_hit_rate", perf_cfg, perf_dir),
        ("ctx_growth", perf_cfg, perf_dir),
        ("dis_score_assess", upgrade_cfg, upgrade_dir),
    ):
        mod = _import_detector(str(det_dir / f"{name}.py"), name)
        if mod is None or not hasattr(mod, "run"):
            continue
        try:
            results[name] = mod.run(cfg, common_cfg, dry_run=True) or []
        except Exception as exc:
            print(f"[bottleneck_read] WARN: detector {name} crashed: {exc}",
                  file=sys.stderr)
    return results


# ---------- aggregation ----------

def _aggregate_token_spend(findings: list[dict]) -> dict:
    """Thread token_spend.py output (see schema in token_spend.py:136-155).
    Returns shape: {total_tokens, by_model, recent_7d_per_model_per_day, raw}."""
    if not findings:
        return {"total_tokens": 0, "by_model": {}, "recent_7d_per_model_per_day": [], "raw": {}}
    rep = next((f for f in findings if f.get("type") == "token_spend_report"), None)
    if rep is None:
        # skip case
        return {"total_tokens": 0, "by_model": {}, "recent_7d_per_model_per_day": [],
                "raw": findings[0]}
    by_model = {}
    for m in rep.get("model_summary") or []:
        by_model[m["model"]] = {
            "input_tokens": m.get("total_input_tokens", 0),
            "output_tokens": m.get("total_output_tokens", 0),
            "cache_creation_tokens": m.get("total_cache_creation_tokens", 0),
            "cache_read_tokens": m.get("total_cache_read_tokens", 0),
            "msg_count": m.get("total_msg_count", 0),
        }
    total = rep.get("grand_total_input_tokens", 0) + rep.get("grand_total_output_tokens", 0)
    return {
        "total_tokens": total,
        "by_model": by_model,
        "recent_7d_per_model_per_day": rep.get("recent_7d_per_model_per_day", []),
        "raw": {
            "files_scanned": rep.get("files_scanned"),
            "models_seen": rep.get("models_seen"),
            "grand_total_input_tokens": rep.get("grand_total_input_tokens", 0),
            "grand_total_output_tokens": rep.get("grand_total_output_tokens", 0),
        },
    }


def _aggregate_cache_hit_rate(findings: list[dict]) -> float:
    rep = next((f for f in findings if f.get("type") == "cache_hit_rate_report"), None)
    if rep is None:
        return 0.0
    pct = rep.get("overall_cache_hit_rate_pct", 0.0)
    return round(float(pct) / 100.0, 4)


def _aggregate_ctx_growth(findings: list[dict]) -> list[dict]:
    out = []
    for f in findings:
        if f.get("type") in ("ctx_growth_report", "ctx_growth_alert"):
            out.append({
                "type": f.get("type"),
                "growth_pct": f.get("growth_pct_estimate") or f.get("growth_pct"),
                "threshold_pct": f.get("alert_threshold_pct") or f.get("threshold_pct"),
                "session_count": f.get("session_count"),
                "total_input_tokens": f.get("total_input_tokens"),
                "total_output_tokens": f.get("total_output_tokens"),
            })
    return out


def _aggregate_dis_score(findings: list[dict]) -> list[dict]:
    """Per spec §1: ONLY dis_score_assess is in scope. Returns per-skill rows."""
    out = []
    for f in findings:
        ftype = f.get("type", "")
        if ftype.startswith("dis_") and ftype not in ("dis_score_summary",):
            out.append({
                "skill": f.get("name"),
                "D": f.get("D"),
                "I": f.get("I"),
                "S": f.get("S"),
                "total": f.get("total"),
                "percentile": f.get("percentile"),
                "message": f.get("message"),
            })
    return out


# ---------- cold-fire ----------

def _cold_fire_perf() -> tuple[bool, str | None]:
    if KILLSWITCH_PATH.exists():
        return False, "killswitch"
    if not PERF_DAEMON_PATH.exists():
        return False, "daemon_missing"
    try:
        proc = subprocess.run(
            ["python3", str(PERF_DAEMON_PATH)],
            capture_output=True, text=True, timeout=120,
        )
        if proc.returncode != 0:
            return False, f"daemon_exit_{proc.returncode}"
        return True, None
    except subprocess.TimeoutExpired:
        return False, "daemon_timeout"
    except Exception as exc:
        return False, f"daemon_error:{type(exc).__name__}"


# ---------- main report ----------

def build_report(date: str) -> dict:
    report: dict = {
        "token_spend_recent_7d": {"total_tokens": 0, "by_model": {}},
        "cache_hit_rate_recent_7d": 0.0,
        "ctx_growth": [],
        "host_metrics": {},
        "dis_score": [],
        "source_files": [],
        "cold_fired": False,
        "stale_age_hours": 0.0,
    }

    source_files: list[str] = []

    # 1) consumed bundle (records freshness; SHIP-phase data only)
    bundle, age_h, bundle_path = _read_consumed_bundle(date)
    used_bundle = bundle is not None and age_h < CACHE_FRESH_HOURS
    if bundle_path and bundle is not None:
        source_files.append(str(bundle_path))
        report["stale_age_hours"] = round(age_h, 3)

    # 2) pending per-host (perf + upgrade) — surface host_metrics + ctx alerts
    perf_by_host, perf_paths = _read_pending(date, "performance")
    upgrade_by_host, upgrade_paths = _read_pending(date, "upgrade")
    source_files.extend(str(p) for p in perf_paths)
    source_files.extend(str(p) for p in upgrade_paths)

    if perf_by_host:
        sig = _extract_perf_proposed_actions(perf_by_host)
        report["host_metrics"] = sig["host_metrics"]
        if sig["ctx_growth_alerts"]:
            report["ctx_growth"].extend(sig["ctx_growth_alerts"])

    # 3) cold-fire if BOTH bundle stale AND no pending data
    if not used_bundle and not perf_by_host and not upgrade_by_host:
        fired, skip_reason = _cold_fire_perf()
        if fired:
            report["cold_fired"] = True
            perf_by_host, perf_paths = _read_pending(date, "performance")
            source_files.extend(str(p) for p in perf_paths)
            if perf_by_host:
                sig = _extract_perf_proposed_actions(perf_by_host)
                report["host_metrics"] = sig["host_metrics"]
                if sig["ctx_growth_alerts"]:
                    report["ctx_growth"].extend(sig["ctx_growth_alerts"])
        elif skip_reason:
            report["cold_fire_skipped"] = skip_reason

    # 4) ALWAYS run detectors in-process — guarantees token_spend / cache_hit /
    #    dis_score numbers reach the S5 ranker regardless of cron freshness.
    detector_findings = _run_detectors_inproc()
    report["token_spend_recent_7d"] = _aggregate_token_spend(detector_findings["token_spend"])
    report["cache_hit_rate_recent_7d"] = _aggregate_cache_hit_rate(
        detector_findings["cache_hit_rate"]
    )
    cg = _aggregate_ctx_growth(detector_findings["ctx_growth"])
    if cg:
        report["ctx_growth"].extend(cg)
    report["dis_score"] = _aggregate_dis_score(detector_findings["dis_score_assess"])

    # de-dup source_files preserving order
    seen = set()
    report["source_files"] = [p for p in source_files if not (p in seen or seen.add(p))]
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="/upskill bottleneck telemetry reader (S3)")
    ap.add_argument("--date", default=None, help="YYYY-MM-DD (default: today HKT)")
    ap.add_argument("--out", default="/tmp/upskill_bottleneck.json", help="output JSON path")
    args = ap.parse_args()

    date = args.date or _today_hkt()
    report = build_report(date)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
