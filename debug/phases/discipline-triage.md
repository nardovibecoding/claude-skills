# /debug — F-family triage primitive (HARD RULE — added 2026-05-01)

Before routing a symptom to a verb (wiring/bug/drift/flaky/performance/leak/race/wedge/critic), classify the symptom against the F-family taxonomy AND the active discipline list. Symptom-to-family mapping is more precise than symptom-to-verb because verbs handle execution; families handle classification.

Source: `~/.claude/rules/invariant-taxonomy.md` (F1-F16) + `~/.claude/rules/disciplines/_index.md` (D1-D16 + 7 blanks + M1).

---

## Step 0 — F-family classification (BEFORE choosing verb)

For every /debug invocation, first ask: **which F-family does this symptom match?** Use the taxonomy keywords:

| symptom shape | F-family | likely discipline | likely verb |
|---|---|---|---|
| "X happened but Y didn't" | F1.1 state-pair, F1.7 flag-pair | D5 lifecycle-pair | bug |
| "lock acquired but never released" / "RSS climbing" | F1.2 lifecycle, F1.3 resource-pair, F4.2 count-bound | D5 + D8 | leak |
| "two sources disagree" / "cache stale" | F1.4 cache-coherence, F1.6 distributed-pair | D1 SSOT | drift |
| "request sent, no response" | F1.5 communication-pair, F7.3 timeout | D2 idempotency, D9 timeout | bug or wedge |
| "set true never set false" | F1.7 flag-pair | D5 | bug |
| "init order broken" / "phase X required Y first" | F2.1, F2.3 phase-gating | D-blank-1 (no detector yet) | bug |
| "writer emits {a,b,c}, reader expects {a,b,d}" | F3.1 schema-pair | D3a schema-contract | bug |
| "crashed reading old data" | F3.2 versioning | D4 deprecation | drift or bug |
| "TS lies about runtime shape" | F3.3 runtime-vs-static | D10 illegal-states | bug |
| "Σ exceeded budget" / "open-orders > N" | F4.1 sum-bound, F4.2 count-bound | D14 quantitative, D8 | bug |
| "calls/sec exceeds limit" | F4.3 rate-bound | D14 + D8 | performance |
| "counter went backwards" | F4.4 monotonicity | D14 | bug |
| "cash + Σ ≠ total" | F4.5 conservation | D14 | bug ($ HIGH) |
| "rolled back partially" | F5.1 transaction | D2, D14 | bug ($ HIGH) |
| "double-billed / double-fill" | F5.2 idempotency, F8.1 idempotency-key | D2 | bug ($ HIGH) |
| "two flags both true" | F5.3 mutual-exclusion | D10 | bug |
| "RMW under load gives wrong count" | F6.1 RMW atomicity | D1 mutex-bypass | race |
| "check-then-act race" | F6.2 TOCTOU | D-blank-2 (no detector) | race |
| "snapshot read inconsistent" | F6.3 snapshot consistency | D-blank-2 | race |
| "two writers same file" | F6.4 single-owner | D1 SSOT-code | drift |
| "emit never resolves" | F7.1 progress | D5 | bug |
| "deadlock" | F7.2 no-deadlock | D-blank-7 | wedge |
| "untimed await hangs" | F7.3 timeout | D9 | wedge |
| "duplicate via retry across hosts" | F8.1 idempotency-key | D2 | bug |
| "exchange vs portfolio drift" | F8.2 reconciliation | D6 live-truth | drift |
| "cross-host event ordering broken" | F8.3 causal consistency | D-blank-3 | bug |
| "remote dep silent" | F8.4 cross-host liveness | D6 | wedge |
| "swallowed catch" / "unhandled rejection" | F9.1, F9.3 | D11 errors-as-values | bug |
| "raw throw at boundary" | F9.2 error propagation | D11 | bug |
| "over-defensive guards on typed-non-null" | F9.4 defensive-vs-trustful | D11 + D12 | critic |
| "state changed silently, no log" | F10.1 state-change emit | D5 | wiring |
| "no heartbeat" | F10.4 heartbeat | D6, D3b RED/USE | wedge |
| "(x as any).field=" everywhere | F11.1 no-as-any | D10 | critic |
| "two functions mutate same field" | F11.2 single-mutator | D1 SSOT-code | critic |
| "PnL via path A != path B" | F12.1 cross-path equiv | D-blank-4 | bug |
| "encode then decode != identity" | F12.2 round-trip | D-blank-4 | bug |
| "config schema drifted" | F13.1, F13.4 | D-blank-5 (partial via D1) | drift |
| "DRY_RUN gate missing on call site" | F14.2 gate-coverage | D15 permission-gate | critic ($ HIGH) |
| "Math.random in scoring" / "test flake from clock" | F15.2-F15.3 | D-blank-6 | flaky |
| "money as float gives off-by-cent" | F16.1 money-as-int | D16 numeric precision | bug ($ HIGH) |
| "NaN propagated" | F16.2 NaN containment | D11 + D16 | bug |

---

## Step 0.5 — DI consultation

After F-family classification, ALSO check `<project>/.ship/_meta/domain-invariants.md` (per M1 meta-rule). The bug may violate a project-specific DI that's higher precision than the F-family.

Example: PM bot bug "trade-journal says fill but portfolio says no position" violates **DI.4** (Order↔Fill↔Position chain) AND **DI.12** (trade-journal-portfolio reconciliation) — both more specific than F8.2 reconciliation.

Print BOTH the F-family AND the DI in the verdict. Cite both in `realize-debt.md` ledger.

---

## Step 1 — Then route to verb

After Step 0 + Step 0.5, choose the verb per existing routing in `~/.claude/skills/debug/SKILL.md`. The classification is INPUT to the verb, not a replacement.

Verb-routing remains:
- `/debug check <feature>` — Wiring (B: feature → runtime)
- `/debug bug "<symptom>"` — Bug (A: symptom → root cause, 17-step engine)
- `/debug drift <feature>` — Drift
- `/debug flaky <feature>` — Flaky
- `/debug performance <feature>` — Performance
- `/debug leak <feature>` — Leak
- `/debug race <feature>` — Race
- `/debug wedge <unit>` — Wedge
- `/debug critic <target>` — Critic

The F-family + DI annotation makes the verb's investigation tighter — the engine knows what shape it's looking for.

---

## Step 5+ — Receipt logging

When /debug verdict closes a bug, append a receipt per CLAUDE.md §Code-quality disciplines:

```json
{"ts": "2026-05-01T08:30:00Z", "discipline": "D5", "source": "/debug", "slug": "<bug-slug>", "violation_class": "F1.1 state-pair (resolved without exit-trace)", "DI": "DI.3", "severity": "HIGH"}
```

Path: `~/.claude/scripts/state/discipline-receipts.jsonl` (created on first append).

This feeds the ratchet rule for daemon-detector activation.

---

## Cross-references

- Taxonomy: `~/.claude/rules/invariant-taxonomy.md`
- Discipline index: `~/.claude/rules/disciplines/_index.md`
- M1 meta-rule: `~/.claude/rules/disciplines/M1-domain-invariants.md`
- Ship discipline impact (parallel template): `~/.claude/skills/ship/phases/common/discipline-impact.md`
- Daemon activation gate: `~/.ship/bigd-discipline-detector-mapping/goals/01-spec.md`
- Existing /debug routing: `~/.claude/skills/debug/SKILL.md`

Source: 2026-05-01 discipline scaffolding session.
