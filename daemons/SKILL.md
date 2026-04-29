---
name: daemons
description: |
  On-demand daemons panel — smart by default (re-render if today's bundle exists), full re-fire only when needed.
  Triggers: "/daemons", "/bigd" (legacy alias), "daemons now", "fire daemons", "where's my daemons report", "daemons panel", "show today's daemons", "force daemons".
  Args: `--force` (full re-fire all 3 hosts), `--status` (dry-run, show pipeline state), `--since N` (diff mode — show what's NEW vs RECURRING vs RESOLVED across last N days; useful after skipping summons).
  Use when the 14:00 HKT auto-fire missed, panel injected into another session, or Bernard wants today's report on demand.
  NOT FOR: editing daemon code (use /ship), bot liveness check (use /debug check), inbox triage (use the panel's action codes).
  Produces: rendered bundle digest with 3-table per-host view (Mac/Hel/London).
---

# /daemons — manual daily-push fire (smart)

## Decision tree (no flags)

```
TODAY's bundle in consumed/ ────yes──→ re-render existing (1 sec, 0 daemon CPU)
            │
            no
            ↓
TODAY's bundle in ready/ ──────yes──→ consume + render (5 sec)
            │
            no
            ↓
pending/<DATE>/ has 18 valid ──yes──→ assemble + consume + render (10 sec)
            │
            no  (= count < 18, some host(s) missing)
            ↓
fire only the MISSING host(s) ───→ wait → pull → assemble → render (30s-3min)
            │
            no host has anything → full fire (~3 min)
```

`/bigd --force` always fires all 3. `/bigd --status` only reports state, no work.

## Steps (single bash run)

```bash
ARG="${1:-}"
DATE=$(TZ=Asia/Hong_Kong date +%Y-%m-%d)
PEND=~/inbox/_summaries/pending/$DATE
READY=~/inbox/_summaries/ready/${DATE}_bundle.json
CONSUMED=~/inbox/_summaries/consumed/${DATE}_bundle.json

render_panel() {
  python3 -c "
import sys, json
sys.path.insert(0, '/Users/bernard/.claude/hooks')
import inbox_hook
b = json.load(open('$1'))
print(inbox_hook._format_bundle_digest(b))
"
}

count_pending() { ls "$PEND" 2>/dev/null | grep -c '\.json$' || true; }
hosts_present() {
  ls "$PEND" 2>/dev/null | sed -E 's/.*_([a-z]+)\.json/\1/' | sort -u | tr '\n' ' '
}

echo "=== /bigd | DATE=$DATE | mode=${ARG:-smart} ==="

# --status: report only, no work
if [ "$ARG" = "--status" ]; then
  echo "consumed bundle: $([ -s "$CONSUMED" ] && echo "EXISTS ($(wc -c < "$CONSUMED") bytes)" || echo "missing")"
  echo "ready bundle:    $([ -s "$READY" ] && echo "EXISTS"    || echo "missing")"
  echo "pending count:   $(count_pending)/18  hosts: $(hosts_present)"
  exit 0
fi

# --since N: diff mode. Show NEW / RECURRING / RESOLVED across last N days.
# Use when you skipped /bigd for a few days and want "what changed".
if [ "$ARG" = "--since" ]; then
  DAYS="${2:-7}"
  python3 ~/.claude/skills/bigd/scripts/since_diff.py "$DAYS"
  exit 0
fi

# Smart fast paths (skip when --force)
if [ "$ARG" != "--force" ]; then
  if [ -s "$CONSUMED" ]; then
    echo "[fast] consumed bundle exists — re-rendering"
    render_panel "$CONSUMED"
    exit 0
  fi
  if [ -s "$READY" ]; then
    echo "[fast] ready bundle exists — consuming + rendering"
    BID=$(python3 -c "import json; print(json.load(open('$READY'))['bundle_id'])")
    cd ~/NardoWorld/scripts/bigd && python3 _lib/collector.py --consume "$BID" >/dev/null 2>&1
    render_panel "$CONSUMED"
    exit 0
  fi
fi

# 1. Fire missing hosts (or all 3 with --force)
present="$(hosts_present)"
echo "[1/5] firing daemons (current pending: $(count_pending)/18, hosts: ${present:-none})"

fire_mac=true
fire_hel=true
fire_london=true
if [ "$ARG" != "--force" ]; then
  echo "$present" | grep -qw mac    && fire_mac=false
  echo "$present" | grep -qw hel    && fire_hel=false
  echo "$present" | grep -qw london && fire_london=false
fi

if $fire_hel; then
  ssh -o ConnectTimeout=5 hel "systemctl --user start bigd-parallel.service" 2>&1 &
  echo "  fired hel"
fi
if $fire_london; then
  ssh -o ConnectTimeout=5 pm@london "systemctl --user start bigd-parallel.service" 2>&1 &
  echo "  fired london"
fi
if $fire_mac; then
  ( find ~/NardoWorld/scripts/bigd -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null
    cd ~/NardoWorld/scripts/bigd && bash run_parallel.sh > /dev/null 2>&1 ) &
  echo "  fired mac"
fi
wait
$fire_mac && echo "  mac done: $(ls "$PEND"/*_mac.json 2>/dev/null | wc -l) files"

# 2. Wait for VPS (only if we fired any VPS)
if $fire_hel || $fire_london; then
  echo "[2/5] waiting on VPS daemons (timeout 120s)..."
  DEADLINE=$(($(date +%s) + 120))
  while [ $(date +%s) -lt $DEADLINE ]; do
    H=$(ssh -o ConnectTimeout=3 hel        "ls ~/inbox/_summaries/pending/$DATE/ 2>/dev/null | wc -l" 2>/dev/null || echo 0)
    L=$(ssh -o ConnectTimeout=3 pm@london  "ls ~/inbox/_summaries/pending/$DATE/ 2>/dev/null | wc -l" 2>/dev/null || echo 0)
    [ "$H" -ge 6 ] && [ "$L" -ge 6 ] && { echo "  hel=$H london=$L OK"; break; }
    sleep 3
  done
fi

# 3. Pull VPS pendings to Mac
echo "[3/5] pulling VPS → Mac..."
launchctl start com.bernard.bigd-vps-pull 2>/dev/null
sleep 6
echo "  pending now: $(count_pending) files"

# 4. Force-assemble bundle (delete stale)
echo "[4/5] assembling bundle..."
rm -f "$READY" "$CONSUMED"
python3 ~/NardoWorld/scripts/bigd/_lib/collector.py --watch --once --min 18 2>&1 \
  | grep -E "valid|bundle written|dedup" | head -3

BID=$(python3 -c "import json; print(json.load(open('$READY'))['bundle_id'])" 2>/dev/null)
[ -z "$BID" ] && {
  echo "  ERROR: no bundle assembled. Check ~/.cache/bigd/ + ~/inbox/_logs/summary-collector.err"
  exit 1
}
cd ~/NardoWorld/scripts/bigd && python3 _lib/collector.py --consume "$BID" 2>&1 | tail -1

# 5. Render
echo ""
echo "[5/5] === PANEL ==="
render_panel "$CONSUMED"

# Mark force-window fired_today if inside the 15:00 hour, so the auto-fire
# doesn't double-render.
HOUR=$(TZ=Asia/Hong_Kong date +%H)
if [ "$HOUR" = "15" ]; then
  echo '{"force_window_last_fire_date": "'$DATE'"}' > /tmp/claude_inbox_force_window_global.json
fi
```

## When to use which flag

| flag | use when |
|---|---|
| (none) | default — fast re-render if today's bundle exists; otherwise minimal work to fill gaps |
| `--force` | suspect data is stale (detector code changed, manually deleted briefs) — full re-fire |
| `--status` | quick check "did today's bundle assemble?" without doing anything |

## Failure modes + recovery

| symptom | cause | recovery |
|---|---|---|
| `ERROR: no bundle assembled` | collector.py crashed or pending empty after fire | `tail ~/inbox/_logs/summary-collector.err` |
| timed out waiting on VPS | Hel or London SSH down | `ssh hel uptime` / `ssh pm@london uptime`; rerun /bigd after fixing |
| bundle has only Mac (12 missing) | VPS daemons errored | `ssh hel "tail ~/.cache/bigd/bigd_parallel.log"` |
| panel renders with 0 actions | working as intended (clean day) — not a failure | n/a |
