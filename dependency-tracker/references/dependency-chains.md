## Common Dependency Chains

### Persona rename/repurpose
```
personas/ID.json → config.py BOTS{} → admin_bot/commands.py DIGEST_BOTS
                 → send_xdigest.py X_PERSONAS → auto_healer.py digest flags
                 → admin_bot/callbacks.py display names → memory/project_personas.md
                 → CLAUDE.md persona list → ADMIN_HANDBOOK.md
```

### Thread ID change
```
personas/ID.json thread_id → config.py BOT_THREADS{} → admin_bot message routing
                            → send_xdigest.py target → auto_healer.py checks
```

### New env var
```
.env → .zshrc (source) → systemd EnvironmentFile → personas/*.json (if referenced)
     → config.py (os.getenv) → .claude/settings.json (if MCP needs it)
```

### File rename/move
```
old_path → all imports → start_all.sh → crontab → systemd ExecStart
         → CLAUDE.md references → ADMIN_HANDBOOK.md → memory/*.md
```

### Cron job change
```
crontab entry → auto_healer.py schedule checks → admin_bot/commands.py schedule display
              → ADMIN_HANDBOOK.md docs → memory/project_*.md
```

## Anti-Patterns
