# CSS and semantic tokens

Read this when creating or editing styling, tokens, themes, layout primitives, responsive behavior, or component CSS.

## Table of contents

- [Preference](#preference)
- [Token shape](#token-shape)
- [Layers](#layers)
- [Theme](#theme)
- [Typography](#typography)
- [Color](#color)
- [Shape](#shape)
- [Layout](#layout)
- [Focus](#focus)
- [Reduced motion](#reduced-motion)
- [Contrast](#contrast)

## Preference

Prefer plain CSS layers, CSS modules, scoped Svelte CSS, or app-local component CSS. Tailwind is not the default. Use Tailwind only when the existing project already uses it or the user asks for it.

## Token shape

Use semantic tokens, not raw palette names in components.

Good:

```css
:root {
  --color-bg: #f7f7f4;
  --color-surface: #ffffff;
  --color-surface-subtle: #f0f0eb;
  --color-text: #1d1d1b;
  --color-muted: #64645f;
  --color-border: #deded8;
  --color-accent: #315c45;
  --color-accent-text: #ffffff;

  --font-sans: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;

  --radius-xs: 4px;
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;

  --space-1: .25rem;
  --space-2: .5rem;
  --space-3: .75rem;
  --space-4: 1rem;
  --space-6: 1.5rem;
  --space-8: 2rem;
  --space-12: 3rem;
}
```

Component CSS should use tokens:

```css
.account-card {
  background: var(--color-surface);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-6);
}
```

## Layers

For global CSS, use a small layer model:

```css
@layer reset, tokens, base, components, utilities;
```

- `reset`: normalize browser quirks.
- `tokens`: variables only.
- `base`: body, type, links, focus defaults.
- `components`: named product components.
- `utilities`: tiny helpers that are worth repeating.

Keep utilities sparse. A utility system should not become Tailwind by hand.

## Theme

Do not require dual mode by default. Respect the existing app choice:

- Existing light-only app: preserve light unless asked.
- Existing dark-only app: preserve dark unless asked.
- System-aware app: use semantic tokens for both.
- SwiftUI: use system appearance unless brand requirements override.

Never invert random sections mid-page. A page has one theme family.

## Typography

Use system fonts unless the brand or existing app uses something else. For Rails and Svelte, self-host brand fonts when needed. Keep body copy readable. Avoid tiny gray text as a style.

Use one type system:

- Product UI: system sans and clear hierarchy.
- Docs: comfortable line length, generous line height, strong headings.
- Marketing: restrained display scale, never shouting.

## Color

Choose one accent per surface. Use it consistently. Desaturate unless the brand requires saturation. Avoid AI-purple and blue glow defaults.

Never use color alone to communicate state. Pair color with text, icon, or position.

## Shape

Pick one radius system and follow it. For example:

- Inputs: `var(--radius-sm)`
- Buttons: `var(--radius-sm)`
- Cards: `var(--radius-md)`
- Pills: full radius only for real pills

Do not mix pill buttons with square cards unless the rule is deliberate and consistent.

## Layout

Prefer CSS Grid for page structure and Flexbox for local alignment. Avoid calc-based flex math.

Use container classes with semantic names:

```css
.page-shell {
  width: min(100% - 2rem, 72rem);
  margin-inline: auto;
}
```

Use `min-height: 100dvh` for viewport sections, not `100vh`, when a full viewport section is truly needed.

## Focus

Every interactive element needs a visible focus state. Use `:focus-visible`. Do not remove outlines without replacing them.

```css
:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 3px;
}
```

## Reduced motion

Gate non-essential animation:

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    scroll-behavior: auto !important;
    transition-duration: 0.01ms !important;
  }
}
```

## Contrast

Check text, placeholders, focus rings, disabled states, and buttons against the actual background. Do not ship low-contrast gray on off-white just because it looks calm.
