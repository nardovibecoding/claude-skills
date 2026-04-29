# chat — message list + composer

Conversational UI. Message list, composer, sidebar, status indicators.

## When to use

- AI chat (Claude, ChatGPT, Cursor sidebar).
- Customer support / messaging apps.
- Internal team chat (Slack-style).

## Structural skeleton

```
┌──────┬─────────────────────────────────┐
│ NAV  │ Conversation title              │
│      ├─────────────────────────────────┤
│ ▢ ←  │  ┌──────────┐                   │
│ ▢    │  │ user msg │                   │  right-aligned
│ ▢    │  └──────────┘                   │
│ ▢    │                                 │
│      │  ┌──────────────────┐           │
│      │  │ assistant reply  │           │  left-aligned
│      │  └──────────────────┘           │
│      │                                 │
│      ├─────────────────────────────────┤
│      │ [ message input… ]      [send]  │
│      └─────────────────────────────────┘
```

## Required components

- **Sidebar** (optional): conversation list, new-chat button, search.
- **Header**: conversation title + actions (rename, delete, share).
- **Message list**: scrolls, auto-stick-to-bottom.
- **User bubble**: right-aligned, accent fill.
- **Assistant bubble**: left-aligned, surface fill, supports markdown + code blocks.
- **Composer**: textarea (auto-grow), send button, attachment, model selector.
- **Status indicators**: typing, tokens, model name.

## Common mistakes

- Both bubbles same color — speaker confusion.
- Auto-scroll fights user-scroll (must detect user reading old messages).
- Code blocks not properly contained in bubble.
- Composer no enter-to-send convention shown.
- No way to edit/regenerate previous turn.

## Density rules

- Bubble max-width: 70-80% of column.
- Bubble padding: 12-16px.
- Bubble radius: 12-16px (asymmetric — flatter on speaker side).
- Composer min-height: 40-56px, max-height: 200px (then scroll).
- Vertical gap between turns: 12-16px.

## Accessibility notes

- Each message has `role="article"` with author + timestamp accessible name.
- Live region for incoming assistant messages: `aria-live="polite"`.
- Code blocks: copy button with confirmation announcement.
- Composer: `<textarea>` with label, send button has accessible name.
- Keyboard: enter sends, shift+enter new line, ↑ to edit last message.

## Sample DTCG

```json
{
  "chat": {
    "bubble-radius":  { "$type":"dimension", "$value":{"value":14,"unit":"px"} },
    "bubble-padding": { "$type":"dimension", "$value":{"value":14,"unit":"px"} },
    "user-bg":        { "$type":"color",     "$value":"{color.accent}" },
    "assistant-bg":   { "$type":"color",     "$value":"{color.surface-2}" }
  }
}
```
