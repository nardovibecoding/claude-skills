#!/usr/bin/env python3
"""
gaps_read.py — /upskill SOP step 2 (S2 slice)

READ-ONLY internal gap reader. Aggregates bigd-gaps daemon output across
hosts (mac/hel/london) and emits a normalized JSON to --out for downstream
ranking (S5).

Resolution order:
  1. consumed bundle: ~/inbox/_summaries/consumed/<DATE>_bundle.json
     - if exists AND mtime <6h, use it (cache hit, stale_age_hours computed)
  2. pending per-host:  ~/inbox/_summaries/pending/<DATE>/gaps_<host>.json
     - read all available; cold_fired stays False
  3. cold-fire fallback: invoke ~/NardoWorld/scripts/bigd/gaps/daemon.py
     - SKIPPED if KILLSWITCH file present → emits cold_fire_skipped reason
     - on success, re-reads pending dir

Output JSON shape (matches plan §S2 line 147):
  {
    "findings_by_severity": {critical, high, medium, low, info},
    "source_files": [...],
    "cold_fired": bool,
    "stale_age_hours": float,
    "findings": [{id, severity, title, host}, ...],
    "cold_fire_skipped": "killswitch" | absent
  }

CLI:
  python3 gaps_read.py [--date YYYY-MM-DD] [--out PATH]

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
DAEMON_PATH       = Path.home() / "NardoWorld" / "scripts" / "bigd" / "gaps" / "daemon.py"

CACHE_FRESH_HOURS = 6.0
SEVERITY_KEYS     = ("critical", "high", "medium", "low", "info")
HOSTS             = ("mac", "hel", "london")


def _today_hkt() -> str:
    return datetime.now(HKT).strftime("%Y-%m-%d")


def _empty_severity() -> dict:
    return {k: 0 for k in SEVERITY_KEYS}


def _accumulate_severity(target: dict, src: dict | None) -> None:
    """Add per-severity counts from src into target (in-place). Ignores keys
    not in SEVERITY_KEYS to keep schema deterministic."""
    if not isinstance(src, dict):
        return
    for k in SEVERITY_KEYS:
        v = src.get(k, 0)
        if isinstance(v, int):
            target[k] += v


def _extract_findings_for_host(daemon_summary: dict, host: str) -> list[dict]:
    """Pull a list of findings (id/severity/title/host) from one daemon
    summary dict. The bigd-gaps schema does not embed full findings in the
    summary; it carries `proposed_actions` + `skipped_findings` + a
    severity-bucketed count.

    Strategy: walk proposed_actions (most actionable) and skipped_findings.
    Each entry contributes one record. Missing fields default to "" / "low".
    """
    out: list[dict] = []
    # Param is typed `dict`; isinstance guard would be unreachable. Caller
    # ensures we only pass dicts (see _aggregate_from_*).

    for action in daemon_summary.get("proposed_actions") or []:
        if not isinstance(action, dict):
            continue
        out.append({
            "id":       action.get("id") or action.get("finding_id") or "",
            "severity": action.get("severity") or "low",
            "title":    action.get("title") or action.get("description") or action.get("action_type") or "",
            "host":     host,
        })

    for skipped in daemon_summary.get("skipped_findings") or []:
        if not isinstance(skipped, dict):
            continue
        out.append({
            "id":       skipped.get("id") or skipped.get("finding_id") or "",
            "severity": skipped.get("severity") or "low",
            "title":    skipped.get("title") or skipped.get("reason") or "",
            "host":     host,
        })

    return out


def _read_consumed_bundle(date: str) -> tuple[dict | None, float, Path | None]:
    """Return (bundle_dict, age_hours, path) or (None, inf, None)."""
    path = CONSUMED_DIR / f"{date}_bundle.json"
    if not path.exists():
        return None, float("inf"), None
    age_s = time.time() - path.stat().st_mtime
    age_h = age_s / 3600.0
    try:
        return json.loads(path.read_text(encoding="utf-8")), age_h, path
    except Exception as exc:
        print(f"[gaps_read] WARN: failed to parse {path}: {exc}", file=sys.stderr)
        return None, age_h, path


def _read_pending_per_host(date: str) -> tuple[dict[str, dict], list[Path]]:
    """Return ({host: summary_dict}, [paths_read])."""
    out: dict[str, dict] = {}
    paths: list[Path] = []
    date_dir = PENDING_DIR / date
    if not date_dir.exists():
        return out, paths
    for host in HOSTS:
        p = date_dir / f"gaps_{host}.json"
        if not p.exists():
            continue
        try:
            out[host] = json.loads(p.read_text(encoding="utf-8"))
            paths.append(p)
        except Exception as exc:
            print(f"[gaps_read] WARN: failed to parse {p}: {exc}", file=sys.stderr)
    return out, paths


def _aggregate_from_bundle(bundle: dict) -> tuple[dict, list[dict]]:
    """Walk `summaries["gaps@<host>"]` keys. Returns (sev_totals, findings)."""
    sev = _empty_severity()
    findings: list[dict] = []
    summaries = bundle.get("summaries") or {}
    for key, ds in summaries.items():
        if not isinstance(key, str) or not key.startswith("gaps@"):
            continue
        host = key.split("@", 1)[1]
        land = (((ds or {}).get("ship_phases") or {}).get("land") or {})
        _accumulate_severity(sev, land.get("findings_by_severity"))
        findings.extend(_extract_findings_for_host(ds, host))
    return sev, findings


def _aggregate_from_pending(by_host: dict[str, dict]) -> tuple[dict, list[dict]]:
    sev = _empty_severity()
    findings: list[dict] = []
    for host, ds in by_host.items():
        land = (((ds or {}).get("ship_phases") or {}).get("land") or {})
        _accumulate_severity(sev, land.get("findings_by_severity"))
        findings.extend(_extract_findings_for_host(ds, host))
    return sev, findings


def _cold_fire() -> tuple[bool, str | None]:
    """Returns (fired_ok, skip_reason). Honors KILLSWITCH."""
    if KILLSWITCH_PATH.exists():
        return False, "killswitch"
    if not DAEMON_PATH.exists():
        return False, "daemon_missing"
    try:
        proc = subprocess.run(
            ["python3", str(DAEMON_PATH)],
            capture_output=True, text=True, timeout=120,
        )
        if proc.returncode != 0:
            return False, f"daemon_exit_{proc.returncode}"
        return True, None
    except subprocess.TimeoutExpired:
        return False, "daemon_timeout"
    except Exception as exc:
        return False, f"daemon_error:{type(exc).__name__}"


def build_report(date: str) -> dict:
    report: dict = {
        "findings_by_severity": _empty_severity(),
        "source_files":         [],
        "cold_fired":           False,
        "stale_age_hours":      0.0,
        "findings":             [],
    }

    # 1) consumed bundle
    bundle, age_h, bundle_path = _read_consumed_bundle(date)
    if bundle is not None and age_h < CACHE_FRESH_HOURS:
        sev, findings = _aggregate_from_bundle(bundle)
        report["findings_by_severity"] = sev
        report["source_files"]         = [str(bundle_path)] if bundle_path else []
        report["stale_age_hours"]      = round(age_h, 3)
        report["findings"]             = findings
        return report

    # 2) pending per-host
    by_host, paths = _read_pending_per_host(date)
    if by_host:
        sev, findings = _aggregate_from_pending(by_host)
        report["findings_by_severity"] = sev
        report["source_files"]         = [str(p) for p in paths]
        report["findings"]             = findings
        # Stale bundle (if any) noted via age:
        if bundle is not None:
            report["stale_age_hours"] = round(age_h, 3)
        return report

    # 3) cold-fire fallback (no fresh data anywhere)
    fired, skip_reason = _cold_fire()
    if not fired:
        if skip_reason:
            report["cold_fire_skipped"] = skip_reason
        return report

    report["cold_fired"] = True
    by_host, paths = _read_pending_per_host(date)
    if by_host:
        sev, findings = _aggregate_from_pending(by_host)
        report["findings_by_severity"] = sev
        report["source_files"]         = [str(p) for p in paths]
        report["findings"]             = findings
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="/upskill internal gap reader (S2)")
    ap.add_argument("--date", default=None, help="YYYY-MM-DD (default: today HKT)")
    ap.add_argument("--out",  default="/tmp/upskill_gaps.json", help="output JSON path")
    args = ap.parse_args()

    date = args.date or _today_hkt()
    report = build_report(date)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
