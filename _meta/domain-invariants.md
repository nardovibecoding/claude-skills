# Skill harness Domain Invariants (DIs)

Per M1 meta-rule (`~/.claude/rules/disciplines/M1-domain-invariants.md`).

Project: `~/.claude/skills/` — meta-project; the skill harness itself.

Last updated: 2026-05-01 (initial population — STUB).

---

## Invariants

```yaml
- id: DI.1
  name: Skill SOP completeness (no stub-shipped)
  invariant: skill marked "shipped" must have all SOP step scripts present + non-stub bodies
  receipt: 2026-04-27 /upskill v1 marked shipped while SOP steps 1-6 were stub echoes (skill-route-trace-gate lesson)
  severity: HIGH (process / silent shipping of nothing)
  enforced_by: ~/.claude/hooks/skill_route_trace_gate.py + RC-1 stub-marker check
  related_F: [F2.1 init-before-use, F10.4 heartbeat]

- id: DI.2
  name: Skill route-trace coverage
  invariant: skill ship Phase 4 LAND must produce route-trace.md citing ≥3 router files for SKILL-mode targets
  receipt: 2026-04-29 /design skill three-bug-shipped-silently incident
  severity: HIGH
  enforced_by: ~/.claude/hooks/skill_route_trace_gate.py + ship.md §SKILL-mode route-trace gate
  related_F: [F2.3 phase-gating, F11.2 single-mutator, F14.2 gate-coverage]

- id: DI.3
  name: Skill security audit on install
  invariant: every external skill install via /upskill or /extractskill runs skill_security_auditor.py before write
  receipt: /upskill v2 Step 7 extract.py — security gate must PASS or extract aborts
  severity: HIGH (supply-chain)
  enforced_by: scripts/extract.py invokes skill_security_auditor.py per /upskill SKILL.md §7
  related_F: [F11.1 no-`as any`, F12 anti-AI-slop hallucinated-import]

- id: DI.4
  name: Hook idempotency
  invariant: every hook script is idempotent under repeat-firing (PreToolUse, PostToolUse, Stop, UserPromptSubmit)
  receipt: stale-prose-hook on every commit; must not double-write logs or duplicate ledger entries
  severity: MEDIUM
  enforced_by: per-hook flock + ledger dedup; partial
  related_F: [F5.2 idempotency, F1.3 resource-pair]

- id: DI.5
  name: SKILL.md frontmatter validity
  invariant: every SKILL.md has parseable YAML frontmatter (name, description, optional verified_at, optional documents)
  receipt: 2026-04-23 yaml-frontmatter-colon-pitfall (bare colons in description: break parser)
  severity: MEDIUM
  enforced_by: skill loader validates at install + invocation; runtime check
  related_F: [F3.1 schema-pair, F13.1 schema validity]

- id: DI.6
  name: Skill router precedence
  invariant: explicit project keywords trump generic; path-based trumps keyword-based; same-tier last-keyword-wins
  receipt: 2026-04-27 /ship routing rules in SKILL.md §Routing keyword priority
  severity: LOW
  enforced_by: documented in /ship SKILL.md; manual review only
  related_F: [F2.3 phase-gating, F11.2 single-mutator]
```

---

## Notes

This is a STUB. The skill harness has more DIs than enumerated here (auto-commit hook safety, MEMORY.md append discipline, .claude/projects/.../memory/ schema, etc.). Expand as receipts surface.

Activation rule (per M1): when scaffolding work touches a skill or hook, /ship Phase 1 SPEC must declare which DIs from this list are applicable.

---

## Cross-references

- M1 meta-rule: `~/.claude/rules/disciplines/M1-domain-invariants.md`
- /ship SKILL-mode route-trace gate: `~/.claude/rules/ship.md §SKILL-mode route-trace gate`
- skill_route_trace_gate hook: `~/.claude/hooks/skill_route_trace_gate.py`
- skill_security_auditor: `~/.claude/skills/upskill/scripts/skill_security_auditor.py`

Source: 2026-05-01 discipline scaffolding session.
