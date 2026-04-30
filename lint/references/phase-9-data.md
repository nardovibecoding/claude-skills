# Phase 9: data-hygiene

Two scopes: **bot-data** (per-host `packages/bot/data/*`) and **SSOT log** (`~/NardoWorld/meta/ssot/`). Read-only by default; auto-prune behind `--fix`.

Implementation: `~/.claude/skills/lint/scripts/phase9_data_hygiene.py` (single script, both scopes).

## Scope A — Bot-data hygiene

For each host (hel, london — mac has no bot data dir per file-map):

1. **Cross-platform pollution** — flag files violating platform-split:
   - hel files matching `^(clob_|polymarket_|poly_)` → flag (Kalshi-only host should not have Polymarket data)
   - london files matching `^kalshi_` → flag (Polymarket+Manifold host should not have Kalshi data)
   - Report file size + last-write time per flagged file.
2. **Dead deprecated** — read `~/NardoWorld/projects/prediction-markets/file-map.md`, find rows tagged `DEPRECATED` (e.g. `trades.jsonl`), check on-disk presence per host → flag with size.
3. **Oversized log** — any file >500MB in `packages/bot/data/` → warn (suggests rotation backlog).
4. **File-map drift** — files on disk but not present in file-map prose → flag `[unverified]` (must be added to file-map after verification per CLAUDE.md §Data file maps).

Auto-fix: warn-only for all 4 (manual decision — prose update + cross-host data is wallet-adjacent).

## Scope B — SSOT log hygiene

For each host (mac always; hel + london when `~/NardoWorld/meta/ssot/ssot.jsonl` exists):

1. **Size check** — `stat ssot.jsonl`. WARN if >500MB. Auto-fix: rotate (rename to `ssot.YYYYMMDD-HHMMSS.jsonl.gz`, gzip async).
2. **Retention prune** — list `ssot.YYYYMMDD-HHMMSS.jsonl.gz`; delete if mtime >90d. Auto-fix: delete under `--fix`.
3. **Schema drift** — sample 100 random rows via `shuf -n 100 ssot.jsonl`. For each row, verify required fields present: `ts`, `host`, `event_id`, `kind`, `actor`, `subject`, `outcome`. Count rows missing any. WARN if any missing. Auto-fix: warn-only (writer bug, not lint's job to repair).
4. **Writer-gap detection** — query via `~/.claude/scripts/ssot-query.sh "SELECT host, MAX(ts) AS last_ts FROM ssot GROUP BY host"`. For each host, compare `last_ts` to now. If >1h gap AND host has expected active source (Claude session running on mac/hel OR `systemctl is-active pm-bot|kalshi-bot` returns active on london/hel), flag FAIL. Auto-fix: warn-only.
5. **Per-host parity** — confirm all expected hosts (mac always; hel when S3 ships; london when S4 ships) have produced ≥1 event in last 24h. Flag missing as WARN.

Auto-fix: rotate (1) + retention prune (2) under `--fix`. Drift (3), writer-gap (4), parity (5) = warn-only.

## Capacity additions

Add to capacity table (printed at end of /lint run):

| Metric | Healthy | Warning | Critical |
|---|---|---|---|
| bot-data total / host | <5GB | 5-10GB | >10GB |
| SSOT log size / host | <100MB | 100-500MB | >500MB |
| SSOT writer gap (any host) | <1h | 1-6h | >6h |

## Inputs (read every invocation, no cache)

- `~/NardoWorld/projects/prediction-markets/file-map.md` — re-read each run (DEPRECATED rows, full filename inventory)
- `ssh hel/london ls ~/prediction-markets/packages/bot/data/` — live disk state
- `~/.claude/scripts/ssot-query.sh` — writer-gap query

## Failure modes

- SSH timeout to hel/london → script catches, logs `[SKIP host=X reason=ssh-timeout]` as WARN, continues. Never crashes.
- `ssot-query.sh` missing/broken → log `[SKIP scope=ssot reason=query-helper-unavailable]`, continue with bot-data scope.
- file-map.md missing → log `[SKIP scope=bot-data-deprecated reason=file-map-missing]`, continue with pollution + size scopes.

## Invocation

| flag | scope |
|---|---|
| `/lint` (no flag) | runs Phase 9 alongside other phases |
| `/lint --data` | Phase 9 only |
| `/lint --bot-data` | Phase 9 only (synonym) |
| `/lint --data --fix` | runs auto-prune for size/retention |

Skip Phase 9 for `/lint --quick`. Unattended mode runs Phase 9 in dry-mode (warn-only, no `--fix`).

## Heuristics

- **H2 schema-drift detector** (`detect_schema_drift`): regex/structural rule set, validated per ship.md HARD RULE — see `~/.ship/ssot-log/experiments/heuristic-validation.md` H2 section.
- **H3 path classifier** (`classify_pollution`): regex `^(clob_|polymarket_|poly_)` (poly-side) and `^kalshi_` (kalshi-side), validated per ship.md HARD RULE — see same file H3 section.
