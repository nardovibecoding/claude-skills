# /debug Wiring mode (Group B — feature-first → runtime)

Per master plan §3 compression matrix row "Wiring": run steps 0, 2, 3, 4 (with pre-S5 fallback), 9, 16. Skip 1, 5-8, 10-15.

## Inputs

- `<target>` = `<host>:<feature>` or `<feature>`
- Read-only access to `~/NardoWorld/meta/{state_registry,pipeline_graph,data_lineage,sync_graph,consistency_registry}.json`
- Optional: feature-level evidence sources (ship execution logs in `~/.ship/<slug>/experiments/`, git log on the relevant repo, journal grep on the host)

## Honest layering note (premise re-verified 2026-04-26 in S1)

Phase 4 graphs are **process-level** (systemd units, file producers/consumers, host-host syncs). They do NOT enumerate feature-level wiring (e.g. whether `prewarmPrepared` is threaded through `executeSignal` at main.ts:2125). Feature-level wiring lives in:
- `~/.ship/<slug>/experiments/03-execution-log.md` (the ship's own visible-proof section)
- git log on the target repo (`wired-commit` SHA in the ledger entry)
- live journal grep on the host (`[prewarm] signed N/N` style log lines)

Wiring mode therefore combines (a) Phase 4 process-level liveness with (b) feature-level evidence pointers, and reports both in the verdict. A feature can be `wired` (process active + ship evidence cited) even when it has zero Phase 4 graph entries — Phase 4 records the host process, the ledger records the feature.

## Steps

### Step 0 — TRIAGE
Parse `<target>` into `(host?, feature)`. Resolve `host` via state_registry if omitted. Identify mode: this phase = mode 2 Wiring. Confirm caller used a Group B trigger phrase or `/debug check`.

Failure: if `<feature>` is empty → return `INVALID_INPUT`, do not proceed.

### Step 2 — BUILD-MAP (Phase 4 L1 + L3, read-only)
Load `pipeline_graph.json` + `data_lineage.json`. Find any node whose `id`, `exec`, `writes`, or any field references the feature name (case-insensitive substring). Report `phase4_node_matches: [...]`. Empty match is OK and expected for sub-process features (see honest layering note).

### Step 3 — EXECUTION-MAP (Phase 4 L1 + L2, read-only)
Load `state_registry.json` + `sync_graph.json`. Find the host process node (e.g. `pm-bot@london`). Capture `status`, `verify_cmd`, `intent_fields`. This proves the **process** the feature lives inside is wired into Big-SystemD.

### Step 4 — DEPENDENCY-MAP (Phase 4 L4 + orphan-sweep)
Load `consistency_registry.json`. Look for utilization_drift / orphan signals matching the feature.

**Pre-S5 fallback (per master plan §16):** `orphan_registry.json` does NOT exist yet (S5 ships it). When absent, treat as empty + flag `dependency_map: partial (pre-S5: orphan_registry not yet seeded)` in the verdict block. Do NOT block S1 on this.

### Step 9 — RUNTIME-VERIFY
Per Iron Law #2 (`NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE`), the verdict requires **fresh evidence in this invocation**, not inherited from prior runs.

Evidence sources, in order of preference:
1. **Live process check** — `systemctl is-active <unit>` on the target host (read from state_registry verify_cmd). Sufficient for `wired` only when feature ≡ process (e.g. `kalshi-bot.service` itself).
2. **Live feature signal** — host journal/log grep for the feature's distinctive log marker. Sufficient for `wired` when paired with (1).
3. **Ship execution log evidence** — `~/.ship/<slug>/experiments/*.md` containing visible-proof block + git SHA. Used when (2) is not directly grep-able from this session, but the ship was Bernard's last action; ledger entry must record the SHA + the visible-proof excerpt verbatim.

Verdict matrix:

| (1) process active | (2) live feature signal | (3) ship evidence | Verdict |
|---|---|---|---|
| ✓ | ✓ | ✓ or n/a | `wired` |
| ✓ | ✗ | ✓ (within 24h) | `wired` (with note: relying on ship-log evidence; freshness=ship-log timestamp) |
| ✓ | ✗ | ✗ | `partial` (process up but feature wiring unverified) |
| ✗ | n/a | n/a | `not_wired` |
| (any) | (conflicting) | (any) | `inconclusive` — STOP and surface the conflict |

### Step 16 — LEDGER write
Append entry to `~/NardoWorld/realize-debt.md` per master plan §9 schema. ID = max existing `R-NNNN` + 1, zero-padded. Idempotency: if an entry already exists with same `(ship_slug, feature_name)` and status `wired`, do NOT duplicate — log `(dedup'd against existing R-NNNN)` and return the existing ID.

## Output format

JSON to stdout, suitable for /ship Phase 4 LAND hook to parse:

```json
{
  "verb": "check",
  "target": "<host>:<feature>",
  "verdict": "wired|partial|not_wired|inconclusive",
  "phase4_evidence": {
    "state_registry": {"node_id": "...", "status": "..."},
    "pipeline_graph": {"node_matches": [...], "edge_matches": [...]},
    "data_lineage": {"collector_matches": [...]},
    "consistency_registry": {"signals": [...]}
  },
  "feature_evidence": {
    "ship_log": "<path>",
    "wired_commit": "<sha>",
    "visible_proof_excerpt": "..."
  },
  "dependency_map": "ok|partial (pre-S5: orphan_registry not yet seeded)",
  "ledger_entry": "R-NNNN",
  "freshness": "<iso8601 of evidence>"
}
```

Plus a human-readable summary printed after the JSON (one block, ≤10 lines).

## Iron-Law self-check before returning verdict

Before printing `wired`:
- Did Step 9 actually read fresh evidence in THIS invocation? (not "should be wired", not "was wired last time")
- Are Phase 4 file paths cited in `phase4_evidence`?
- Is the freshness timestamp on the evidence < 24h old?

If any answer is no → downgrade verdict by one rung (`wired` → `partial`, `partial` → `inconclusive`).

## Causal-claim gate (per ~/.claude/CLAUDE.md)

The verdict `wired` is a causal claim ("the feature is in production"). Before printing it, silently run the 3-question gate:
(a) What else changed between "not wired" and "wired" observation? → must be the wiring commit, not coincident other commits.
(b) Single snapshot or N≥2? → live process check + ship log = N=2 minimum.
(c) Inherited premise? → no, freshness check above forbids it.

If any answer is fuzzy → downgrade to `partial`.
