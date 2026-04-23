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
