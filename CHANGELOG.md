# Changelog

All notable changes are recorded here. This project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.5.0] - 2026-08-19

### Added

- Added an isolated Phase 7 per-effect performance matrix for one and three outputs, including repeatable targeted scenarios and previous-release worktree comparisons.
- Added runtime cursor-tracker health and launch-count reporting.

### Changed

- Consolidated Dust Motes cursor sampling into one panel-owned service instead of one polling subprocess per output.
- Suspended cursor sampling when Dust Motes is inactive, reduced motion is enabled, or every ambience output is unable to paint.
- Delayed renderer animation startup until the host geometry is stable so first loops use the full output dimensions.
- Seeded Rainfall drops across their complete travel path on startup instead of cascading from partial first cycles.
- Initialized Aurora Drift secondary glows at their animated opacity floor so startup no longer briefly over-stacks fully opaque extras.

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
