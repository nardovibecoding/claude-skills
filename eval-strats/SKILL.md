---
name: eval-strats
description: Strategy evaluation skill for PM bots. Reads signal-trace + trade-journal + eval-history from Hel/London PM bots; computes per-strategy metrics (signals/gates/exec, pipeline %, edge accuracy, fee drag) + 11 bug flags (WIRING / SCAN_SPAM / FEE>100% / TIMEBOX_MISMATCH / EDGE_ANTI / FEE_DOMINANT / PAUSED / ALL_GATED / GHOST_SOURCE / STALE_DATA / SELF_IMPACT). Outputs markdown table + JSON snapshot at data/strat-eval-snapshot.json + appends row to strategy_logbook.xlsx Daily history. Triggers — "/eval-strats", "eval my strategies", "strategy eval", "which strategies are working", "find broken strategies", "strategy bug flags". NOT FOR — placing trades (read-only audit), London-host this MVP (Hel only — London comes in v1.1), Brier score (deferred to v2). Produces — sortable markdown table, JSON sidecar for future dashboard tab, daily logbook row with format_version=2.
---

# eval-strats

Strategy evaluation skill — Hel-host MVP (Kalshi).

## Invocation

```
python3 ~/prediction-markets/scripts/eval_strats.py [--host=hel|london|local] \
                                                     [--platform=kalshi|poly|all] \
                                                     [--strategy=<name>] \
                                                     [--json] [--no-write] [--snapshot-only]
```

Default: `--host=hel --platform=kalshi`. MVP scope is Hel only — London host fully wired in v1.1.

## What it does

1. **Fetches** signal-trace.jsonl (last ~80MB), trade-journal.jsonl, eval-history.jsonl, config.hel.json, portfolio.json mtime via `ssh hel`.
2. **Computes** per-strategy 24h window metrics: emit / gate / exec / record counts, pipeline % (exec/emit), silent drops (orphan traceIds), top gate reason, top gate market, edge accuracy from trade-journal.
3. **Flags bugs** per spec §2.3 (11 flags). Includes PAUSED with sub-reason (cooldown / kill_switch / manual_disable / not_in_config / host_filter).
4. **Writes** markdown table to stdout, JSON snapshot to `data/strat-eval-snapshot.json`, appends/updates row in `data/strategy_logbook.xlsx` Daily history (with flock on `/tmp/pm_logbook.lock` and atomic-swap copy pattern — same as `update_logbook.py`).

## Verification

Unit tests at `~/prediction-markets/scripts/test_eval_strats_bugs.py` (11 cases, all pass).

End-to-end on Hel produces:
- markdown table with WIRING flag on dutch_book + calibration_arb (silent drops > 0)
- SCAN_SPAM flag on dutch_book (KXERUPTSUPER market dominates gates)
- TIMEBOX_MISMATCH flag on dutch_book (UNRESOLVED timebox exits)
- FEE_DOMINANT flag on calibration_arb / panic_fade / price_spike
- PAUSED flag on correlation (in disabledSources)
- ALL_GATED flag on sports_edge

## Output paths

- markdown: stdout
- JSON snapshot: `~/prediction-markets/data/strat-eval-snapshot.json`
- xlsx Daily history append: `~/prediction-markets/data/strategy_logbook.xlsx`
- format_version=2 stamped in `Read me` sheet

## Deferred (not in this MVP)

- Dashboard tab (separate `dashboard-strat-eval.ts` work)
- London host parity (only Hel wired this pass)
- Backfill from `signal_history.jsonl.stale-apr17` (schema-add only this run)
- Brier score (v2)
- SELF_IMPACT flag (needs market-volume cross-ref; v1.1)
- Cooldown / kill_switch runtime state polling (not_in_config / host_filter detection done; runtime state needs bot RPC)

## Spec source

`~/prediction-markets/.ship/strat-eval-skill/01-draft-plan.md` (rev 4, locked 2026-04-26).
