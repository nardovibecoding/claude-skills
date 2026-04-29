"""
/debug performance detector pack (P1-P4).

Symptom-first inventory: when user types `/debug performance <host>`,
cmd_performance fires all four detectors via run_all() and writes
per-detector findings to <perf_slug>/experiments/p<N>-<name>.md.

P1 = zombie procs (defunct, ps STAT contains 'Z')
P2 = orphan procs (PPID=1, not in expected init-adopted allowlist)
P3 = hot-loop procs (sustained CPU >5% over 2 samples 3s apart)
P4 = leak suspects (top RSS hogs + flag any growing >5% over 30s sample)

Each detector exposes `scan(host: str) -> dict` returning:
  {"detector": "<id>", "host": <host>, "findings": [...], "verdict": "ok|warn|crit",
   "evidence_cmd": "<the shell cmd actually executed>",
   "summary": "<one-line>"}

Detectors are read-only. SSH timeout 10s. Failures degrade to verdict="error"
with a `gap` note instead of crashing the verb.
"""
from __future__ import annotations

from . import p1_zombie, p2_orphan, p3_hot_loop, p4_leak

DETECTORS = [
    ("p1-zombie", p1_zombie),
    ("p2-orphan", p2_orphan),
    ("p3-hot-loop", p3_hot_loop),
    ("p4-leak", p4_leak),
]


def run_all(host: str) -> list[dict]:
    """Run every detector against host. Never raises."""
    results = []
    for label, mod in DETECTORS:
        try:
            r = mod.scan(host)
        except Exception as e:
            r = {"detector": label, "host": host, "findings": [], "verdict": "error",
                 "evidence_cmd": "", "summary": f"detector crashed: {type(e).__name__}: {e}"}
        r.setdefault("detector", label)
        r.setdefault("host", host)
        results.append(r)
    return results
