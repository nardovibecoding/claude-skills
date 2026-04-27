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
5. **Wiring-check via /debug (HARD GATE — master plan §6)** — for every named feature delivered in this slice, run:
   ```bash
   python3 ~/.claude/skills/debug/bin/debug.py check <host>:<feature>
   ```
   Parse the `--- /debug check <target> → verdict: <X> ---` line. Per CLAUDE.md "compiles ≠ works" Realization Check, only `verdict: wired` allows phase close. `not_wired`, `partial`, `inconclusive` BLOCK Phase 4 close — fail-closed, no `--force` override.

   **Why:** /debug check confirms (a) process is ACTIVE in state_registry, (b) ship-log feature evidence ≤48h old, (c) Phase 4 graphs reference the feature. Build passing means nothing if the named feature isn't actually live in the running process. This gate converts the soft Realization Check into an enforced phase-close condition.

   **Ledger writer ownership:** /debug writes `~/NardoWorld/realize-debt.md` automatically. /ship NEVER writes the ledger directly — only reads back the verdict. Idempotency: /debug dedups against existing entries by `(ship_slug, feature, host)`, so re-running the check during a Phase 4 retry is safe.

   **The ONLY way to close Phase 4 with verdict ≠ wired:**
   - Write `.ship/<slug>/state/04-wiring-override.md`
   - Include: feature name, current verdict, why it cannot reach `wired` now (e.g. "feature is data-producer; downstream consumer ships next slice"), Bernard-approved justification (explicit ack required — auto-mode cannot approve)
   - Override file must exist AND have Bernard's ack string before phase close
   - Override is logged in the ledger entry as `--ship-override-wiring=advisory`

   **Feature naming:** pull from Phase 1 spec §EARS ACs ("the system shall..."). One /debug check per acceptance-criterion-named feature. If 3 ACs name 3 features, run 3 checks.

6. **Dry-run/paper flip** (trading code) — 15-min paper mode run before live flip. Balance unchanged = proceed.
7. **Performance check (bot-specific)** — Measure → Identify → Fix → Verify → Guard:
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
8. **Lightweight CHANGELOG** — append to `~/NardoWorld/CHANGELOG.md`:
   ```
   YYYY-MM-DD | <feature> | <one-line why>
   ```
9. **Push via singlesourceoftruth** — git push + vpssync. Rule C7.

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

## §4.5 — DEPLOY GATES (mandatory when feature adds cron / timer / LaunchAgent / systemd unit)

**Born from Apr 27 2026 bigd 6th-daemon race.** Bundle assembler ran 4-15s before slow daemons finished, captured 8/18. Pure timing race, not daemon bug. Three independent timers schedule-coincided. The fix below prevents every future variant.

### G2 — Producer-consumer chain declaration (in artifact)

Every new daemon/timer artifact MUST contain a `## Producer-consumer chain` block:

```yaml
produces: <output_path or topic>          # e.g. ~/inbox/_summaries/pending/<DATE>/<daemon>_<host>.json
consumed_by: <next_stage_unit>            # e.g. bigd-collector
chain_method: synchronous_call | done_marker | event_trigger
                                          # NEVER schedule_coincidence
```

If any of these fields is missing or `chain_method == schedule_coincidence`, **Phase 4 cannot close.**

### G3 — Failure-mode declaration

What happens when upstream finishes late? Required choice in artifact:

```yaml
failure_mode_when_upstream_late: retry_next_tick | block_with_timeout | degrade_with_warning
```

`assume_complete` or absent → FAIL.

### G4 — Refactor-proof contract (when adding a NEW producer to existing system)

When the feature adds a producer to an existing N-producer system, the same PR MUST bump every consumer's expected count. Phase 4 reviewer checklist:

- [ ] Searched callers of `_DAEMONS` / `_KNOWN_DAEMONS` / `EXPECTED_COUNT` / `expected.*=.*\d+` for stale N
- [ ] Searched docs for "N daemons" / "N×3 = M instances" prose
- [ ] All hits updated in same commit

### Phase 4 closes by running /debug race

After deploy, run:

```bash
python3 ~/.claude/skills/debug/bin/debug.py race <feature> --dry-run
```

Verdict must be `race_free`. `race_present (...)` blocks Phase 4 close. Findings paste into the §4.5 block.

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
