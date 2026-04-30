# /github publish — non-NEW modes

NEW publish (first-time push) is the 13-step pipeline in `publish-workflow.md` + `voice-and-hook.md` + `readme-playbook.md`. This file covers the other 7 modes.

Mode dispatch: see SKILL.md mode table. If user intent is ambiguous, ASK once before acting.

---

## RENAME mode

When user wants to rename an existing public repo (e.g. `claudecode-X → simply-X`). The rename itself is one `gh` command but the cleanup is what matters. Stale self-references in the renamed repo's own README/install.sh are the failure mode.

### 5-step sequence (per repo)

1. **`gh repo rename <user>/<old-name> <new-name>`** — GitHub auto-301 redirects old URLs forever. Stars/watchers/forks follow. Existing clones keep working via redirect.
2. **`git clone https://github.com/<user>/<new-name>`** — fresh local copy with the new name. Don't reuse the old clone (its remote is stale until you `git remote set-url`).
3. **Sed-rewrite self-references** in the cloned repo — README install URL, README badges, install.sh comments, plist labels, any string containing the old repo name. Use `grep -rn '<old-name>' .` to enumerate first; manually verify each hit before sed-rewrite (some hits may be intentional — e.g. a "renamed from X" credit line).
4. **Cross-link audit** — for each SIBLING repo in the same author's portfolio, grep its README for the old name. If hit, queue that sibling for a "fix stale cross-link" PR. Authors with paired repos commonly cross-link in READMEs.
5. **Commit + push** the cleaned repo. Verify the live README on the new URL renders without stale-name hits.

### Safety rules

- NEVER rename when a NEW repo with the OLD name might be created later — redirect breaks the moment you re-create it. Reserve names you'll never reuse.
- NEVER rename a repo with open PRs/issues containing old-name URLs in titles/bodies without first auditing those.
- Cross-link audit is mandatory — skipping leaves stale prose in sibling repos. `gh repo list <user> --json name --jq '.[].name'` then grep each repo's README.
- Don't rename and retrofit in the same session unless the retrofit is trivial.

### Batch renames (e.g. brand pivot across 7 repos)

1. Do all `gh repo rename` first (fast, atomic-ish per call).
2. Clone all renamed repos to a workspace dir.
3. Sed-rewrite each one's self-refs (per-repo, not bulk — different repos have different old names).
4. Cross-link audit ONCE across the whole portfolio.
5. Commit + push each repo. Verify live URLs.

Budget: ~5 min per repo + ~10 min cross-link audit + verify. 7 repos = ~45 min batch.

---

## RETROFIT mode

Add `install.sh` / 1-liner / template flag to a published repo. Subset of NEW: skip classify+hook+structure (already exists); run installer/smoke/audit/push.

Steps (per `publish-workflow.md` Phases 2-4):
1. Pull repo locally if not already cloned.
2. Add/update `install.sh` (idempotent, template at `publish-workflow.md` §2).
3. Smoke test installer in `mktemp -d` sandbox.
4. Spawn ship-auditor agent.
5. Privacy scan on diff (faster than full repo).
6. Commit + push. If template-flag flip requested: `gh repo edit --template=true|false`.

---

## PURGE-HISTORY mode (DESTRUCTIVE)

When secret/credential/sensitive file accidentally committed to a public repo's history. The file MUST be stripped from every past commit, not just the latest.

### Tool: `git filter-repo` (NOT `git filter-branch` — deprecated)

Install: `brew install git-filter-repo` / `pip install git-filter-repo`.

### 5-step sequence

1. **Backup tag first** — `git tag pre-purge-$(date +%Y%m%d-%H%M%S)` and push: `git push --tags`. Reversible: worst case, delete the rewritten history and reset to the tag.
2. **Identify the targets** — exact filenames OR exact strings. `git log --all --full-history -- <path>` to confirm files. For string-replace use `git log -p -S '<secret>'` to confirm presence.
3. **Run filter-repo** —
   - File removal: `git filter-repo --path <secret-file> --invert-paths`
   - String redact: `git filter-repo --replace-text <(echo '<exact-secret>==><REDACTED>')`
