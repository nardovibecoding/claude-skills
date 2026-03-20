---
name: event-register
description: |
  Auto-register for crypto/Web3 events on Lu.ma. Scrapes event lists from
  sources like cryptonomads.org, then fills and submits registration forms.

  USE FOR:
  - "register for ethcc events"
  - "sign up for HK Web3 events"
  - "auto-fill luma events"
  - "event register"
  - When user wants to batch-register for conference side events

allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - WebSearch
  - WebFetch
  - Agent
---

# Event Auto-Register Skill

Batch-register for crypto/Web3 conference events on Lu.ma using Patchright browser automation.

## Prerequisites

- `patchright` installed (`pip3 install patchright`)
- Lu.ma login cookies saved at `/Users/bernard/telegram-claude-bot/.luma_state.json`
- Profile data at `/Users/bernard/telegram-claude-bot/luma_profile.json`
- Script at `/Users/bernard/telegram-claude-bot/luma_fill_test.py`

## Workflow

### Step 1 — Gather event URLs

Collect Lu.ma event URLs from one of these sources:

**Option A: User provides URLs directly**
Add them to the `events` list in `luma_fill_test.py`.

**Option B: Scrape from cryptonomads.org**
1. Open browser on the conference side-events page (e.g. `https://cryptonomads.org/ETHCC%5B9%5DSideEvents2026`)
2. Scroll to load all events
3. Click into each event card to find the Lu.ma registration URL
4. Collect all `lu.ma/*` or `luma.com/*` URLs

**Option C: Scrape from Lu.ma calendar**
Search `site:lu.ma <conference name> <year>` to find the calendar page, then extract event links.

**Option D: Search the web**
Use WebSearch to find `lu.ma <event name> registration` for specific events.

### Step 2 — Update events list

Edit `luma_fill_test.py` and update the `events` list:

```python
events = [
    ("Event Name", "https://lu.ma/event_slug"),
    ...
]
```

### Step 3 — Check login state

If `.luma_state.json` is stale or missing, re-login:

```bash
python3 -c "
import asyncio, json
from patchright.async_api import async_playwright

async def login():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        ctx = await browser.new_context()
        page = await ctx.new_page()
        await page.goto('https://lu.ma/signin')
        for i in range(90):
            await page.wait_for_timeout(2000)
            cookies = await ctx.cookies()
            if any('token' in c['name'].lower() or 'session' in c['name'].lower() for c in cookies):
                state = await ctx.storage_state()
                with open('.luma_state.json', 'w') as f:
                    json.dump(state, f)
                print(f'Saved {len(cookies)} cookies')
                await browser.close()
                return
        print('Timeout')
asyncio.run(login())
"
```

Tell user to login in the browser. Script auto-saves cookies when login detected.

### Step 4 — Run automation

```bash
cd /Users/bernard/telegram-claude-bot && python3 luma_fill_test.py
```

Run in background for batch processing. Monitor output for results.

### Step 5 — Review results

Check output for:
- `✅ Registration confirmed!` — success
- `⏳ Submitted (awaiting confirmation)` — submitted, pending host approval
- `⚠️ UNFILLED` — some fields not filled, may need manual review
- `⚠️ No submit button found` — page structure different, check manually
- `⏭ Page unavailable` — 404 or cancelled event
- `❌ CRASHED` — error, check logs

Screenshots saved to `/tmp/luma_event_*.png` for manual verification.

## Profile Configuration

Edit `luma_profile.json`:

```json
{
  "full_name": "Stevie Ong",
  "email": "stevie.ong@mexc.com",
  "mobile": "+85252735493",
  "company": "MEXC",
  "job_title": "Partnerships",
  "twitter": "Nardodipepe",
  "telegram": "StevieOng_MEXC",
  "linkedin": "https://linkedin.com/in/bernardngb"
}
```

## Text Field Mapping

The script uses keyword matching to fill fields. Key mappings:
- company/org/team/protocol/firm → `profile.company`
- job/title/position → `profile.job_title`
- twitter/x handle → `profile.twitter`
- telegram → `profile.telegram`
- project/build/hackathon → "Vibe coding AI-powered tools, dApps, and automation workflows"
- hear/know/discover → "Luma"

## Dropdown Logic

Uses `smart_pick_option()` with priority rules:
- Country → China/Hong Kong
- Role → Exchange > Investor > Partner > Builder
- Building on X → Yes
- Join/attend/interest → Yes (first positive option)
- How did you hear → Luma/Social/Twitter

## Known Issues

- Some events use non-standard form layouts — fields may not auto-fill
- "Request to Join" events need host approval after submission
- Non-breaking spaces (`\xa0`) in labels are handled by replacement
