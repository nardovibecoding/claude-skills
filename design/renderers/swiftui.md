# renderers/swiftui — SwiftUI emit + HIG audit + Liquid Glass

DTCG `tokens.json` → Swift code. HIG-conformant. iOS 26 Liquid Glass aware.

## Output structure

```
<project>/
  Sources/<Module>/Design/
    Tokens+Color.swift     // Color extensions
    Tokens+Font.swift      // Font.custom + size constants
    Tokens+Spacing.swift   // CGFloat constants
    Tokens+Radius.swift    // CGFloat constants
    Tokens+Shadow.swift    // ShadowStyle structs
    Tokens+Motion.swift    // Animation presets
  Resources/Fonts/         // bundled .ttf/.otf files (if custom)
```

## Color emit

DTCG hex `#0071e3` → Swift `Color(hex: "#0071e3")` via extension:

```swift
import SwiftUI

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet(charactersIn: "#"))
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let r = Double((int >> 16) & 0xff) / 255
        let g = Double((int >> 8) & 0xff) / 255
        let b = Double(int & 0xff) / 255
        self.init(.sRGB, red: r, green: g, blue: b, opacity: 1)
    }
}

extension Color {
    // Generated from tokens.json
    static let brandPrimary    = Color(hex: "#0071e3")
    static let brandPrimaryFg  = Color(hex: "#ffffff")
    static let surfaceBg       = Color(hex: "#f5f5f7")
    static let surfaceCard     = Color(hex: "#ffffff")
    static let textPrimary     = Color(hex: "#1d1d1f")
    static let textSecondary   = Color(hex: "#6e6e73")
}
```

For wide-gamut OKLch tokens: emit `Color(.displayP3, ...)` via custom transform.

Dark mode: emit `Color(light: ..., dark: ...)` helper or use Asset Catalog generation.

## Font emit

```swift
extension Font {
    static func body() -> Font   { .custom("Inter", size: 16, relativeTo: .body) }
    static func title() -> Font  { .custom("Inter", size: 28, relativeTo: .title2).weight(.semibold) }
    static func mono() -> Font   { .custom("JetBrainsMono-Regular", size: 14, relativeTo: .body) }
}
```

Custom fonts must be:
1. Added to `Resources/Fonts/`.
2. Listed in `Info.plist` under `UIAppFonts` (iOS) or `ATSApplicationFontsPath` (macOS).
3. Loaded with PostScript name (NOT family name).

## Spacing + Radius

```swift
enum Space {
    static let xs:  CGFloat = 4
    static let sm:  CGFloat = 8
    static let md:  CGFloat = 16
    static let lg:  CGFloat = 24
    static let xl:  CGFloat = 32
}

enum Radius {
    static let sm: CGFloat = 4
    static let md: CGFloat = 8
    static let lg: CGFloat = 12
    static let xl: CGFloat = 16
    static let pill: CGFloat = 999
}
```

## Shadow + Motion

```swift
struct ShadowStyle {
    let color: Color
    let radius: CGFloat
    let x: CGFloat
    let y: CGFloat
}

enum Shadow {
    static let sm = ShadowStyle(color: .black.opacity(0.05), radius: 4, x: 0, y: 1)
    static let md = ShadowStyle(color: .black.opacity(0.08), radius: 12, x: 0, y: 4)
}

enum Motion {
    static let fast   = Animation.easeOut(duration: 0.15)
    static let normal = Animation.easeOut(duration: 0.25)
    static let slow   = Animation.easeOut(duration: 0.4)
}
```

## HIG audit checklist (run on every Swift output)

- [ ] **Hit targets** ≥ 44×44pt (iOS) or 28×28pt (macOS controls).
- [ ] **Dynamic Type** supported — use `.font(.body)` over hardcoded sizes when possible, or pair `.custom(..., relativeTo:)`.
- [ ] **Dark mode** — every color works in both schemes; use Asset Catalog or `Color(light:dark:)` helper.
- [ ] **System materials** preferred over custom blur — `.background(.ultraThinMaterial)` instead of hand-rolled.
- [ ] **Toolbar items** use `ToolbarItem` + `placement` correctly.
- [ ] **Lists** use `List` + `ForEach` with stable IDs, not custom VStack.
- [ ] **Navigation** uses `NavigationStack` (iOS 16+) or `NavigationSplitView` (multi-pane).
- [ ] **Accessibility labels** on every interactive element, especially icon-only buttons.
- [ ] **Reduced motion** respected — `@Environment(\.accessibilityReduceMotion)` checked before `.animation()`.
- [ ] **Increased contrast** respected — secondary colors have sufficient contrast for AX prefs.

## iOS 26 Liquid Glass

`.glassEffect(.regular)` for translucent surfaces over rich backgrounds. Use sparingly — one signature surface per screen. Materials hierarchy:

| Hierarchy | Modifier |
|---|---|
| Translucent overlay (cards over bg image) | `.glassEffect(.regular)` |
| Subtle elevation (sheets, popovers) | `.background(.regularMaterial)` |
| Solid surface (dashboards, dense UI) | `.background(Color.surfaceCard)` |

Liquid Glass requires iOS 26+. Provide `@available` fallback to `.ultraThinMaterial` for iOS 17-25.

## macOS-specific

- **Toolbar**: `.toolbar { ToolbarItemGroup(placement: .primaryAction) { ... } }`.
- **Sidebar**: `NavigationSplitView { sidebar } detail: { ... }`. Width 200-280pt.
- **Window controls**: `.windowStyle(.hiddenTitleBar)` for chromeless; respect traffic-light spacing.
- **Density**: macOS dense — row heights 22-28pt, not iOS 44pt.

## Recommended emit pipeline

Option A: **Style Dictionary v4** with custom Swift transform.
- Pro: cross-platform, mature.
- Con: requires Node toolchain.

Option B: **SwiftTokenGen** (CLI, dedicated to Swift).
- Pro: pure Swift toolchain, simple.
- Con: smaller community.

Pick A for projects that already emit web + Swift; B for Swift-only.

## Reference repos

- `lightscape-jm/swiftui-hig-audit` — HIG checklist agent.
- `199-biotechnologies/swiftui-claude-skills` — Liquid Glass patterns.

## Lint integration

After emit, run `checks/lint.md` rule `hardcoded-hex-in-renderer-output` over `*.swift` to ensure no literal hex bypassed tokens. Run `checks/anti-slop.md` over emitted views to enforce accent-twice rule.
