"""SSOT integrity checks — Phase 9 detector module.

Scope:
  1. check_missing_required: required field absence (event_id / ts / host).
  2. check_unknown_kinds: kinds in last 24h NOT in KNOWN_KINDS registry.
  3. check_writer_health_absence: stub for α.S10 to fill (per F.3 cross-slice coord).

Source-of-truth for KNOWN_KINDS = THIS file.
When a slice (β/γ bucket) introduces a new event kind, it MUST add an entry
to KNOWN_KINDS here AND cite this file in its plan.

Created: α.S7 (this slice). Extended by α.S10 (writer-health detector).
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Dict


# ──────────────────────────────────────────────────────────────────────────────
# KNOWN_KINDS registry — α + β + γ buckets
# ──────────────────────────────────────────────────────────────────────────────
KNOWN_KINDS = frozenset({
    # α-bucket (17): tool/turn/session/system/bot + sample_* + writer_* + secret
    "tool_call",
    "user_turn",
    "assistant_turn",
    "session.precompact",
    "session.permission_request",
    "session.save",
    "system",
    "bot_event",
    "sample_cpu",
    "sample_rss",
    "sample_disk",
    "sample_network",
    "sample_clock_skew",
    "writer_health",
    "writer_backpressure",
    "writer_resume",
    "secret_redaction",
    # β-bucket reservations (6)
    "api_call",
    "llm_call",
    "cost_event",
    "process_crash",
    "circuit_breaker_transition",
    "agent_decision",
    # γ-bucket reservations (1)
    "file_state_change",
})


def check_missing_required(jsonl_path: Path) -> int:
    """Count rows with null/missing event_id, ts, or host."""
    p = Path(jsonl_path)
    if not p.exists():
        return 0
    n = 0
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                n += 1
                continue
            if not row.get("event_id") or not row.get("ts") or not row.get("host"):
                n += 1
    return n


def check_unknown_kinds(jsonl_path: Path, since_hours: int = 24) -> Dict[str, int]:
    """Return {kind: count} for kinds in last N hours NOT in KNOWN_KINDS."""
    p = Path(jsonl_path)
    if not p.exists():
        return {}
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=since_hours)
    cutoff_iso = cutoff.isoformat(timespec="milliseconds").replace("+00:00", "Z")
    unknown: Dict[str, int] = {}
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = row.get("ts") or ""
            if ts < cutoff_iso:
                continue
            kind = row.get("kind") or ""
            if kind and kind not in KNOWN_KINDS:
                unknown[kind] = unknown.get(kind, 0) + 1
    return unknown


def check_writer_health_absence(jsonl_path: Path) -> bool:
    """STUB — α.S10 fills the detection logic. Returns True (placeholder OK)."""
    return True


def run_integrity_checks(jsonl_path: Path) -> dict:
    """Aggregate result. Phase 9 calls this once per host."""
    return {
        "missing_required": check_missing_required(jsonl_path),
        "unknown_kinds": check_unknown_kinds(jsonl_path),
        "writer_health_ok": check_writer_health_absence(jsonl_path),
    }
