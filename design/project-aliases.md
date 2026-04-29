# project-aliases — name → surface map

When the user mentions a project by name in the prompt, route to that project's renderer regardless of cwd.

| Project name (case-insensitive substring) | Surface | Renderer |
|---|---|---|
| vibe island, vibeisland, vibe-island | macOS SwiftUI | `renderers/swiftui.md` |
| pm bot, pm-bot, pmbot, kalshi bot, london bot, hel bot | Web React dashboard | `renderers/html.md` |
| pm dashboard, london dashboard, hel dashboard, trader dashboard | Web React dashboard | `renderers/html.md` |
| dagou, dagou dashboard | Web React dashboard | `renderers/html.md` |
| chrome ext, chrome extension, browser ext, popup, side panel, content script | Chrome extension MV3 | `renderers/extension.md` |
| nardoworld, nardo world | Web (static / wiki) | `renderers/html.md` |
| big d, bigd, daemons panel | Web React dashboard | `renderers/html.md` |
| claude harness, harness, status line | Terminal CLI (no renderer) | skip — output is plain text |

## Default vibes per project (when /design called with project name only)

| Project | Default vibe | Default archetype |
|---|---|---|
| VibeIsland | `bloomberg-terminal` (or `apple-clean` if user prefers light) | `dashboard` |
| PM bot dashboard / Hel / London | `bloomberg-terminal` | `dashboard` |
| Dagou dashboard | `cyberpunk` (degen-trader-flavored) | `dashboard` |
| Chrome extension | `apple-clean` | `popup` |
| NardoWorld wiki | `dark-academia` | `landing` |
| Big-D daemons panel | `bloomberg-terminal` | `dashboard` |

## Override

User-named vibe always wins over project-default vibe. e.g. `/design vibe island art-deco` → SwiftUI surface (from project alias) + art-deco vibe (from explicit name) + dashboard archetype (project default).

## Adding new aliases

Append to the table above when a new project gets a working name. Keep aliases case-insensitive substring; avoid collisions (don't add "design" as a project alias).
