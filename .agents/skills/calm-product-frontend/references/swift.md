# Swift and SwiftUI

Read this when the task touches iOS, iPadOS, macOS, watchOS, visionOS, Swift, SwiftUI, app navigation, native controls, or Apple platform design.

## Table of contents

- [Principle](#principle)
- [Project inspection](#project-inspection)
- [Interface defaults](#interface-defaults)
- [Layout](#layout)
- [Motion and haptics](#motion-and-haptics)
- [Copy](#copy)
- [Accessibility](#accessibility)
- [Previews](#previews)
- [Testing](#testing)

## Principle

Swift surfaces should feel native first and branded second. Do not port web layout tropes into SwiftUI. Use system controls, navigation, spacing, typography, colors, materials, haptics, and gestures unless the product has a clear reason not to.

## Project inspection

Look for:

- Xcode project or workspace.
- `Package.swift`.
- App entry point.
- Existing architecture: MVVM, reducers, coordinators, observation model, environment objects.
- Asset catalog, color assets, symbols, localization.
- Existing previews and tests.

Respect the app's current architecture.

## Interface defaults

Prefer:

- `NavigationStack` or platform-appropriate navigation.
- `List`, `Form`, `Section`, `DisclosureGroup`, `Sheet`, `Alert`, `ToolbarItem`.
- System type styles like `.title`, `.headline`, `.body`, `.caption`.
- Semantic colors and asset catalog colors.
- SF Symbols.
- Dynamic Type.
- VoiceOver labels and hints where visible text is not enough.
- Native focus, keyboard, pointer, and menu behavior on iPad and macOS.

Avoid:

- Web-like cards everywhere.
- Fake browser dashboards.
- Over-custom controls when native controls fit.
- Decorative gradients and glass for normal product work.
- Hard-coded text sizes that break Dynamic Type.
- Custom icon SVGs when SF Symbols covers the concept.

## Layout

Use SwiftUI layout primitives with restraint:

- `VStack`, `HStack`, `Grid`, `List`, `Form`.
- `Spacer` only when it improves actual layout.
- `frame(maxWidth:)` carefully, especially on iPad and macOS.
- Platform-specific adaptations when needed.

Respect safe areas. Do not force full-screen hero layouts into product screens.

## Motion and haptics

Motion is feedback, not showmanship.

Use:

- Small transitions for state changes.
- Native sheet and navigation transitions.
- Matched geometry only when it clarifies object continuity.
- Haptics for important confirmation or boundary feedback, not every tap.

Respect Reduce Motion. Do not animate layout constantly.

## Copy

Use short, direct labels. Buttons should say what happens:

- Save
- Continue
- Invite
- Cancel plan
- Delete workspace

Avoid cute empty-state copy and startup verbs. Explain consequences in plain language for destructive or billing actions.

## Accessibility

Always consider:

- Dynamic Type.
- VoiceOver order.
- Hit target size.
- Color contrast.
- Reduce Motion.
- Reduce Transparency.
- Localization length.
- Keyboard navigation on iPad and macOS.
- Error messages that are discoverable without color alone.

## Previews

When adding or changing SwiftUI views, provide useful previews when the project uses previews:

- Empty state.
- Loading or disabled state.
- Error state.
- Long localized text where relevant.
- Light and dark appearance when the app supports both.

## Testing

Run the relevant Xcode, Swift Package, or project checks when available. Report only checks that actually ran.
