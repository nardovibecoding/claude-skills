---
name: memo
description: |
  Read + write local memo store (TG admin_bot + terminal scribble; email channel S5).
  Bare `/memo` shows the 5 newest. `/memo #tag` filters by tag. `/memo <body>` scribbles a new terminal memo (parses #tag tokens). search/--since modes return placeholders until later slices land.
  Triggers: "/memo", "memo this is a note #idea", "/memo brainstorm dashboard #idea", "/memo #drift", "/memo #idea", "/memo #stale-ref", "/memo #followup", "last memo", "check memo", "did my memo save", "show memos", "recheck memo".
user_invocable: true
---

# Memo

Local memo store at `~/telegram-claude-bot/memo/{pending,done}/`. Index at `~/telegram-claude-bot/memo/_index.jsonl` (built by `scripts/index.py`, S1).

## Dispatch

Inspect `$ARG` (the verb argument after `/memo`):

- empty → **list mode** (5 newest, both pending+done)
- starts with `#` → **tag-filter mode** (S2 — this skill)
- starts with `search ` → **search mode** (coming in S3)
- starts with `--since ` → **diff mode** (coming in S7)
- anything else → **scribble mode** (coming in S4)

## Steps

1. **Pull latest** (auto-rebase + autostash configured locally):
   ```bash
   cd ~/telegram-claude-bot && git pull origin main 2>&1 | tail -3
   ```
   If pull fails, surface the error — do NOT silence with `2>/dev/null`.

2. **Dispatch on `$ARG`**:

   ```bash
   ARG="${ARG:-}"  # the text after /memo
   SCRIPTS="$HOME/.claude/skills/memo/scripts"

   case "$ARG" in
     "")
       MODE=list
       ;;
     \#*)
       MODE=tag
       TAG="${ARG#\#}"            # strip leading #
       TAG="$(echo "$TAG" | tr '[:upper:]' '[:lower:]' | awk '{print $1}')"  # lowercase, first token
       ;;
     "search "*)
       echo "(search mode — coming in slice S3)"
       exit 0
       ;;
     "--since "*)
       echo "(--since diff mode — coming in slice S7)"
       exit 0
       ;;
     *)
       echo "(scribble mode — coming in slice S4)"
       exit 0
       ;;
   esac
   ```

3. **List mode** (bare `/memo`) — preserve existing behavior:
   ```bash
   ls -t ~/telegram-claude-bot/memo/pending/*.md ~/telegram-claude-bot/memo/done/*.md 2>/dev/null | head -5
   ```
   For each file, print:
   - timestamp (from filename `YYYY-MM-DD_HHMMSS.md`)
   - status: `PENDING` (in pending/) or `done` (in done/)
   - body (content after frontmatter)

   Output format:
   ```
   | When (HKT)        | Status  | Content |
   |-------------------|---------|---------|
   | 04-20 22:20:50    | done    | https://x.com/_avichawla/... |
   | 04-20 22:20:36    | done    | test |
   | 04-20 22:20:13    | done    | https://x.com/_avichawla/... |
   ```
   File timestamps are UTC; convert to HKT (UTC+8) for display.

   If no files in pending/ or done/ → fall back to git log:
   ```bash
   cd ~/telegram-claude-bot && git log --all --oneline --grep='memo:' -10
   ```

4. **Tag-filter mode** (`/memo #tag`) — note: bash block is left-aligned (column 0) on purpose so the embedded python heredoc preserves indentation:

```bash
python3 - "$TAG" <<'PY'
import sys, os, datetime
sys.path.insert(0, os.path.expanduser("~/.claude/skills/memo/scripts"))
from index import query_index, build_index, INDEX_FILE

tag = sys.argv[1].strip().lower().lstrip("#")
if not INDEX_FILE.exists():
    build_index()  # lazy init from S1

rows = query_index(tags=[tag], limit=5)
if not rows:
    print(f"(no memos with tag #{tag})")
    sys.exit(0)

def hkt(ts: str) -> str:
    # ts shape "YYYY-MM-DD HH:MM:SS" — treat as UTC, +8 to HKT
    try:
        dt = datetime.datetime.strptime(ts[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return ts[:16]
    dt += datetime.timedelta(hours=8)
    return dt.strftime("%m-%d %H:%M:%S")

print("| When (HKT)        | Status  | Tags                 | Content |")
print("|-------------------|---------|----------------------|---------|")
for r in rows:
    when = hkt(r.get("ts", ""))
    status = "PENDING" if r.get("status") == "pending" else "done"
    tags = ",".join(f"#{t}" for t in r.get("tags") or [])
    body = (r.get("body_preview") or "").replace("|", "\\|")[:60]
    print(f"| {when:<17} | {status:<7} | {tags:<20} | {body} |")
PY
```

## Notes

- Memos arrive automatically via `memo_display.py` hook on every UserPromptSubmit — bare `/memo` is for manual recheck, `/memo #tag` is for filtered recall.
- Tags are lowercase. `#Drift`, `#DRIFT`, and `#drift` all match.
- The index is lazy-built on first invocation; rebuild manually with `python3 ~/.claude/skills/memo/scripts/index.py --build` if it ever drifts.
- `done/` never gets cleared automatically. If it grows large (>500 files) consider `mv done/old_* archive/` but not needed at current rate.
- If VPS push is lagging (>5 min) and expected memo is missing, check `ssh hel 'ls -t ~/telegram-claude-bot/memo/pending/*.md | head -3'` for VPS-side unpushed files.
