---
name: indicator-unplugged
description: Switch to floating dot voice indicator (single monitor mode). Kill menubar indicator, start floating dot.
---

Switch voice indicator to **floating dot mode** (single monitor — menubar too crowded).

Steps:
1. Kill menubar indicator: `pkill -f recording_indicator.py`
2. Start floating indicator if not running: `pgrep -f recording_float.py || nohup python3 /Users/bernard/recording_float.py > /dev/null 2>&1 &`
3. Confirm: "Floating indicator active 🟢"
