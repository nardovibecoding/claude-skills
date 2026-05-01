# §Discipline Impact — mandatory section template (HARD RULE)

Every `/ship` Phase 1 SPEC and Phase 2 PLAN MUST include a §Discipline Impact section with the four sub-fields below. Phase rejected if missing.

Source: 2026-05-01 discipline scaffolding session. Backed by:
- `~/.claude/rules/invariant-taxonomy.md` (F1-F16, ~60 patterns)
- `~/.claude/rules/disciplines/_index.md` (17 active + 7 blank + M1)
- `~/.claude/rules/disciplines/M1-domain-invariants.md` (per-project DIs)

---

## Mandatory sub-sections

### §X.1 — `lens:` (which F-families this slice covers)

Declare which invariant families from the taxonomy this slice's surface touches. List as a YAML-style array. Closure principle (per `~/NardoWorld/lessons/2026-05-01_code-invariant-taxonomy.md`): bugs OUTSIDE the declared lens are out-of-scope, not missed.

```yaml
lens: [F1.1, F1.4, F4.5, F10.1]
```

Each F-code carries its rationale in 1 line:
- `F1.1` — slice mutates portfolio.json fields paired with traceEvent
- `F1.4` — portfolio.json is cached in dashboard reader
- `F4.5` — capital conservation invariant must hold post-slice
- `F10.1` — every state transition in slice must emit a trace event

### §X.2 — `applicable_DIs:` (project domain invariants this slice could affect)

Per M1 meta-rule. Read `<project>/.ship/_meta/domain-invariants.md`; list which DIs this slice's surface could violate. Phase 4 LAND must verify each listed DI still holds post-deploy.

```yaml
applicable_DIs: [DI.1, DI.3, DI.7, DI.9]
```

If `applicable_DIs:` is empty, justify in 1 line: "this slice does not affect any domain invariant because <reason>". Empty without justification = phase rejected.

### §X.2b — `applicable_concerns:` (project quality-axis concerns this slice could affect)

Per M2 meta-rule. Read `<project>/.ship/_meta/concerns.md`; list which C-codes (C1-C7) this slice's surface could touch. Phase 4 LAND must verify each listed concern's threshold still holds post-deploy; concern-receipt appended to `~/.claude/scripts/state/concern-receipts.jsonl`.

```yaml
applicable_concerns: [C1, C3, C7]
```

C-codes from `~/.claude/rules/concerns-taxonomy.md`:
- C1 Cost / C2 Resilience / C3 Behavioral / C4 External drift / C5 Model accuracy / C6 Stress / C7 Security

If `applicable_concerns:` is empty, justify: "no concerns affected because <reason>". Empty without justification = phase rejected.

### §X.3 — `disciplines:` (which active disciplines this slice activates)

Map each entry in `lens:` to one or more disciplines from `~/.claude/rules/disciplines/_index.md`. This makes the enforcement axis explicit.

```yaml
disciplines:
  D1:  # SSOT
    f_families: [F1.4, F11.2]
    detection: write-time grep + plan-time call-graph audit
  D5:  # Lifecycle pair
    f_families: [F1.1, F10.1]
    detection: write-time grep + Phase 4 LAND trace-emit count check
  D14:  # Quantitative
    f_families: [F4.5]
    detection: runtime conservation assertion every 15min
```

**Note (added 2026-05-02 ship-discipline-detector-runner):** the `detection:` field above is human-readable description for the slice. The MACHINE-EXECUTABLE detection (run by RC-11 at Phase 4 LAND) lives in the discipline's rule file at `~/.claude/rules/disciplines/<file>.md` under `## detection_runner` as a structured YAML block (type/scope/pattern/max_violations/etc.). If the rule file lacks a `detection_runner:` block, RC-11 will mark the discipline UNRUNNABLE and BLOCK phase close — fix by either adding the block (see ssot.md / lifecycle-pair.md as canonical examples) or by adding `[skip-detector: <D-code> reason=<text>]` to the slice plan/spec. Drift between the prose `## Detection` table and the `detection_runner:` block in a discipline file = D1 SSOT violation against that discipline file.

### §X.4 — `gaps:` (F-families touched but with NO active discipline coverage)

If `lens:` includes any F-family that maps only to a blank-titled discipline (e.g. F2.x ordering, F12.x equivalence), flag it explicitly. Slice author chooses:
- **gap_action: accept** — out-of-scope; explicit in slice scope
- **gap_action: build_detector** — slice will land a detector for the blank discipline (promotes blank → active per ratchet rule, requires ≥10 receipts justification)
- **gap_action: defer** — note for next slice; current slice does not address

Empty when no gaps. Phase rejected if gap exists but no `gap_action:` declared.

---

## Receipt logging (Phase 4 LAND)

After Phase 4 LAND closes, append a receipt to `~/.claude/scripts/state/discipline-receipts.jsonl` per discipline this slice violated AND closed:

```json
{"ts": "2026-05-01T08:30:00Z", "discipline": "D1", "source": "/ship", "slug": "<slug>", "violation_class": "F1.4 cache-mirror", "severity": "HIGH"}
```

This feeds the ratchet rule: when a discipline accumulates ≥10 receipts in 30d, daemon-detector wire-up is triggered (per `~/.ship/bigd-discipline-detector-mapping/goals/01-spec.md` activation gate).

---

## Phase-close gates (HARD RULE)

| gate | rule |
|---|---|
| G-D1 | §X.1 `lens:` non-empty OR phase rejected |
| G-D2 | §X.2 `applicable_DIs:` populated OR explicit "no DIs affected because <reason>" justification |
| G-D3 | §X.3 every F-family in lens maps to ≥1 D-discipline (active OR blank-titled) |
| G-D4 | §X.4 every gap has `gap_action:` declared |
| G-D5 | Phase 4 LAND closes by appending receipts to `discipline-receipts.jsonl` |

Source: matches `rules/ship.md` Iron Laws — these gates are additive enforcement, not replacements.

---

## Worked example (recent slice)

Slice: `pm-engine-pipeline-respec` slice 1 (failure-branch trace at standalone-exec)

```yaml
lens: [F1.1, F10.1]
  # F1.1 — emit/exec/record state-pair on standalone exec path
  # F10.1 — every state transition emits trace event

applicable_DIs: [DI.3]
  # DI.3 resolution-state consistency (resolved=true ⟹ exitPrice + exitReason)

disciplines:
  D5:
    f_families: [F1.1, F10.1]
    detection: write-time grep for traceEvent({event:"exec"}) co-located with appendJournalEntry()
  D3a:
    f_families: [F10.1]
    detection: schema-fixture test for TraceEvent shape (deferred to D-blank-4 when test infra lands)

gaps:
  - F12.x equivalence — emit/parse round-trip not tested (D-blank-4)
    gap_action: defer
    rationale: blank discipline; activate when test-infra investment lands

# Phase 4 LAND log:
# - 1 receipt appended for D5 (slice closed F1.1+F10.1 gap on standalone path)
```

Source: 2026-05-01 discipline scaffolding session. Apply this template to every Phase 1+2 brief from now on.
