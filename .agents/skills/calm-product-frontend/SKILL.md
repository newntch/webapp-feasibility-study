---
name: calm-product-frontend
description: Calm anti-SaaS frontend and product UI skill for Rails/Hotwire, Svelte/SvelteKit, and Swift/SwiftUI. Use when building or redesigning Rails product surfaces, settings/account/onboarding/billing-lite flows, landing pages, docs, changelogs, support pages, portfolio pages, or native Apple app screens with quiet, durable, human, non-hype visual design and copy.
---

# Calm Product Frontend Skill

Design and implement product interfaces that feel calm, useful, native to the stack, and free of SaaS theater. Prefer boring reliability over ornamental novelty. The default center of gravity is Rails, Hotwire, plain CSS, Svelte where useful, and SwiftUI for Apple platforms.

## Reference loading

Keep this file in context. Read a reference only when the task touches that area:

- Rails, Hotwire, Turbo, Stimulus, ViewComponent, Phlex: `references/rails.md`
- Svelte or SvelteKit, including Rails-mounted islands: `references/svelte.md`
- Swift, SwiftUI, Apple platforms: `references/swift.md`
- Plain CSS layers, modules, semantic tokens, responsive systems: `references/css-and-tokens.md`
- Calm anti-SaaS copy and visual taste: `references/copy-and-calm-style.md`
- Final quality gate: `references/preflight.md`

## 1. Read the room

Before touching code, infer what the user actually wants.

Look for:

1. Surface type: marketing page, Rails product UI, settings, account, onboarding, billing-lite, docs, changelog, support, portfolio, native Apple screen, redesign.
2. Audience: a solo founder, existing customers, internal operators, technical buyers, app-store users, support readers, procurement, or a public audience.
3. Existing stack: Gemfile, package.json, app/views, app/components, app/javascript, app/frontend, config/importmap.rb, vite config, SvelteKit routes, Package.swift, Xcode project files.
4. Existing taste: typography, spacing, copy voice, tokens, radii, icon family, screenshots, native controls, accessibility wins.
5. Quiet constraints: regulated work, payments, privacy, healthcare, public-sector, older users, dense support content. These override aesthetic preference.

Before code, state one line:

`Reading this as: <surface> for <audience>, in <stack>, with a calm <visual language>, using <implementation foundation>.`

Ask exactly one clarifying question only when two materially different directions are plausible. Otherwise proceed.

## 2. Core dials

Use these names exactly.

- `DESIGN_VARIANCE`: 4 by default. 1 is strict utility, 10 is experimental composition.
- `MOTION_INTENSITY`: 2 by default. 1 is static, 10 is cinematic.
- `VISUAL_DENSITY`: 3 by default. 1 is sparse editorial, 10 is cockpit UI.

Presets:

| Signal | DESIGN_VARIANCE | MOTION_INTENSITY | VISUAL_DENSITY |
|---|---:|---:|---:|
| Calm product surface | 3-4 | 1-2 | 4-6 |
| Landing page for a real product | 4-5 | 2-3 | 3-4 |
| Docs, changelog, support | 2-4 | 1 | 4-6 |
| Portfolio or personal site | 4-6 | 2-3 | 3 |
| Public-sector or regulated | 2-3 | 1 | 5-6 |
| Native SwiftUI app | 2-4 | 1-2 | match platform |
| Redesign preserve | match existing | match or -1 | match |
| Redesign overhaul | existing + 1 | 2 max by default | match |

Do not ask the user to set dials. Infer them and mention them briefly.

## 3. Stack defaults

Existing project conventions win. Never replace the stack to satisfy an aesthetic.

### Rails first

Prefer server-rendered Rails with semantic HTML, Turbo, and small Stimulus controllers. Reach for Hotwire before a client-side app. Use Rails form helpers, validation errors, flash messages, partials, ViewComponent, or Phlex according to the project.

Default styling is plain CSS with layers, semantic tokens, and scoped component classes. Do not introduce Tailwind unless the project already uses it or the user asks for it.

### Svelte where useful

Use Svelte or SvelteKit for richer client-side interfaces, complex local state, and high-interaction islands. Keep Svelte components idiomatic. Do not import React mental models like hooks, Server Components, Zustand, `use client`, or Motion hooks.

### Swift is first-class

For Apple surfaces, design in SwiftUI with Apple platform conventions. Prefer native controls, system typography, semantic colors, SF Symbols, Dynamic Type, VoiceOver, and subtle native transitions. Do not translate web gimmicks into native UI.

### React is not the default

Use React or Next only when the existing project already uses them or the user explicitly asks. Do not add shadcn, Radix Themes, Motion, GSAP, or Tailwind as a reflex.

## 4. Calm anti-SaaS style

The style baseline is quiet, durable, human, product-respecting, and text-forward.

Prefer:

- Specific product language over startup slogans.
- Real interface screenshots, real diagrams, or no visual.
- One useful CTA per intent.
- Native controls and predictable flows.
- Plain labels that explain what happens next.
- Spacious but useful layouts.

Avoid by default:

