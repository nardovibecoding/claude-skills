---
name: replies
description: On-hand review of sy-replies queue. Shows pending replies grouped by class with frequency. Verbs - promote/discard/skip a row, or stats for class distribution.
---

# /replies — sy-replies queue review panel

Reads `~/NardoWorld/meta/sy-replies-queue.jsonl` (or `$SY_REPLIES_QUEUE_PATH`).
Writes promoted entries to `~/NardoWorld/lessons/sy-replies-promoted.md` (or `$SY_REPLIES_PROMOTED_PATH`).

## Usage

```
/replies                        # Show full pending table (all sections)
/replies QUESTION               # Show only QUESTION section
/replies stats                  # Class distribution + top 10 unlabeled patterns
/replies promote KEY            # Promote row; KEY = <session_id>:<turn_idx>
/replies discard KEY            # Discard row
/replies skip KEY               # Leave pending (no-op)
```

The KEY is shown in the table output under each row as `KEY: <session_id>:<turn_idx>`.

## Steps (invoke verbatim)

```bash
python3 ~/.claude/scripts/sy_replies_review.py [args]
```

Pass the command output directly to Bernard — do not summarize or reformat.

## Section structure

- One section per single-label class (APPROVE_COMPLEX, FEATURE_REQUEST, IMAGE_FEEDBACK, OPTION_SELECT, QUALITY_PUSHBACK, QUESTION)
- MULTI-LABEL section for rows with N>1 labels
- UNLABELED section for `classes: []`
- APPROVE_SIMPLE: summary count only (auto-promoted, not shown for review)

## Dedup rule

Rows with identical `user_reply.lower().strip()` are collapsed into one line with count. Highest-count shown first within each section.

## Promote writeback

`promote KEY` does three things atomically:
1. Appends a formatted block to `sy-replies-promoted.md` (deduped by key)
2. Sets `review_status: "promoted"` + `promoted_at: <epoch>` in queue.jsonl
3. Rewrites queue.jsonl atomically (tmp + rename, fcntl.LOCK_EX)

## Falsifier

Run `/replies`, verify table renders with at least one section.
Run `promote` on a QUESTION row; verify queue row has `review_status: "promoted"` and `sy-replies-promoted.md` has the appended entry.
