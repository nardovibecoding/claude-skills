# renderers/extension — Chrome MV3 popup

Manifest v3 constraints. Locally bundled Tailwind. CSP-compliant. Shadow DOM for content scripts.

## MV3 hard rules

- **NO remote code**: no CDN scripts, no eval, no `unsafe-inline`. Everything bundled in the extension.
- **NO inline `<style>` or `<script>`** in popup HTML. Use external files.
- **CSP** restricts to `script-src 'self'`. Tailwind must compile to a static CSS file at build time.
- **Service worker** has no DOM. UI surfaces are popups + side panels + content scripts only.
- **No DOM in service-worker.js** — UI work happens in popup or content script.

## File structure

```
extension/
  manifest.json
  popup/
    popup.html
    popup.css         (compiled Tailwind, bundled)
    popup.tsx         (React, bundled via vite/webpack)
  content/
    content.tsx       (Shadow DOM injection)
    content.css       (scoped, bundled)
  background/
    service-worker.js
  assets/
    tokens.css        (DTCG-emitted custom properties)
    icon-16.png, icon-48.png, icon-128.png
  vite.config.ts      (or webpack.config.js)
```

## Sample manifest.json

```json
{
  "manifest_version": 3,
  "name": "My Extension",
  "version": "0.1.0",
  "action": {
    "default_popup": "popup/popup.html",
    "default_icon": { "16": "assets/icon-16.png", "48": "assets/icon-48.png" }
  },
  "background": {
    "service_worker": "background/service-worker.js",
    "type": "module"
  },
  "content_scripts": [{
    "matches": ["<all_urls>"],
    "js": ["content/content.js"],
    "css": ["content/content.css"]
  }],
  "permissions": ["storage"],
  "host_permissions": ["https://*/*"],
  "content_security_policy": {
    "extension_pages": "script-src 'self'; object-src 'self'"
  }
}
```

## popup.html scaffold

```html
<!doctype html>
<html data-theme="light">
  <head>
    <meta charset="utf-8">
    <link rel="stylesheet" href="../assets/tokens.css">
    <link rel="stylesheet" href="popup.css">
    <title>Popup</title>
  </head>
  <body class="popup">
    <div id="root"></div>
    <script type="module" src="popup.js"></script>
  </body>
</html>
```

## popup.css (bundled Tailwind output)

Build: `tailwindcss -i ./popup/popup.src.css -o ./popup/popup.css`. Source:

```css
@import 'tailwindcss';
@import '../assets/tokens.css';

@theme {
  --color-bg:    var(--color-surface-bg);
  --color-card:  var(--color-surface-card);
  --color-fg:    var(--color-text-primary);
  --color-brand: var(--color-brand-primary);
}

.popup {
  width: 360px;
  min-height: 200px;
  max-height: 600px;
  background: var(--color-bg);
  color: var(--color-fg);
  font-family: var(--font-sans);
  padding: var(--space-md);
}
```

## Popup constraints

- **Width**: 320-800px, sweet spot 360-420px.
- **Height**: variable up to 600px max (Chrome enforces).
- **No external resources** at runtime — all fonts, images bundled.
- **No autofocus stealing** from page — popup focus management is local.

## Content-script Shadow DOM

To avoid host-page CSS bleed, mount React inside Shadow DOM:

```tsx
// content.tsx
import { createRoot } from 'react-dom/client';
import App from './App';
import cssText from './content.css?inline';

const host = document.createElement('div');
host.id = '__my-ext-root';
document.body.appendChild(host);

const shadow = host.attachShadow({ mode: 'open' });
const styleEl = document.createElement('style');
styleEl.textContent = cssText;
shadow.appendChild(styleEl);

const mount = document.createElement('div');
shadow.appendChild(mount);

createRoot(mount).render(<App />);
```

Tokens travel via the bundled `tokens.css` (imported as inline via `?inline` in Vite). Shadow DOM completely isolates from host site.

## Service worker UI

Service workers have no DOM. Inter-component messaging:

```js
// service-worker.js
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === 'GET_DATA') {
    chrome.storage.local.get('key').then(sendResponse);
    return true; // async response
  }
});
```

Popup → SW: `chrome.runtime.sendMessage({type:'GET_DATA'})`.

## Bundler config (Vite)

```ts
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { crx } from '@crxjs/vite-plugin';
import manifest from './manifest.json';

export default defineConfig({
  plugins: [react(), crx({ manifest })],
});
```

`@crxjs/vite-plugin` handles MV3 bundling, HMR for popup, and content-script reloading.

## Lint integration

After build:
- Inspect `dist/` for any `<script src="http">` or external font URLs — block as MV3 violations.
- Run `hardcoded-hex-in-renderer-output` over `popup.tsx` + `content.tsx`.
- Verify CSP in manifest doesn't relax to `unsafe-inline`.

## Reference pattern

Pattern after `theluckystrike/chrome-extension-starter-mv3`. Don't copy verbatim — describe the pattern, write fresh code matching project's stack.
