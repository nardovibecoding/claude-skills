---
name: indicator
description: |
  Switch voice indicator mode. /indicator plugged = menubar (dual monitor).
  /indicator unplugged = floating dot (single monitor).
  Triggers: "plugged", "unplugged", "switch indicator", "menubar indicator", "floating dot".
---

# Voice Indicator Switch

## /indicator plugged (dual monitor)
Kill floating dot, start menubar indicator.
```bash
pkill -f recording_indicator.py 2>/dev/null
nohup python3 /tmp/claude-voice-control/recording_indicator.py --mode menubar > /dev/null 2>&1 &
```

## /indicator unplugged (single monitor)
Kill menubar indicator, start floating dot.
```bash
pkill -f recording_indicator.py 2>/dev/null
nohup python3 /tmp/claude-voice-control/recording_indicator.py --mode dot > /dev/null 2>&1 &
```
