---
name: uninstall-skill
description: Safe skill removal workflow with V1-V5 verification before delete. Rename to .disabled first, cooldown confirmation, then delete. Triggers: "uninstall skill X", "remove skill X", "delete skill X".
user-invocable: true
triggers:
  - uninstall skill
  - remove skill
  - delete skill
---

# Uninstall Skill

Safe skill removal: verify, disable, confirm, delete.

## V1-V5 Pre-Delete Checklist

Before any destructive action on skill <name>, verify ALL of:

- **V1** Last accessed: `stat -f %Sa ~/.claude/skills/<name>/SKILL.md` -- was it used in last 30 days?
- **V2** Inbound refs: `grep -rl "<name>" ~/.claude/skills/ 2>/dev/null | grep -v "node_modules|\.git|\.pyc"` -- any skill docs reference it?
- **V3** settings.json refs: `grep "<name>" ~/.claude/settings.json ~/.claude/settings.local.json` -- any hook calls it?
- **V4** skill-router refs: `grep "<name>" ~/.claude/skills/skill-router/SKILL.md` -- any profile lists it?
- **V5** Load-bearing check: is it in the protected list? (loop, s, combo, r1a, recall, ship, legends, lint, extractskill, github-publish, strict-* agents, skill-router, skill-loader MCP) -- if yes, STOP.

## Workflow

### Step 1: Verify V1-V5 (above)

If any check has a real inbound ref (not node_modules/.git/binary noise), flag it and ask user before proceeding.

### Step 2: Disable (rename, don't delete)

```bash
# Rename SKILL.md -> SKILL.md.disabled
mv ~/.claude/skills/<name>/SKILL.md ~/.claude/skills/<name>/SKILL.md.disabled
echo "Disabled: <name>"
```

### Step 3: Confirm cooldown

Tell user: "Skill <name> disabled. Verify nothing breaks for 24h, then confirm delete."
Do NOT proceed to Step 4 without explicit confirmation.

### Step 4: Delete (only after explicit user confirmation)

```bash
rm -rf ~/.claude/skills/<name>
echo "Deleted: <name>"
```

Also delete from skills-master if present:
```bash
rm -rf ~/.claude/skills-master/<name>
```

### Step 5: Clean up orphan refs

After deletion, check and remove references:
- skill-router SKILL.md profile entries
- Any other skill docs that reference <name> by skill-name (not just word match)

## Guard Rules

- NEVER skip V1-V5. Even if user says "just delete it."
- NEVER delete load-bearing skills (V5 list above).
- Disable first, delete second -- always.
- Log every deletion: "Deleted <name> | was last accessed <date> | refs: none"
