---
name: apply-evolution
description: |
  Review and apply evolution patches generated from the AI Evolution Digest.

  USE FOR:
  - When user says "apply evolution", "apply patch", "review evolution"
  - After returning to Mac and wanting to apply pending evolution patches
  - To review what patches are waiting
user_invocable: true
---

# Apply Evolution Patches

Review and apply pending evolution patches from the AI Evolution Digest system.

## Steps

1. **List pending patches:**
   ```
   ssh bernard@157.180.28.14 "ls -la /home/bernard/telegram-claude-bot/evolution_patches/*.md 2>/dev/null"
   ```

2. **Pull patches to local:**
   ```
   cd /Users/bernard/telegram-claude-bot && git pull origin main
   ```

3. **For each patch file in `evolution_patches/`:**
   - Read the patch markdown file
   - Show the user: what it changes, which files, risk assessment
   - Ask: "Apply this patch? (y/n)"
   - If yes: apply the diff changes to the actual source files
   - Run syntax check: `python3 -c "import py_compile; py_compile.compile('file.py', doraise=True)"`
   - If syntax OK: commit with message `[evolution] <title>`
   - Push to git
   - Delete the patch file

4. **After all patches processed:**
   - Report summary: applied N, skipped M
   - VPS auto-pulls within 1 min

## Important
- ALWAYS show the full diff to the user before applying
- ALWAYS explain the impact on existing functionality
- NEVER apply without user confirmation
- If a patch looks risky or outdated, recommend skipping it
