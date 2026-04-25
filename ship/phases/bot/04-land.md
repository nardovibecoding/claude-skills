# Phase 4: LAND (bot variant)

Post-production bookend — discipline gate before declaring done.

## OUTPUT CONTRACT (enforced for owning strict-* agents)

- WRITE the full brief to `.ship/<feature>/0N-<phase>.md` via the Write tool.
- RETURN only: (a) the artifact file path, (b) a ≤15-line summary (verdict + key counts + top 3 risks).
- NEVER include the full §0-§N body in the return message. The file on disk is the source of truth.
- Phase is not closed until `test -s .ship/<feature>/0N-<phase>.md` passes.

## Steps

1. **Strict-plan claims-vs-reality** — subagent audits: "you said X would work. Does it?" File-path citations.
2. **Smoke test** — feature VISIBLE? Log output present? Data written? Heartbeat alive? For bots: one full cycle completed end-to-end.
3. **Regression scan adjacent** — what OTHER features share code paths with the changed ones? Run quick sanity checks. **Hel-London symmetry critical** — if touching PM bot, verify both hosts still consistent.
4. **Security scan** — run through:
   - Secrets: any key/token in commit? grep commit history
   - Auth flow: new endpoint — authz checked?
   - Input validation: system boundaries validated?
   - Wallet exposure: POLY_PRIVATE_KEY path unchanged / safe?
   - Cookies/tokens: not logged? not committed?
   - Dependencies: new deps — CVE scan if relevant

   **CRITICAL finding = hard fail (no exceptions):**
   If the security scan returns ANY finding with `severity=CRITICAL`, Phase 4 MUST fail-closed. No `--force` override. Smoke test results and perf results are irrelevant — CRITICAL blocks regardless.

   The ONLY way to close Phase 4 with an open CRITICAL is a documented exception:
   - Write `.ship/<slug>/state/04-land-exception.md`
   - Include: CRITICAL finding description, why it cannot be fixed now, Bernard-approved justification (explicit ack required — auto-mode cannot approve)
   - Exception file must exist AND have Bernard's ack string before Phase 4 can close
5. **Dry-run/paper flip** (trading code) — 15-min paper mode run before live flip. Balance unchanged = proceed.
6. **Performance check (bot-specific)** — Measure → Identify → Fix → Verify → Guard:
   - **Scan loop rate** vs baseline (scans/min)
   - **Order fill latency** P50 / P99 (ms)
   - **Memory growth** over last 1h (MB/hr — alarm if >10MB/hr trend)
   - **CPU idle** % vs baseline
   - **I/O wait** — any blocking reads/writes on hot path?
   - **API rate utilization** — % of quota used per provider (Poly, Kalshi, Helius, OpenAI)
   - **Socket reconnect frequency** — stable WS vs flapping?
   - **Zombie process check** — any old copies still running? (rule from leak-audit lessons)
   - **N+1 query patterns** — batch fetches where possible
   - **Unbounded caches** — flagging growth
   - **Principle:** profile before optimizing. Measure baseline FIRST, optimize only what shows up.
7. **Lightweight CHANGELOG** — append to `~/NardoWorld/CHANGELOG.md`:
   ```
   YYYY-MM-DD | <feature> | <one-line why>
   ```
8. **Push via singlesourceoftruth** — git push + vpssync. Rule C7.

## Verdict compression (evidence-driven Phase 4 cadence)

The default observation cadence is "deploy slice K → observe T+30min → deploy slice K+1". This is a CEILING, not a floor. Verdict can fire earlier when evidence is decisive.

V1 verdict closes as soon as ANY of these is true:
- **Fingerprint window cleanly closed** — for bug fixes, the regression's known fingerprint window (e.g. T+7-10min for a wedge) passes without symptom recurrence. Document in observation log with `[isolation-verified, N=X]` label.
- **N=2 single-point comparison forms a fingerprint match** — pre-fix observation + post-fix observation, same conditions, both labelled. If they match the prior bug pattern, V1 = NEGATIVE; if post-fix observation diverges in the right direction, V1 = POSITIVE.
- **T+30 reached** — the upper bound; if no decisive evidence sooner, the full window runs.

Compressed verdict MUST be documented in the observation log with explicit "verdict at T+X (compressed from T+30 ceiling) because <fingerprint window | N=2 comparison>". Sequential-deploy mandate is preserved — it's about variable attribution, not about wall-clock duration. Skipping the wait when verdict is already in is correct discipline, not cutting corners.

Source: pm-london wedge 2026-04-25 — L1 wedge confirmed at T+11min, but protocol held us at T+30 ceiling, costing ~15 min before L3 deploy.

## Artifact

`.ship/<feature>/04-land.md` (security scan results, regression notes, perf deltas)

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