4. **Force-push every branch + tag** — `git push --force --all && git push --force --tags`. WARNING: every collaborator's clone is now broken; they must reclone.
5. **Rotate the leaked credential immediately** — assume the secret is already harvested by a public-Git-history scraper. Treat redaction as containment, not as a substitute for rotation.

### Safety rules

- Public repos with stars/forks: force-push REWRITES history but cached forks still hold the secret. Open issues with each forker asking them to delete + re-fork. Or accept the leak is permanent (most realistic).
- Backup tag is non-negotiable.
- Single-commit repos (fresh-init publishes): purge unnecessary. Just delete the file in a new commit.
- Don't combine PURGE with RENAME or RETROFIT in the same session.

---

## UNINSTALL mode

When deleting a public repo. Default to ARCHIVE first; UNINSTALL is the last resort.

### 4-step sequence

1. **Capture metrics** — `gh repo view <user>/<repo> --json stargazerCount,forkCount,isFork,parent`. Note numbers; deletion drops them.
2. **Suggest ARCHIVE first** — if the repo has any stars/forks, propose archive instead.
3. **Confirm twice** — first prompt "are you sure (y/n)", then "this will delete <N> stars and <M> forks (y/n)". Both yes required.
4. **Delete** — `gh repo delete <user>/<repo> --yes`. Name becomes available for someone else within ~30 days; flag this.

### Safety rules

- Forks are NOT deleted — anyone who forked keeps their copy.
- Auto-redirect dies — unlike RENAME, deletion does NOT preserve URL redirects. All external links 404 immediately.
- Star/fork count is gone — even if you re-create, social proof resets to zero.

---

## ARCHIVE mode

Soft EOL — preserves history, stars, forks, but marks read-only on GitHub. Reversible.

```bash
gh api -X PATCH /repos/<user>/<repo> -f archived=true
```

To unarchive: `-f archived=false`.

### When to ARCHIVE (vs UNINSTALL)

- Repo no longer maintained but had value to others (preserves discovery + history)
- Tool superseded by another repo (link to successor in README before archiving)

### When NOT to ARCHIVE

- Active development just paused → leave open
- Created by mistake → UNINSTALL
- Embarrassing first attempt with no users → UNINSTALL

---

## VISIBILITY-CHANGE mode

Flip public ↔ private. One command, but consequences differ by direction.

### Public → Private

```bash
gh repo edit <user>/<repo> --visibility=private --accept-visibility-change-consequences
```

Consequences: stargazers lose view access; forks become orphaned; external links 404; GitHub Pages disabled.

### Private → Public

```bash
gh repo edit <user>/<repo> --visibility=public --accept-visibility-change-consequences
```

Consequences: ALL git history becomes public (run privacy scan FIRST on full git log); GitHub Pages can now be enabled.

### Safety rules

- Private → Public requires Phase 1 privacy scan FIRST on the full git history (`git log --all -p | grep <patterns>`), not just the working tree.
- Public → Private warns user about fork orphaning.

---

## FORCE-UPDATE mode

Push local staging changes → existing public repo. Most common operation post-publish (README polish, install.sh fix, README cross-link update).

### 5-step sequence

1. **Pull first** — `git pull --ff-only` to ensure no remote-only changes get clobbered.
2. **Privacy scan on staged changes** — `git diff HEAD | grep <patterns>` (only the diff, not full repo). Faster than full Phase 1.
3. **Idempotency check** — if updating `install.sh`, run smoke test under sandbox once before push.
4. **Commit + push to default branch** — never `git push --force` to main without an explicit `--force-allowed` flag from user.
5. **Verify** — `gh repo view <user>/<repo>` and check the new commit landed; raw URLs (install.sh, README) fetch the new content.

### Safety rules

- NEVER force-push to main unless user explicitly approves with `--force-allowed`. Fast-forward only.
- Privacy scan on diff is sufficient (fresh-init pattern doesn't apply — repo already exists).
- If installer change, smoke test in sandbox before push. README-only changes can skip smoke.
