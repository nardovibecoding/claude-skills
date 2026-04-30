---
name: github
description: |
  Unified GitHub skill — audit repos, publish new repos, rename / retrofit / purge / archive / change visibility / force-update existing repos.
  Triggers (audit) — "audit my repos", "/github audit", "monthly maintenance", "github audit --fix", "scan stale refs".
  Triggers (publish) — "publish X to github", "make X public", "ship this to github", "upload to github".
  Triggers (other modes) — "rename repo X to Y", "rebrand X", "retrofit X", "add install.sh to X", "purge history of X", "delete repo X", "archive X", "make X private", "update X on github", "push staging to X".
  NOT FOR — internal codebase changes (use Edit/Write directly), authoring code (use ship), security review (use security-review).
  Produces — audit report grouped by severity / new public repo URL with README + LICENSE + install.sh + topics / renamed repo with redirects + clean self-refs / archived or deleted repo.
user-invocable: true
---

<github>

Unified GitHub workflow. Verb dispatch to either audit (5 phases) or publish modes (NEW / RENAME / RETROFIT / PURGE-HISTORY / UNINSTALL / ARCHIVE / VISIBILITY-CHANGE / FORCE-UPDATE).

## Verb dispatcher

| Verb / form | Mode | Reference file(s) to load |
|---|---|---|
| `/github audit` | audit (full, confirm-then-fix) | `references/audit-phases.md` |
| `/github audit --fix` | audit + auto-fix safe issues | `references/audit-phases.md` |
| `/github audit --report` | audit dry run, no changes | `references/audit-phases.md` |
| `/github audit --phase N` | audit single phase | `references/audit-phases.md` |
| `/github publish` (or no verb when "publish/upload/ship to github" intent) | NEW publish (13-step pipeline) | `references/voice-and-hook.md` (FIRST), `references/readme-playbook.md`, `references/publish-workflow.md` (mandatory), `references/description-formulas.md`, `references/topics-by-category.md`, `references/project-types.md`, `references/vhs-templates.md` (optional GIF) |
| `/github rename <old> <new>` | RENAME | `references/publish-modes.md` §RENAME, `references/publish-workflow.md` (rename safety overlap) |
| `/github retrofit <repo>` | RETROFIT | `references/publish-modes.md` §RETROFIT, `references/publish-workflow.md` Phases 2-4 |
| `/github purge <repo> <file-or-secret>` | PURGE-HISTORY (DESTRUCTIVE) | `references/publish-modes.md` §PURGE-HISTORY |
| `/github uninstall <repo>` | UNINSTALL | `references/publish-modes.md` §UNINSTALL |
| `/github archive <repo>` | ARCHIVE | `references/publish-modes.md` §ARCHIVE |
| `/github visibility <repo> public\|private` | VISIBILITY-CHANGE | `references/publish-modes.md` §VISIBILITY-CHANGE |
| `/github update <repo>` | FORCE-UPDATE | `references/publish-modes.md` §FORCE-UPDATE |

## Disambiguation

If user intent is ambiguous between two verbs (e.g. "fix nardo-bus" — could be retrofit or update or audit-fix), ASK ONCE before acting:
"audit / publish / rename / retrofit / purge / uninstall / archive / visibility / update?"

If user types a NEW publish trigger ("publish X", "make X public") without the explicit verb, default to `/github publish` (NEW mode) — the 13-step pipeline in `publish-workflow.md`.

If user types an audit trigger ("audit my repos", "monthly maintenance"), default to `/github audit` (full, confirm-then-fix).

## Naming canon (locked 2026-04-27)

For nardovibecoding, brand prefix is `simply-*` (replaces older `claudecode-*` prefix). Mechanical rule:
```
s|^(claudecode-|claude-)|simply-|
```
Preserve the rest of the name. New publishable repos default to `simply-<descriptor>`. Existing `claudecode-*` repos retrofit via `gh repo rename` (URL redirects preserved by GitHub).

## Cross-cutting safety rules

These apply to all publish modes (audit-only modes don't push):
- **Fresh-init for NEW publishes** — never `gh repo create --source=.` from a working directory with unaudited git history. Copy to `/tmp/publish-<repo>/`, fresh `git init`, single commit.
- **Privacy scan as the LAST gate before push** — `publish-workflow.md` §1.1. Paths, emails, IPs, wallet patterns, author identifiers. Zero hits in working tree AND in `git log --all -p` (for non-fresh-init pushes).
- **Smoke installer in sandbox** — `mktemp -d` + run `install.sh` + assert README's "After" claim before push. Smoke failure REFUSES the push.
- **Ship-audit before push (NEW + RETROFIT)** — spawn `ship-auditor` agent on staging dir. Verdict gates push: PASS continues, NEEDS_FIX asks, REWORK refuses.
- **Template flag matches shape** — `--template=true` only for fork-shape repos (skill packs, hook packs, scaffolds). Tool-shape (binaries, daemons, libraries) stays OFF. Override with `--force-template=<true|false>`.
- **Never force-push to main** without explicit `--force-allowed` flag from user.
- **Never combine destructive operations** in same session (RENAME + PURGE + RETROFIT all separate sessions).

## Skip this skill when

- One-line typo fix to existing repo (just edit + commit).
- Internal private repo with no README audience.
- Pushing to existing branch (not creating new repo).
- Renaming a private repo with no README audience (just `gh repo rename` and stop).
- Repo audit on a single repo (just `gh repo view <repo>` ad-hoc).

## History

Merged 2026-04-30 (skill-consolidation step 17): combined `github-audit` + `github-publish` into `/github` with verb dispatch. Audit body moved to `references/audit-phases.md`; non-NEW publish modes moved to `references/publish-modes.md`; existing publish references kept in place. Old slash commands `/github-audit` and `/github publish` (as standalone slashes) retired — use `/github audit` / `/github publish` going forward. Triggers like "audit my repos" / "publish X" still route here via natural-language dispatch.

</github>
