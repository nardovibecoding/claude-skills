# /debug Drift mode (Group A — symptom-first → cause)

Per master plan §3 compression matrix row "Drift": run steps 0,2,3,4,5,7,9,10,13,15,16. Light pass on 1,6,11. Skip 8,12,14.

Symptom: "X used to work, now silently stale". Code/data moved under a feature; verify_cmd output diverges from baseline.

---

## Iron Laws (verbatim from `~/.claude/skills/_iron_laws.md`)

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

Drift mode is **advisory only** — it never auto-patches. It emits countermeasures + writes the ledger; Bernard or another /ship slice applies the fix.

---

## Steps

### Step 0 — TRIAGE
Parse `<feature>` (`host:feature` or `feature`); identify mode=drift; capture `--baseline=<sha-or-iso>` flag (default `30 days ago`).

Failure: empty feature → `INVALID_INPUT`.

### Step 1 — REPRODUCE (⚡ light)
Resolve baseline ref. If `--baseline=<sha>` provided, use as anchor. Else `git log --since='30 days ago' -1 --format=%H` on the feature's repo. On shallow clone failure, fall back to `HEAD~100`.

### Step 2 — BUILD-MAP
Read pipeline_graph + data_lineage; substring match feature name; report node + edge matches.

### Step 3 — EXECUTION-MAP
Read state_registry + sync_graph; capture `verify_cmd` for the feature's host process node.

### Step 4 — DEPENDENCY-MAP
Read consistency_registry; query for `wiring_drift`, `content_schema_drift`, `config_wiki_drift`, `graph_filesystem_drift` signals matching feature.

### Step 5 — PATTERN ANALYSIS
`git log --oneline <baseline>..HEAD -- <files>` for the feature's defining files. Count commits + report top 5 messages.

### Step 7 — EXPECTED-SIGNAL
What should still be true if feature is current? (e.g. verify_cmd exits 0 with same fingerprint as baseline.)

### Step 9 — RUNTIME-VERIFY
Run state_registry verify_cmd if exists; capture exit + stdout. On `--dry-run`, synthesize a stub observation.

Append to `~/.ship/<drift-slug>/experiments/observations.md` per `~/.claude/rules/ship.md` § Observations log with `[single-point]` label.

### Step 10 — CLASSIFY
- `current` — verify_cmd output matches baseline; no commits in range touching feature files.
- `stale-soft` — commits exist but verify_cmd still passes (drift but no impact yet).
- `stale-hard` — verify_cmd output diverges (production impact).
- `inconclusive` — verify_cmd missing or unexecutable; baseline missing.

### Step 11 — DEPTH-CHECK (⚡ light)
5-Whys lite on drift cause: why did the upstream change touch this feature? Single chain step OK; no full causal-chain artifact required (skip Step 14 cleanup).

### Step 13 — FIX (advisory only)
NEVER auto-patch. Emit countermeasures:
- immediate: re-run/refresh feature
- preventive: add to consistency-daemon detector watch (per master plan §19)
- detection: schedule periodic /debug drift check

### Step 15 — VERDICT-VERIFY
Iron Law #2 — fresh evidence in this invocation; no inheritance from prior runs.

### Step 16 — LEDGER
Write entry: `mode: drift`, `status: open` (default) or `drift-fixed` if external fix applied.

---

## Verdict matrix

| verify_cmd output | commits in range | Verdict |
|---|---|---|
| matches baseline | 0 | `current` |
| matches baseline | ≥1 | `stale-soft` |
| diverges | ≥1 | `stale-hard` |
| diverges | 0 | `inconclusive` (something else changed) |
| n/a | (any) | `inconclusive` |

Exit codes: 0=current, 1=stale-{soft,hard}, 2=invalid, 3=inconclusive.

---

## Output

JSON to stdout + ledger entry. Plus ≤10-line human summary.

---

## Cross-refs

- `~/.claude/CLAUDE.md` § Epistemic discipline (Evidence-tagging, Causal-claim gate)
- `~/.claude/rules/ship.md` § Observations log
- master plan §3 (compression matrix), §9 (ledger schema)
