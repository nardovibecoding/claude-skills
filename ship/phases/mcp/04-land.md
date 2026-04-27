# /ship Phase 4 LAND — MCP route

For shipping an MCP server (stdio or HTTP). The "server file exists but Claude Code never connects" failure mode is what this route exists to prevent.

## OUTPUT CONTRACT

Write artifact to `.ship/<slug>/04-land.md` (≤200 lines). Return summary ≤15 lines.

## Steps

### 1. Universal pre-checks (load `phases/common/realization-checks.md`)

Run RC-1 (stub markers) + RC-2 (SPEC drift between server's tool listing and README claims) + RC-7 (hook-output blocklist).

### 2. Server starts cleanly

```bash
# stdio: server should start, await JSON-RPC on stdin, not crash
timeout 3 python3 <server-path>  # or `node <server-path>`
# Expected: no immediate crash, no error to stderr beyond startup logs
```

ASSERT: process starts, doesn't crash within 3s. If server requires env vars (API keys, config paths), document them in README + verify presence pre-start.

### 3. ListTools probe

For stdio servers, send a `tools/list` JSON-RPC request and verify response shape:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | \
    timeout 5 python3 <server-path> | \
    python3 -c "
import json, sys
for line in sys.stdin:
    try:
        r = json.loads(line)
        if 'result' in r and 'tools' in r['result']:
            print(f'OK: {len(r[\"result\"][\"tools\"])} tools listed')
            for t in r['result']['tools'][:3]:
                print(f'  - {t[\"name\"]}: {t.get(\"description\",\"\")[:60]}')
            break
    except: pass
"
```

ASSERT:
- Response is valid JSON-RPC
- `result.tools` is a non-empty array (unless server is intentionally tool-less)
- Each tool has `name` + `description` + `inputSchema`

### 4. Test-tool call

Pick the simplest tool from the server (often `ping`, `echo`, or `health`). Send a `tools/call` request, assert success:

```bash
echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"<simplest-tool>","arguments":{}}}' | \
    timeout 5 python3 <server-path>
```

ASSERT: response includes `result.content` (success) — NOT `error`.

### 5. settings.json wiring (mcpServers)

Verify the server is registered in Claude Code's MCP config:

```bash
python3 -c "
import json
s = json.load(open('$HOME/.claude/settings.json'))
servers = s.get('mcpServers', {})
print(list(servers.keys()))
"
```

ASSERT: server name appears in `mcpServers`. If not registered, the server file existing changes nothing — Claude Code never connects.

### 6. Verdict

- Steps 2-5 PASS → `wired`
- Step 4 fails (server starts + lists tools but call errors) → `partial` (close OK with `--ack-tool-debt`)
- Step 2, 3, or 5 fails → `not_wired` (BLOCK)

## SPEC drift specific to MCP

The README's tool listing must match the server's actual `tools/list` output. Ship-auditor mini-run catches this. BLOCK if README claims a tool that the server doesn't expose.

## Override path

`.ship/<slug>/state/04-mcp-override.md` + Bernard ack.

## Owning Agent

`strict-execute` writes; `strict-review` re-verifies at T+24h (MCP servers can stop responding after long idle).

## SPREAD/SHRINK

Standard per `phases/common/refresh.md`.

## Reference

Inherit ledger-writing protocol from `phases/bot/04-land.md`.
