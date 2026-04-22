# Phase 5: MONITOR (app variant — canary visual)

gstack canary pattern. Post-deploy visual monitor.

## Pre-deploy baseline capture

- Screenshots of 3-5 critical pages (home, signup, checkout, dashboard)
- Console error baseline per page
- Load time baseline per page
- Critical API response times

## 10-min default (30 min for major releases) watch loop

- 60s tick: take new screenshots, diff vs baseline
- Console error check per page
- Load time check (alert if 2x slowdown)
- Broken link scan
- User error reports (if Sentry/similar wired in)

## Alert rules

- Changes not absolutes
- New errors that persist >2 checks = alert
- Load time degradation > 2x baseline = alert
- Screenshot diff > threshold = human review (MANDATORY GATE even in auto-mode)

## Rollback command ready

For 30-min post-deploy window.

## Post-window cleanup

- Clean monitor = declare DONE
- Update CHANGELOG with outcome
- Capture lessons (tie to /combo)
- Announce to users if major release

## Artifact

`.ship/<feature>/05-monitor.md`

## Post-launch skills to invoke separately

After `/ship` app completes, these slavingia skills help with GTM:
- **pricing** — set sustainable price
- **first-customers** — get first 100 customers
- **marketing-plan** — distribution strategy
- **find-community** — audience discovery
- **grow-sustainably** — profitable growth
- **processize** — systematize ops

Install as standalone skills when Tokengotchi (or similar) launches to users.

---

## Owning Agent

**strict-review** — use this agent's brief template for the phase artifact.

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
