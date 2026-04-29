# renderers/html — CSS vars + Tailwind v4

DTCG → CSS custom properties + Tailwind v4 `@theme` block. React component scaffolds.

## Output structure

```
<project>/
  src/
    styles/
      tokens.css       // :root vars (auto-generated from tokens.json)
      theme.css        // Tailwind v4 @theme block
      globals.css      // imports + dark-mode + resets
    components/
      ui/              // base components consuming tokens
```

## CSS custom properties emit

```css
/* tokens.css — auto-generated, DO NOT EDIT */
:root {
  --color-brand-primary:    oklch(0.62 0.18 250);
  --color-brand-primary-fg: oklch(1.00 0 0);
  --color-surface-bg:       oklch(0.97 0.005 250);
  --color-surface-card:     oklch(1.00 0 0);
  --color-text-primary:     oklch(0.20 0.01 250);
  --color-text-secondary:   oklch(0.50 0.01 250);

  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;

  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;

  --font-sans: 'Inter', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, monospace;

  --shadow-sm: 0 1px 2px rgba(0,0,0,0.04);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.08);

  --motion-fast:   150ms;
  --motion-normal: 250ms;
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
}

[data-theme="dark"] {
  --color-surface-bg:   oklch(0.15 0.005 250);
  --color-surface-card: oklch(0.18 0.008 250);
  --color-text-primary: oklch(0.94 0.005 250);
  /* ... */
}
```

## Tailwind v4 `@theme`

```css
/* theme.css */
@import "tailwindcss";

@theme {
  --color-brand: var(--color-brand-primary);
  --color-bg:    var(--color-surface-bg);
  --color-card:  var(--color-surface-card);
  --color-fg:    var(--color-text-primary);
  --color-muted: var(--color-text-secondary);

  --spacing-xs: var(--space-xs);
  --spacing-sm: var(--space-sm);
  --spacing-md: var(--space-md);

  --radius-md: var(--radius-md);

  --font-sans: var(--font-sans);
  --font-mono: var(--font-mono);
}
```

Tailwind v4 picks up these as utilities: `bg-brand`, `text-fg`, `p-md`, `rounded-md`, `font-sans`.

## React component scaffold

```tsx
// Button.tsx — token-only, no literals
import { cn } from '@/lib/cn';

export function Button({
  variant = 'primary',
  className,
  ...props
}: { variant?: 'primary' | 'ghost' } & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={cn(
        'rounded-md px-md py-sm font-medium transition-colors',
        variant === 'primary' && 'bg-brand text-bg hover:opacity-90',
        variant === 'ghost'   && 'text-fg hover:bg-card',
        className
      )}
      {...props}
    />
  );
}
```

NO literal hex / px / pt anywhere in components. Every value via token utility.

## Dark mode strategy

Two options:

**A. Data attribute** (recommended for explicit toggle):
```html
<html data-theme="dark"> ... </html>
```
```css
[data-theme="dark"] { --color-surface-bg: oklch(0.15 ...); }
```

**B. Media query** (auto-follows OS):
```css
@media (prefers-color-scheme: dark) {
  :root { --color-surface-bg: oklch(0.15 ...); }
}
```

Use A for projects with theme toggle UI. Use B for set-and-forget marketing sites.

## Build pipeline

Style Dictionary v4 config:

```js
// style-dictionary.config.js
export default {
  source: ['design/tokens.json'],
  platforms: {
    css: {
      transformGroup: 'css',
      buildPath: 'src/styles/',
      files: [{ destination: 'tokens.css', format: 'css/variables', options: { outputReferences: true } }]
    }
  }
};
```

Run on `pnpm build` via prebuild script. CSS output is generated, NEVER hand-edited.

## Sample emitted globals.css

```css
@import './tokens.css';
@import './theme.css';

* { box-sizing: border-box; margin: 0; padding: 0; }

html { font-family: var(--font-sans); color: var(--color-fg); background: var(--color-bg); }

body { line-height: 1.5; }

a { color: var(--color-brand); text-decoration: none; }
a:hover { opacity: 0.85; }

button { font: inherit; cursor: pointer; }

:focus-visible {
  outline: 2px solid var(--color-brand);
  outline-offset: 2px;
}
```

## Lint integration

After emit:
- `hardcoded-hex-in-renderer-output` lint over `src/components/**/*.{tsx,css}`.
- `off-scale-spacing` lint over CSS for `padding`/`margin` values not in `--space-*` scale.
- `font-count` over the project — no more than 2 font families.
