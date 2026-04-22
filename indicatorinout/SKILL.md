---
name: indicatorinout
description: Voice indicator mode toggle.
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
