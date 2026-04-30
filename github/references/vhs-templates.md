# VHS Demo Templates

VHS (by Charmbracelet) records terminal sessions as GIFs from `.tape` script files.
Install: `brew install vhs`

## Base settings (all templates)

```tape
# Save to assets/demo.gif
Output assets/demo.gif

# Terminal appearance
Set FontFamily "JetBrains Mono"
Set FontSize 16
Set Width 900
Set Height 500
Set Padding 20
Set Theme "Catppuccin Mocha"

# Typing speed
Set TypingSpeed 50ms
```

## CLI Tool Template

```tape
Output assets/demo.gif
Set FontFamily "JetBrains Mono"
Set FontSize 16
Set Width 900
Set Height 500
Set Theme "Catppuccin Mocha"
Set TypingSpeed 50ms

# Show the main command
Type "mytool --help"
Enter
Sleep 2s

# Run a real example
Type "mytool analyze ./example"
Enter
Sleep 3s

# Show key output
Sleep 2s
```

## Claude Code Skill Template

```tape
Output assets/demo.gif
Set FontFamily "JetBrains Mono"
Set FontSize 16
Set Width 900
Set Height 500
Set Theme "Catppuccin Mocha"
Set TypingSpeed 50ms

# Show install
Type "git clone https://github.com/user/skill.git ~/.claude/skills/skill-name"
Enter
Sleep 1s

# Show usage
Type "claude"
Enter
Sleep 1s
Type "audit this skill at ~/suspicious-skill/"
Enter
Sleep 4s
```

## Python Script Template

```tape
Output assets/demo.gif
Set FontFamily "JetBrains Mono"
Set FontSize 16
Set Width 900
Set Height 500
Set Theme "Catppuccin Mocha"
Set TypingSpeed 50ms

Type "python3 main.py --example"
Enter
Sleep 3s
```

## MCP Server Template

```tape
Output assets/demo.gif
Set FontFamily "JetBrains Mono"
Set FontSize 16
Set Width 900
Set Height 600
Set Theme "Catppuccin Mocha"
Set TypingSpeed 50ms

# Show the server starting
Type "python3 server.py"
Enter
Sleep 2s

# Show available tools
Type "# Available tools:"
Sleep 1s
Enter
Type "# - search_feeds, get_feed_detail, user_profile, ..."
Enter
Sleep 3s
```

## Tips
- Keep demos under 15 seconds (GIF file size)
- Show the MOST IMPRESSIVE output first
- Use `Sleep` generously so viewers can read
- Theme: dark backgrounds perform better on GitHub (most users use dark mode)
- `Set TypingSpeed 30ms` for faster demos, `80ms` for readability
- Add `Hide` / `Show` to skip boring parts (installs, loading)
- Run `vhs validate demo.tape` before recording
