# Changelog

All notable changes are recorded here. This project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Added Drip as a theme-aware ordered effect with bar-aware downward and upward travel, explicit direction overrides, screen-edge fallbacks, and a quiet reduced-motion state.
- Added solid opaque teardrops that emerge from behind the bar with matching shadows, curved reflections, live-retimed motion controls, and bounded detail at high populations.
- Added effect-level reset and a session-only Pause Preview control that stops renderer work without changing persisted enablement.

### Changed

- Replaced raw enum IDs in dropdowns with human-readable labels while retaining stable persisted values.

## [0.7.0] - 2026-08-20

### Added

- Added an opt-in, theme-aware Bokeh effect with a deterministic bounded light field, three grouped depth blurs, reduced-motion shutdown, and configurable population, size, softness, drift, twinkle, and palette roles.
- Added an opt-in Node Mesh effect with a deterministic 30 Hz bounded simulation, eight retained declarative ShapePath/PathMultiline connection buckets, configurable node and line treatment, reduced-motion static output, and shared-cursor attraction or repulsion across arbitrary output origins.
- Added isolated Node Mesh renderer-selection, pixel-equivalence, visual, settings, multi-output, lifecycle, and one-/three-output performance coverage.
- Added selectable rain and snow precipitation styles behind the existing `rainfall` effect, including bounded shared-clock snowfall, flake size/flutter/detail controls, conditional settings metadata, and static reduced-motion rendering.
- Added isolated rain extraction-parity, precipitation visual, negative-origin multi-output, fullscreen, lifecycle, and one-/three-output performance coverage.

### Changed

- Relabeled the compatible persisted `dropCount` setting as **Precipitation Count** while retaining its on-disk key and existing rain defaults.

### Fixed

- Fixed Node Mesh connections rendering no pixels by replacing post-completion dynamic ShapePath parenting with declarative render-lifecycle paths.
- Reset stalled-frame backlog after one fixed simulation step, preventing temporary callback-cadence catch-up.
- Preserved the Node Mesh renderer object while its enabled setting toggles inside an active stack, with zero simulation work while disabled.
- Fixed settings sliders changing values during mouse-wheel or touchpad scrolling by forwarding wheel input to the containing settings list and requiring a left-button drag to change values.
- Kept the bar tooltip fixed at **Desktop Ambience** instead of appending the selected custom icon name.

## [0.6.0] - 2026-08-20

### Added

- Added a theme-aware Tactical Grid effect with pointer parallax, guide lines, and four targeting-reticle styles.

### Fixed

- Tactical Grid now receives the shared cursor tracker so pointer guides, reticles, and parallax render in the live panel.
- Mouse Influence now keeps a positional repulsion field around the pointer after the sampled movement impulse decays.

## [0.5.0] - 2026-08-19

### Added

- Added an isolated Phase 7 per-effect performance matrix for one and three outputs, including repeatable targeted scenarios and previous-release worktree comparisons.
- Added runtime cursor-tracker health and launch-count reporting.

### Changed

- Consolidated Dust Motes cursor sampling into one panel-owned service instead of one polling subprocess per output.
- Suspended cursor sampling when Dust Motes is inactive, reduced motion is enabled, or every ambience output is unable to paint.
- Delayed renderer animation startup until the host geometry is stable so first loops use the full output dimensions.
- Seeded Rainfall drops across their complete travel path on startup instead of cascading from partial first cycles.
- Initialized Aurora Drift secondary glows at their animated opacity floor and removed staggered startup pauses so every ribbon begins smoothly together.
- Reworked God Rays around a persistent motion clock so activation, speed changes, and ray-count changes no longer restart or destroy individual animated layers.
- Refined active-stack selection and hover styling into one Omarchy-native semantic surface without nested borders.

## [0.4.0] - 2026-08-19

### Added

- Plugin version in the settings header.
- Ko-fi support link in the settings window.
- Documented development, versioning, validation, and release process.
- Automated contract checks for pull requests and release validation.

### Changed

- Rewrote every setting description to state its purpose directly.
- Pinned the configurable bar-icon picker to the sidebar footer.

### Fixed

- Bar-icon choices now update live and use Omarchy's inline widget setting format.
- Toggle descriptions no longer extend beneath their switches.

## [0.3.0] - 2026-08-19

### Added

- Configurable bar launcher with eight icon choices.
- Optional marker-owned Omarchy menu entry.

## [0.2.0] - 2026-08-19

### Added

- Bar and Omarchy menu launchers for the persistent settings window.

## [0.1.0] - 2026-08-19

### Added

- Standalone persistent ambience plugin.
- Eight ordered effects and a dedicated vignette.
- Central settings and theme services.
- Per-output surfaces, fullscreen suppression, and settings UI.
- Install, update, disable, uninstall, and cleanup documentation.
