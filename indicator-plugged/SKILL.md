---
name: indicator-plugged
description: Switch to menubar voice indicator (dual monitor mode). Kill floating dot, start menubar indicator.
---

Switch voice indicator to **menubar mode** (dual monitor — has room in menubar).

Steps:
1. Kill floating indicator: `pkill -f recording_float.py`
2. Start menubar indicator if not running: `pgrep -f recording_indicator.py || nohup python3 /tmp/claude-voice-control/recording_indicator.py > /dev/null 2>&1 &`
3. Confirm: "Menubar indicator active 🟢"
