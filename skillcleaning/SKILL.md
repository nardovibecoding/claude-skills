---
name: skillcleaning
description: |
  Audit, trim, and optimize all installed skills. Checks: 15K YAML char budget,
  200-line body limit, unused skills, overlaps, description bloat.
  Triggers: "skill cleaning", "clean skills", "audit skills", "skill health",
  "check skill budget", "are we over 15K".
---

# Skill Cleaning — Automated Audit + Optimize

## Step 1: Measure Budget
```bash
# Total YAML chars (must be under 15,000)
find ~/.claude/skills -name "SKILL.md" -not -path "*/node_modules/*" -not -path "*/.git/*" -exec awk '/^---/{n++; next} n==1{print}' {} \; | wc -c

# Count active skills
find ~/.claude/skills -name "SKILL.md" -not -path "*/node_modules/*" -not -path "*/.git/*" | wc -l

# Top 10 by YAML size
for f in $(find ~/.claude/skills -name "SKILL.md" -not -path "*/node_modules/*" -not -path "*/.git/*"); do
  chars=$(awk '/^---/{n++; next} n==1{print}' "$f" | wc -c)
  echo "$chars $(basename $(dirname $f))"
done | sort -rn | head -10
```

Report: "X/15,000 chars used (Y%). Z active skills."

## Step 2: Check Usage
Read `~/.claude.json` → `skillUsage` section. List skills with 0 uses.

## Step 3: Check Overlaps
For each skill, compare description against all others. Flag pairs with >50% keyword overlap.
Known overlaps to check: investigate vs systematic-debugging, critic vs codex, build vs ship, guard vs careful+freeze.

## Step 4: Check Body Length
Flag any SKILL.md body > 200 lines. These need references/ extraction.

## Step 5: Propose Actions
Present a table:
```
📊 SKILL HEALTH REPORT

Budget: X/15,000 chars (Y%)
Active: Z skills

OVER BUDGET? [YES/NO] — need to free X chars

DISABLE (unused + no foreseeable use):
- skill_name (X chars, 0 uses) — reason

TRIM (description > 500 chars):
- skill_name: X chars → target 400

MERGE (overlapping):
- skill_a + skill_b → combined_skill

REFACTOR (body > 200 lines):
- skill_name: X lines → extract to references/
```

## Step 6: Execute (after approval)
- Disable: `mv SKILL.md SKILL.md.disabled`
- Trim: Edit YAML description to under 500 chars
- Merge: Create new skill, disable originals
- Verify: re-measure budget, confirm under 15K

## Rules
- NEVER delete skill folders — always disable (rename .disabled)
- gstack skills: disable only, don't edit (managed by gstack)
- Anthropic skills (docx/pdf/xlsx/pptx): trim descriptions only, don't disable
- Plugins (hookify/telegram/frontend-design): can't disable from here
- After ANY change: re-measure total YAML chars