- Gradient hero theater, AI-purple glows, glass panels everywhere, bento-as-decoration.
- Fake urgency, fake scarcity, fake waitlists, fake metrics, fake customers, fake testimonials.
- "Trusted by" unless the logos are real and relevant.
- Decorative dashboards, fake terminal windows, div-based product screenshots.
- Startup verbs: unlock, elevate, unleash, revolutionize, seamless, next-gen, supercharge.
- Overly humble craft language: field notes, quietly in use, on our desks, from the workshop.
- Decorative status dots, weather strips, version stamps, section-number eyebrows, scroll cues.
- The em dash character. Use a comma, period, colon, or regular hyphen.

A pure text page is allowed when it serves the product. Do not add generated lifestyle imagery to fill space.

## 5. Design systems and tokens

Do not default to a design-system package. Start from the app's own tokens, native platform conventions, and existing components.

Reach for official systems only when the product context requires them, such as GOV.UK, USWDS, Polaris, Fluent, Carbon, Primer, Material, or Atlassian. Use one system per project.

For all other work, define semantic tokens:

- Color: `--color-bg`, `--color-surface`, `--color-text`, `--color-muted`, `--color-border`, `--color-accent`.
- Typography: `--font-sans`, `--font-mono`, text sizes, line heights.
- Shape: one radius scale with clear rules.
- Spacing: predictable steps, not one-off magic values.
- Shadow: rare, subtle, and tied to real elevation.

Tailwind may consume these tokens if already present, but Tailwind is not the source of truth.

## 6. Layout rules

Use layouts that help people act.

- Product UI: prioritize scan paths, labels, grouping, inline help, validation, empty states, and clear hierarchy.
- Marketing: lead with the concrete outcome, not brand theater.
- Docs and support: optimize findability, headings, examples, and next actions.
- Settings and account: use plain forms, clear save behavior, predictable sections.
- Billing-lite: be transparent, avoid dark patterns, show plan state and consequences.
- Native apps: use platform navigation, list, form, sheet, alert, and toolbar conventions.

Keep heroes compact. Keep navigation on one line at desktop. Do not repeat the same section layout more than twice in a row. Do not use three equal feature cards unless that is genuinely the clearest information shape.

## 7. Motion policy

Default motion is low. Use motion for feedback, hierarchy, and state changes, not spectacle.

Allowed by default:

- CSS transitions for hover, focus, press, disclosure, and small state changes.
- Turbo-native navigation changes and inline updates.
- Svelte transitions when they clarify entry, exit, or local state.
- SwiftUI transitions that feel native and respect platform expectations.

Banned by default:

- Scroll hijacking, parallax, cinematic reveals, marquee filler, magnetic cursors, cursor trails, particle effects, GSAP choreography, perpetual animations.
- Animation that depends on React state for scroll, pointer, or frame-by-frame values.
- Motion that fails under `prefers-reduced-motion` or Apple Reduce Motion.

For any animation, be able to state what it communicates in one sentence.

## 8. Visual assets

Use this priority order:

1. Real product screenshots or recorded UI frames from the project.
2. Real photography supplied by the user or already in the product.
3. Simple diagrams, annotated screenshots, or native UI previews.
4. No image, when the words and layout are enough.

Do not generate lifestyle images by default. Do not fabricate product screenshots. Do not build fake dashboards from div rectangles. Do not use placeholder photo captions as decoration.

## 9. Product states

Never ship only the happy state. Include or preserve:

- Loading state that matches the final layout.
- Empty state with a useful next action.
- Error state with recovery path.
- Disabled and pending states.
- Success confirmation where needed.
- Form validation and helper text.
- Keyboard, screen-reader, reduced-motion, and small-screen behavior.

Use skeletons sparingly. For calm products, an inline pending label or disabled button is often better than shimmer.

## 10. Redesign protocol

Detect mode first:

- Preserve: keep IA, routes, copy voice, brand recognition, analytics events, and accessibility wins. Improve typography, spacing, tokens, states, and clarity.
- Overhaul: change visual language but preserve content intent, slugs, forms, and SEO-critical structure unless the user approved deeper changes.
- Greenfield: build from the user brief and stack defaults.

For redesigns, audit before editing:

1. Existing stack and components.
2. Brand tokens and type.
3. Routes, nav, forms, and key actions.
4. Copy voice.
5. Accessibility and performance.
6. Things to retire.

Do not silently change route slugs, primary nav labels, form field names, legal copy, brand marks, or analytics hooks.

## 11. Implementation workflow

1. Inspect the project before importing anything. Read Gemfile, package.json, import maps, lockfiles, and existing CSS.
2. Choose the smallest architecture that fits the job.
3. Define or reuse tokens before styling components.
4. Build semantic HTML first.
5. Add CSS layers or modules.
6. Add behavior as progressive enhancement.
7. Add product states.
8. Test small screens, keyboard, focus, contrast, and reduced motion.
9. Run the relevant checks for the stack.
10. Before final output, run `references/preflight.md`.

## 12. Output style

When showing work to the user:

- Be specific about the design read and stack choice.
- Mention the dials only when useful.
- State files changed and why.
- Keep commentary calm and concrete.
- Do not oversell the result.
- Do not claim tests passed unless they were actually run.
