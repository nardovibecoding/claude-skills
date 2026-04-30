# Phase 10: System-drift scan (hooks/agents/LaunchAgents/scripts)

Cross-surface drift detector. Same accumulation pattern shows up in `~/.claude/hooks/`, `~/.claude/agents/`, `~/.claude/scripts/`, and `~/Library/LaunchAgents/com.bernard.*` — `.bak` cruft, zombie `.disabled`, orphans, rescinded-but-still-wired guards, mergeable settings.json stanzas, dot-vs-dash collisions. One scanner covers all four.

```bash
python3 ~/.claude/skills/lint/scripts/system_drift_scan.py --severity LOW
```

Flags:
- `--surface hooks|agents|scripts|launchagents|all` — scope (default all)
- `--severity LOW|MEDIUM|HIGH` — minimum severity
- `--json` — machine-readable

Drift codes detected:
- **D1** `.bak*` / `.disabled.<phase>` cruft — replaced=deleted rule violated
- **D2** zombie `.disabled` — kept per Bernard's rule, surface for review (not deleted)
- **D3** `.disabled` + live counterpart present — conflict
- **D4** orphan — on disk, not wired in settings.json, not dispatcher-routed (importlib), not imported, not referenced from skills/rules/CLAUDE.md/hooks/LaunchAgents
- **D5** dot-vs-dash naming collision (LaunchAgents) — duplicate scheduling risk per `rules/infra.md` §LaunchAgent naming canon
- **D6** rescinded-but-still-wired — file body has `FORBIDDEN_*=[]` or `# RESCINDED` comment but settings.json still calls it
- **D7** stanza-merge candidate — settings.json has multiple stanzas with same matcher in same event
- **D8** `launchctl`-loaded but plist file missing — orphan launchd unit

## Wired detection (HARD RULE — learned 2026-04-30)

Naive grep misses dispatcher routing. The B4 orphan-sweep almost deleted 40 LIVE hooks because they're loaded via `dispatcher_pre.py` / `dispatcher_post.py` `importlib.util` at runtime. Phase 10 explicitly checks both:
- direct `command:` paths in settings.json
- string literals inside `dispatcher_*.py` that match `"<name>.py"` pattern

For agents + scripts, wiring detection is a recursive grep across skills, rules, CLAUDE.md, hooks, and LaunchAgents — agents are referenced via `subagent_type: <name>`, scripts via path strings inside plists or hook commands.

## NOT auto-fix

Phase 10 reports findings; deletion is gated. Each `.bak` and `.disabled.<phase>` is safe-delete (HIGH precision). Each `D4 orphan` requires human confirmation — false positives possible if a script is invoked via shell alias / external repo / TG bot / cron not yet covered.

For batch-cleanup of LaunchAgent cruft (D1 only), safe-fix:
```bash
python3 ~/.claude/skills/lint/scripts/system_drift_scan.py --surface launchagents --json | \
  jq -r '.[] | select(.code=="D1") | .path' | xargs -n1 rm -v
```

Skip Phase 10 for `/lint --quick` (slow due to recursive greps).

Source: 2026-04-30 hooks consolidation. 144 hook files, ~190k of `.bak` cruft, 2 rescinded-but-wired london guards, 11 mergeable settings.json stanzas, 4 LaunchAgent `.disabled.bigd-repair-phase5` zombies — none of which any existing /lint phase would have caught.
