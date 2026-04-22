---
name: crash
description: Recover unsaved conversations after Claude Code sessions crashed. Scans today's jsonl session files, diffs against existing convo_YYYY-MM-DD_*.md checkpoints in memory/, saves summaries for any unsaved sessions. Triggers: /crash, "sessions crashed", "recover unsaved sessions", "save all unsaved convos".
user-invocable: true
---

<crash>
Bulk-recover crashed sessions. Spawn ONE background agent, exit fast.

## Step 1: Print status
"Scanning today's jsonls... agent running in bg."

## Step 2: Spawn agent (model=sonnet, run_in_background=true)

Prompt to agent:

"Recover unsaved Claude Code sessions.

DATE = today (YYYY-MM-DD format, use `date +%Y-%m-%d`).
JSONL_DIR = /Users/bernard/.claude/projects/-Users-bernard/
MEM_DIR = /Users/bernard/.claude/projects/-Users-bernard/memory/

### A) Inventory
1. List all `$JSONL_DIR/*.jsonl` modified on DATE (use `ls -lat` + date-field filter, or `find $JSONL_DIR -name '*.jsonl' -newermt DATE -not -newermt DATE+1day`).
2. Skip files <10KB (empty/stub sessions).
3. List existing `$MEM_DIR/convo_DATE_*.md` — extract topic slugs.

### B) Classify each jsonl
For each jsonl >=10KB:
- Use `head -c 8000` and `tail -c 8000` via Bash to sample start + end (jsonl lines can be huge, don't Read full).
- Extract first user message + last user/assistant content. Infer topic slug (1-4 words, kebab-case).
- Match against existing saved slugs — skip if topic already saved (fuzzy match: substring or 80% word overlap).

### C) Save unsaved sessions
For each unsaved jsonl, write `$MEM_DIR/convo_DATE_<slug>.md`:

```
---
date: DATE
topic: <slug>
session_id: <jsonl basename without .jsonl>
status: crashed-recovered
---

# <Topic title>

## What happened
- 3-6 bullets: what user asked, what was built/fixed/decided
- Files touched (if any)
- Final state / outcome

## Crash signature (if detectable)
- Last assistant msg truncated? Tool mid-call? Error in tail?
- Skip section if normal end.
```

Keep each file <80 lines. Skip jsonls that are pure tool-noise with no substantive convo.

### D) Report
Report back in <300 words:
- N jsonls scanned, N already-saved (skipped), N newly saved, N skipped as trivial.
- List new filenames saved.
- Flag any jsonls with visible crash signatures (truncated tool calls, errors in last lines).

No NardoWorld filing, no wikilinks, no lessons — this is fast bulk recovery only. User can run normal /s workflow later if any session needs deeper filing."

## Step 3: Exit
Do not wait. User will be notified when agent completes.
</crash>
