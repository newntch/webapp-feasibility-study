# Svelte and SvelteKit

Read this when the task touches Svelte components, SvelteKit routes, client-heavy UI, or Rails-mounted Svelte islands.

## Table of contents

- [Role](#role)
- [Project inspection](#project-inspection)
- [Component discipline](#component-discipline)
- [State](#state)
- [Styling](#styling)
- [SvelteKit](#sveltekit)
- [Motion](#motion)
- [Rails islands](#rails-islands)
- [Testing](#testing)

## Role

Use Svelte for rich client-side interaction, not as a reflex. It is a good fit for:

- Complex local state.
- Rich filtering, sorting, and exploration.
- Live previews.
- Drag/drop or canvas-like UI.
- Interactive onboarding.
- Product surfaces where a Rails partial plus Stimulus would become tangled.

Use Rails and Hotwire for normal CRUD, settings, forms, account pages, and static product pages unless the existing app says otherwise.

## Project inspection

Look for:

- `package.json`, `pnpm-lock.yaml`, `yarn.lock`, `package-lock.json`
- `svelte.config.*`
- `vite.config.*`
- `src/routes`, `src/lib`
- Existing store patterns.
- Existing CSS conventions.
- Test setup: Vitest, Playwright, Testing Library.

Respect the existing Svelte version and syntax. Do not force new syntax into an older codebase.

## Component discipline

Keep components small and named by product purpose, not by aesthetic. Prefer:

- `AccountEmailForm.svelte`
- `BillingPlanSummary.svelte`
- `InviteMemberDialog.svelte`
- `DocumentFilterPanel.svelte`

Avoid:

- `GlassCard.svelte`
- `AnimatedThing.svelte`
- `BentoItem.svelte` when the product concept is more specific.

## State

Use local component state first. Use shared stores only when state genuinely crosses component boundaries. Keep derived values derived, not manually synchronized.

Do not import React concepts:

- No hooks mental model.
- No `use client`.
- No Zustand/Jotai pattern by default.
- No Motion hooks.

For high-frequency pointer or scroll work, prefer CSS, Svelte actions, or direct DOM values with cleanup. Avoid re-rendering large trees on every frame.

## Styling

Prefer scoped Svelte styles and shared semantic tokens. Use plain CSS modules or layers for global systems. Tailwind is acceptable only when already installed or requested.

Use classes that reveal product intent:

```svelte
<section class="billing-summary">
  <h2>Current plan</h2>
</section>

<style>
  .billing-summary {
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
  }
</style>
```

## SvelteKit

Use SvelteKit conventions when present:

- `+page.svelte` for route UI.
- `+layout.svelte` for shared shell.
- Server load functions for server data.
- Form actions for normal mutations.
- Progressive enhancement for forms when it helps.
- Error boundaries for failure states.

Do not move server concerns into client stores when SvelteKit already gives a server path.

## Motion

Use Svelte transitions only when they communicate entry, exit, or state change. Keep durations short. Avoid scroll drama by default.

Always respect reduced motion:

```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

## Rails islands

When Svelte is mounted inside Rails:

- Keep the island boundary explicit.
- Pass only the props the island needs.
- Preserve server-rendered fallback or empty-state markup when possible.
- Avoid duplicating Rails routing and permissions in the client.
- Clean up mounted instances when Turbo caches or replaces pages.

## Testing

Prefer tests that match the UI risk:

- Component tests for stateful pieces.
- Playwright for flows and keyboard behavior.
- Existing project lint and type checks.

Report only checks that actually ran.
