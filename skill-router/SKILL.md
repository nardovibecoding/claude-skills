---
name: skill-router
description: Switch skill profile mid-session. Toggles .disabled/.md rename. `all` profile re-enables every .disabled in the live dir.
---

# Skill Router — Profile Switching

Swap active skills mid-session without restarting.

## Profiles

| Profile | Skills loaded | When |
|---------|-------------|------|
| `all` | Every skill in live dir (re-enables all .disabled) | Default, general work |
| `coding` | ship, critic, dependency-tracker, + core (chatid, remind, system-check, eli5, skill-router) | Dev/debugging |
| `outreach` | content-humanizer, eli5 + core | BD/content work |
| `minimal` | chatid, remind, system-check, homeinout, indicatorinout, skill-router, eli5 | Quick tasks |

**Note:** `debate`, `systematic-debugging`, `plan-eng-review`, `retro` were removed from profiles (skill dirs do not exist). Protected: skill-router + skill-loader MCP always stay enabled.

## How to Switch

```bash
# The router script handles symlink swapping
~/.claude/switch-profile.sh <profile>
```

After switching, tell the user: "Switched to {profile} mode. {N} skills active."
The new skills take effect on the NEXT prompt.

## Auto-Detect (optional)
If user's message contains keywords, suggest switching:
- "debug", "fix", "error", "broken" → suggest coding
- "outreach", "BD", "message", "DM" → suggest outreach
- Don't auto-switch without asking — just suggest
