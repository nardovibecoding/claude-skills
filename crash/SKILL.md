---
name: crash
description: Alias — /s now folds the cross-session crash sweep into Step 0a. Triggers: /crash, "sessions crashed", "recover unsaved sessions", "save all unsaved convos".
user-invocable: true
---

<crash>
/crash is now folded into /s Step 0a. Invoke /s instead — it fires the cross-session sweep (skip-oracle gated, all dates) as a bg agent AND saves the current session.

If you want sweep-only without saving the current session, run /s and let Step 0's `ALREADY_SAVED` guard stop the main save (Step 0a's bg sweep still runs).

Reading this: invoke /s.
</crash>
