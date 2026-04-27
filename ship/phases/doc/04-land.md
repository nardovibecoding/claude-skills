# /ship Phase 4 LAND — DOC route

For shipping documentation only — atoms, lessons, hub articles, README rewrites, CLAUDE.md edits, rules/*.md additions. No process to verify, no /debug check applies.

## OUTPUT CONTRACT

Write artifact to `.ship/<slug>/04-land.md` (≤150 lines). Return summary ≤10 lines.

## Steps

### 1. Universal pre-checks (load `phases/common/realization-checks.md`)

Run RC-1 (stub markers — `TODO` is allowed in DOC route IF it's clearly future-work flagging, not "I forgot to write this"). Run RC-6 (cross-repo cross-link audit) if doc references public repos.

### 2. File-existence check

The committed doc must exist at the declared path. Trivial but `mv` accidents do happen.

```bash
test -f <doc-path> && wc -l <doc-path>
```

ASSERT: file exists, ≥10 lines (raw stubs typically <5 lines).

### 3. Linked-from-index check

Every new atom / lesson / hub article must be reachable from at least one upstream index file. Common indexes:
- `~/NardoWorld/MEMORY.md`
- `~/NardoWorld/atoms/index.md`
- `~/NardoWorld/lessons/index.md`
- `~/.claude/projects/-Users-bernard/memory/MEMORY.md`
- `~/.claude/CLAUDE.md` (for rule additions)
- `~/.claude/rules/<scope>.md` (for rule promotions)

```bash
DOC=<doc-name-without-ext>
INDEXES=(~/NardoWorld/MEMORY.md ~/NardoWorld/atoms/index.md ~/.claude/projects/-Users-bernard/memory/MEMORY.md)
LINKED=0
for idx in "${INDEXES[@]}"; do
    [ -f "$idx" ] && grep -q "$DOC" "$idx" && LINKED=$((LINKED+1))
done
[ "$LINKED" -ge 1 ] || echo "ORPHAN: $DOC not linked from any index"
```

ASSERT: ≥1 index references the new doc. Orphaned docs BLOCK close (orphans rot — graph-recall can't find them).

### 4. Cross-link integrity

Every `[[wikilink]]` and `[label](path)` in the doc must resolve. Broken intra-doc references degrade Phase 4.

```bash
# Naive check for [[wikilinks]]
grep -oE '\[\[[^\]]+\]\]' <doc-path> | sort -u | while read link; do
    target=$(echo "$link" | tr -d '[]')
    find ~/NardoWorld ~/.claude/projects -name "${target}.md" 2>/dev/null | head -1 | grep -q . || \
        echo "BROKEN-WIKILINK: $link"
done
```

WARN on broken wikilinks (graph-recall handles missing targets gracefully). BLOCK only on broken hard-paths.

### 5. Verdict

- Steps 1-3 PASS, step 4 has WARNs only → `wired` (close OK)
- Step 3 fails (orphan) → `not_wired` (BLOCK; either link from index or move to archive)
- Step 4 fails on hard-path → `partial` (close OK with `--ack-broken-link`)

## What this route deliberately SKIPS

- `/debug check` (no live process)
- §4.5 deploy gates (no cron / timer / systemd unit)
- Performance check (no scan loop)
- Dry-run paper flip (no trading code)

## Override path

`.ship/<slug>/state/04-doc-override.md` with reason + Bernard ack. Common case: doc is a placeholder for future work, intentionally orphaned until hub article catches up.

## Owning Agent

`strict-execute` writes; no `strict-review` follow-up needed (docs don't drift like processes do — but periodic `/lint` covers it).

## SPREAD/SHRINK

Standard per `phases/common/refresh.md`.
