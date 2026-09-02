# Rails, Hotwire, and product UI

Read this when the task touches Rails views, Rails product UI, Hotwire, Turbo, Stimulus, ViewComponent, Phlex, forms, routing, or Rails asset styling.

## Table of contents

- [Defaults](#defaults)
- [Project inspection](#project-inspection)
- [Component choice](#component-choice)
- [Hotwire rules](#hotwire-rules)
- [Forms](#forms)
- [Rails CSS](#rails-css)
- [Accessibility](#accessibility)
- [Redesign safety](#redesign-safety)
- [Checks](#checks)

## Defaults

Prefer the Rails path:

1. Server-render semantic HTML.
2. Use Turbo Drive, Frames, and Streams for navigation and partial updates.
3. Use Stimulus for small behavior that belongs near the DOM.
4. Use Svelte only for rich islands that exceed Stimulus.
5. Add no SPA architecture unless the app already has one.

Respect existing Rails conventions before introducing new ones.

## Project inspection

Look for:

- `Gemfile`, `Gemfile.lock`
- `app/views`, `app/helpers`, `app/components`
- `app/assets/stylesheets`, `app/javascript`
- `config/importmap.rb`, `package.json`, `vite.config.*`
- `Procfile.dev`, `bin/dev`
- Existing component conventions: partials, ViewComponent, Phlex, Cells, custom presenters.
- Existing CSS conventions: propshaft, sprockets, cssbundling-rails, tailwindcss-rails, dartsass-rails, vite.

Do not import libraries before checking what is already installed.

## Component choice

Use the smallest component boundary that keeps the view clear:

- Plain partials for one-off composition.
- Helpers for tiny formatting only.
- ViewComponent when the project already uses it or when the component needs tests, slots, variants, or reuse across many views.
- Phlex when the project already uses it or the team prefers Ruby component trees.
- Svelte island when the interaction has complex client state, drag/drop, rich filtering, or local UI logic that Stimulus would make awkward.

Do not add ViewComponent or Phlex just to avoid writing a partial.

## Hotwire rules

Turbo Frame is for replacing a bounded region. Turbo Stream is for broadcasting or applying multiple DOM changes. Stimulus is for behavior.

Use stable DOM ids from Rails helpers where possible. Preserve URL semantics and browser history. Keep forms functional without custom JavaScript first, then enhance.

Good Stimulus uses:

- `data-controller` for a small behavior.
- `data-action` for user events.
- `data-*-target` for DOM references.
- `values` for configuration.
- Cleanup in `disconnect()` for timers, observers, and event listeners.

Do not use Stimulus as an app-wide state manager.

## Forms

Use Rails form helpers and native browser behavior. Labels go above inputs. Place helper text near the field. Place errors below the field and connect them with `aria-describedby`.

For settings and account pages:

- Group fields by user mental model.
- Keep Save behavior obvious.
- Show pending and success states.
- Avoid auto-save unless the project already uses it consistently.
- Make destructive actions visually and structurally separate.

For billing-lite:

- Show current plan.
- Show billing interval and renewal details if available.
- State consequences before downgrade, cancel, or delete.
- Avoid dark patterns and forced urgency.

## Rails CSS

Prefer plain CSS layers and semantic classes. A good Rails CSS shape:

```css
@layer reset, tokens, base, components, utilities;

@layer tokens {
  :root {
    --color-bg: #f7f7f4;
    --color-surface: #ffffff;
    --color-text: #1d1d1b;
    --color-muted: #64645f;
    --color-border: #deded8;
    --color-accent: #315c45;
    --radius-sm: 6px;
    --radius-md: 10px;
    --space-4: 1rem;
  }
}

@layer components {
  .settings-section {
    border-block-start: 1px solid var(--color-border);
    padding-block: var(--space-4);
  }
}
```

Use BEM-ish or scoped component classes when it improves readability. Keep utility classes small and local.

Tailwind is acceptable when the Rails app already uses it. Do not introduce it as the default.

## Accessibility

Rails views still need full UI states:

- Native labels.
- Correct heading order.
- Focus-visible styles.
- Keyboard access for disclosure, menus, modals, and custom controls.
- Inline validation messages.
- Flash messages that are announced when relevant.
- Server-rendered errors that survive failed submissions.

## Redesign safety

Do not silently change:

- Route names or path helpers.
- Form field names.
- Button labels that analytics tracks.
- DOM ids used by Turbo Streams or tests.
- Legal, consent, or billing copy.
- Existing accessibility affordances.

## Checks

Run the smallest relevant checks available in the project, such as:

- `bin/rails test`
- `bin/rails test:system`
- `bundle exec rubocop`
- `bin/dev` for manual view checks
- Existing project scripts in `package.json`

Report only checks that actually ran.
