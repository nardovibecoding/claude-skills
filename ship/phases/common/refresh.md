# /ship --mode=refresh — Staleness Sweep

Variant-agnostic. Shared between bot and app. Invoked only under `ship --mode=refresh`.

## Purpose

Sweep all `.ship/*/reports/05-monitor.md` (and legacy `.ship/*/05-monitor.md`) lesson entries against current codebase reality. Surface stale lessons before they mislead Phase 0 recall.

## OUTPUT CONTRACT

- WRITE sweep report to `.ship/_refresh_<YYYY-MM-DD>.md` via Write tool.
- RETURN only: (a) report file path, (b) ≤10-line summary (count per outcome class).
- Phase not closed until `test -s .ship/_refresh_<YYYY-MM-DD>.md` passes.

## Steps

1. **Discover all lesson files**

```bash
# New layout
find ~/.ship/*/reports/ -name "05-monitor.md" 2>/dev/null

# Legacy layout
find ~/.ship/ -maxdepth 2 -name "05-monitor.md" 2>/dev/null
```

2. **For each lesson block** (each `---`-delimited YAML block in each file):

   **Check A — fix_commit still in git log** (bug-track entries only):
   ```bash
   git log --oneline | grep <fix_commit>
   # empty = commit gone (deleted branch, force-push, squash)
   ```

   **Check B — affected files still exist**:
   ```bash
   ls <path referenced in lesson body>
   ```

   **Check C — root_cause condition still possible**:
   ```bash
   grep -r "<root_cause_pattern>" <relevant source dirs> | head -3
   # empty = code pattern no longer exists (may be fixed or refactored away)
   ```

3. **Classify each lesson**:

   | Outcome | Condition |
   |---|---|
   | KEEP | All checks pass. Lesson still valid. |
   | UPDATE | 1-2 checks fail partially. Supersede-not-delete: strikethrough old content, append updated content below. |
   | CONSOLIDATE | Duplicate of another lesson (same root_cause, same feature_slug variant). Merge into the newer entry. |
   | REPLACE | All checks fail or lesson is fully superseded by newer lesson. Replace body entirely. |
   | DELETE | Lesson is incorrect or harmful. Human-gated — never auto-deleted. |

4. **Apply changes** (if `--apply` flag):
   - UPDATE, CONSOLIDATE, REPLACE: execute automatically
   - DELETE: log in report as "pending human confirmation" — do NOT touch the file

5. **Write sweep report** to `.ship/_refresh_<YYYY-MM-DD>.md`:

```markdown
# /ship refresh sweep — <YYYY-MM-DD>

## Summary
- Files scanned: N
- Lesson blocks found: N
- KEEP: N | UPDATE: N | CONSOLIDATE: N | REPLACE: N | DELETE (pending): N

## Entries

### <feature-slug> — <lesson created date>
- Outcome: KEEP | UPDATE | ...
- Reason: <one sentence>
- Action taken: <what was done, or "none" for KEEP>
```

## Owning Agent

**strict-plan** — use for discovery + classification. **strict-execute** — use for applying UPDATE/CONSOLIDATE/REPLACE changes.

## SPREAD/SHRINK pass (required before closing)

**SPREAD (L1-L5):**
- L1 Lifecycle — lessons created + updated + deleted covered?
- L2 Symmetry — supersede-not-delete applied (not silent overwrite)?
- L3 Time-lens — sweep should run periodically (monthly recommended)
- L4 Scale — works when `.ship/` has 100+ entries?
- L5 Resources — grep-only, no LLM calls, zero quota cost

**SHRINK (Sh1-Sh5):**
- Sh1 Duplication — does this duplicate existing lesson cleanup in /s or /combo? (it should not — refresh is /ship-scoped)
- Sh2 Abstraction — no abstraction; 5 outcome classes are concrete
- Sh3 Retirement — orphaned lessons deleted only with human gate
- Sh4 Merge — refresh output folds into `.ship/` tree, no new skill
- Sh5 Simplification — 3-check + 5-outcome is the minimal model
