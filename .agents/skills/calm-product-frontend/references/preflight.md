# Final preflight

Run this before delivering UI or code. Fix failures before final output.

## Context

- Design read stated.
- Stack inspected before adding dependencies.
- Existing conventions preserved unless the user asked to change them.
- Correct reference files read for Rails, Svelte, Swift, CSS, or copy.
- Dials inferred and followed.

## Stack

- Rails work stays server-rendered by default.
- Turbo, Stimulus, Rails helpers, partials, ViewComponent, or Phlex are used appropriately.
- Svelte is used only where richer client behavior is justified or already present.
- SwiftUI work follows Apple platform conventions and native controls.
- React, Next, Tailwind, shadcn, Radix, Motion, and GSAP are not introduced by reflex.
- Dependencies were checked before import.

## Styling

- Plain CSS layers, modules, scoped Svelte CSS, or existing project styling used.
- Semantic tokens exist or existing tokens were reused.
- Tailwind is used only if already present or requested.
- One accent color per surface.
- One radius system.
- Focus-visible styles are present.
- Contrast works for text, controls, placeholders, disabled states, and errors.
- Theme choice respects the existing app and does not flip randomly by section.

## Layout

- Navigation fits on one line at desktop when present.
- Primary action is clear.
- No duplicate CTA intent.
- Labels are clear and close to controls.
- Forms have labels above inputs, helper text where useful, and errors below.
- Product UI includes loading, empty, error, disabled, pending, and success states as relevant.
- Small-screen layout is explicit.
- No fake dashboards, fake terminal windows, or div-based product screenshots.
- No three equal feature cards unless that is truly the clearest structure.

## Motion

- Motion is at or below the inferred `MOTION_INTENSITY`.
- Every animation communicates feedback, hierarchy, continuity, or state change.
- Reduced-motion behavior exists.
- No scroll hijack, parallax, marquee filler, magnetic cursor, particles, or perpetual animation by default.
- Timers, observers, and event listeners clean up.

## Copy

- Every visible string was reread.
- Copy is plain, specific, and true.
- No startup filler words.
- No fake numbers, fake customers, fake testimonials, or fake urgency.
- No decorative "trusted by" section without real proof.
- No decorative weather, locale, version, status dot, or section-number labels.
- No em dash character anywhere in visible output.
- CTA labels do not wrap at desktop.

## Rails safety

- Route slugs, path helpers, form field names, Turbo DOM ids, analytics hooks, legal copy, and brand marks were not silently changed.
- Server-rendered fallbacks still work where relevant.
- Validation errors survive failed submissions.

## Swift safety

- Dynamic Type considered.
- VoiceOver labels and order considered.
- Hit targets are adequate.
- Reduce Motion and Reduce Transparency considered.
- Localization length considered where relevant.
- Previews updated when the project uses them.

## Final response

- State what changed.
- State checks run.
- Do not claim tests passed unless they did.
- Keep the explanation calm and concrete.
