# Phase 4: LAND (app variant — full release hygiene)

Full ritual — users depend on quality.

## OUTPUT CONTRACT (enforced for owning strict-* agents)

- WRITE the full brief to `.ship/<feature>/0N-<phase>.md` via the Write tool.
- RETURN only: (a) the artifact file path, (b) a ≤15-line summary (verdict + key counts + top 3 risks).
- NEVER include the full §0-§N body in the return message. The file on disk is the source of truth.
- Phase is not closed until `test -s .ship/<feature>/0N-<phase>.md` passes.

## Steps

1. **Strict-plan claims-vs-reality audit**
2. **Smoke test** — full user journey clicked through (or automated)
3. **Coverage audit** — untested code paths mapped; generate minimum tests for critical paths
4. **Regression scan** — adjacent features broken?
5. **Security scan** (addyosmani security-and-hardening):
   - Secrets: no leaks
   - Auth: authz checked on new endpoints
   - Input validation at boundaries (XSS, SQLi, CSRF)
   - Dependencies: vuln scan (`npm audit` / `pip-audit` / `gh audit`)
   - PII handling: encrypted at rest + in transit
   - Rate limiting: prevent abuse

   **CRITICAL finding = hard fail (no exceptions):**
   If the security scan returns ANY finding with `severity=CRITICAL`, Phase 4 MUST fail-closed. No `--force` override. Smoke test and perf results are irrelevant — CRITICAL blocks regardless.

   The ONLY way to close Phase 4 with an open CRITICAL is a documented exception:
   - Write `.ship/<slug>/state/04-land-exception.md`
   - Include: CRITICAL finding description, why it cannot be fixed now, Bernard-approved justification (explicit ack required — auto-mode cannot approve)
   - Exception file must exist AND have Bernard's ack string before Phase 4 can close
6. **Performance check (web-app)** — Measure → Identify → Fix → Verify → Guard:
   - **Core Web Vitals:**
     - LCP ≤ 2.5s (largest contentful paint)
     - INP ≤ 200ms (interaction to next paint)
     - CLS ≤ 0.1 (cumulative layout shift)
   - **Bundle size** check — CI-enforced perf budget
   - **Backend bottlenecks:** N+1 queries, unbounded fetches, missing indexes, unoptimized SQL, heavy sync compute, missing cache layers
   - **Frontend optimizations:** image dimensions + lazy load, responsive `<picture>`, AVIF/WebP, route-split, render-blocking elimination, memoization (don't overuse)
   - **Infra:** HTTP/2, keep-alive, DNS prefetch, edge deploy, cache headers, content hashing
   - **Anti-patterns to avoid:** over-useMemo/memo, framework assumption without profiling, optimizing without measurement
   - **Principle:** profile before optimizing. Lighthouse CI + web-vitals RUM in prod.
7. **VERSION bump + CHANGELOG** — SemVer (major.minor.patch)
   - Breaking → major
   - Feature → minor
   - Fix → patch
8. **Release notes** — user-facing: what changed, what matters, migration guide
9. **Staging deploy** (if env exists) → verify → production
10. **PR workflow** (if GitHub collab) → code review → merge
11. **Rollback ready** — tag + documented command

## Artifact

`.ship/<feature>/04-land.md` (release notes, security scan results, test coverage, perf deltas)

---

## §4.5 — DEPLOY GATES (mandatory when feature adds cron / timer / scheduled job / background worker)

Same gates as bot/04-land.md §4.5. Apps with backgrounded jobs / scheduled workers / queues must declare:

```yaml
produces: <output_path or topic>
consumed_by: <next_stage_unit>
chain_method: synchronous_call | done_marker | event_trigger   # NEVER schedule_coincidence
failure_mode_when_upstream_late: retry_next_tick | block_with_timeout | degrade_with_warning
```

When the feature adds a NEW producer to an existing N-producer system, every consumer's expected count must be bumped in the same commit.

After deploy, run `python3 ~/.claude/skills/debug/bin/debug.py race <feature> --dry-run`. Verdict must be `race_free`. See bot/04-land.md §4.5 for full rationale.

---

## Owning Agent

**strict-execute + strict-plan** — use this agent's brief template for the phase artifact.

## SPREAD/SHRINK pass (required before closing phase)

**SPREAD (L1-L5):**
- L1 Lifecycle — create + update + retire covered?
- L2 Symmetry — every action has counterpart (write+delete, enable+disable)?
- L3 Time-lens — 1d / 30d / 365d behavior considered?
- L4 Scale — works at 10x inputs?
- L5 Resources — CPU/disk/network/tokens accounted for?

**SHRINK (Sh1-Sh5):**
- Sh1 Duplication — same logic repeated elsewhere?
- Sh2 Abstraction — premature or correct?
- Sh3 Retirement — what's now orphaned by this change?
- Sh4 Merge — can this fold into existing?
- Sh5 Simplification — can this be fewer lines?

Phase is NOT closed until all 10 items answered.
