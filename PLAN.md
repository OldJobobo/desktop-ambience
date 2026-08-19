# Desktop Ambience Standalone Plugin Extraction

Status: approved for execution; persistent panel root, foreground mode, and dedicated vignette are in 1.0 scope

## Goal

Extract Lacuna's ordered desktop animation stack into one self-contained plugin
that installs and runs on the stock Omarchy shell without `lacuna.state`,
`lacuna.menu`, `lacuna.bar`, or any other Lacuna plugin.

This is a direct code extraction, not a visual reimplementation. Copy the
existing owned renderer, state normalization, and Animations settings code,
then replace only the Lacuna-specific host boundaries required to run it as a
standalone plugin. Do not redraw, reinterpret, approximate, or independently
recreate the effects.

The extraction must preserve the current effects and their settings before any
rendering or performance rewrite. A stock-Omarchy user should be able to install
one plugin, enable it, open its settings surface, select and reorder effects,
and remove it without leaving plugin-owned state behind.

## Extraction Method

Use the existing code as the implementation:

- copy `lacuna.ambience-host/` wholesale as the renderer baseline;
- extract the `backgroundEffects` normalization and persistence behavior from
  `lacuna.state/Service.qml` into the plugin-local settings owner;
- extract the Animations section and reorder/edit interactions from
  `lacuna.menu/settings/SettingsWindow.qml`,
  `lacuna.menu/menu/MenuWindow.qml`, and `lacuna.menu/menu/MenuRegistry.qml`;
- rename IDs, paths, namespaces, and ownership boundaries to `jobo`; and
- delete unrelated Lacuna UI and state domains after the copied behavior works.

Preserve copied effect bodies with minimal diffs. Dependency substitution should
happen around them through injected settings and theme adapters. Any effect-body
rewrite requires a separate justification and visual regression review.

## Recommended Product Boundary

Ship one plugin with a persistent **panel** entry point and a lightweight
**bar-widget** launcher in a dedicated repository, named
`jobo.desktop-ambience`. The `omarchy.*` namespace is reserved for first-party
Omarchy plugins; all plugin IDs, IPC targets, layer namespaces, and owned state
introduced here use the `jobo` namespace.

The panel entry point remains loaded and owns both:

- one selected click-through layer-shell ambience surface per output; and
- an on-demand settings window exposed through `open(payloadJson)`, `close()`,
  and `opened`.

This is preferable to declaring separate overlay and panel plugins. Omarchy's
current generic loader chooses one panel-like entry point per plugin, while a
persistent panel root can legally own the effect `PanelWindow` instances and
its settings window together. The optional bar widget is launcher-only: it
summons the panel-owned settings window and never duplicates settings, theme,
renderer, surface, or IPC ownership.

The stock plugin manifest has no contribution point for inserting a third-party
row into the Omarchy command menu. Ship an idempotent, marker-owned menu helper
instead. It adds and removes only the `desktop-ambience` row in the user's
`omarchy-menu.jsonc`, remains opt-in, and is documented in install/uninstall
steps.

The standalone repository should contain the plugin directory at its root so it
can be installed through the normal Omarchy repository-source workflow.

## Version-One Scope

Include the eight effects already composed by
`lacuna.ambience-host/AmbienceStack.qml` plus the dedicated background vignette:

1. Aurora Drift (`auroraDrift`)
2. Cinematic Light (`cinematicLight`)
3. CRT (`crt`)
4. Dust Motes (`dustMotes`)
5. Film Grain (`filmGrain`)
6. God Rays (`godRays`)
7. Rainfall (`rainfall`)
8. VHS (`trackingLines`)
9. Background Vignette (`backgroundVignette`, dedicated lifecycle)

Preserve ordered composition for the existing ambience stack: index 0 is
frontmost, invalid IDs are ignored, and duplicates collapse to the first
occurrence. Preserve the dedicated vignette's existing independent lifecycle
until its source contract is pinned; do not force it into the ordered list as
part of scaffolding.

Do not include these in version one:

- `lacuna.desktop-clock`;
- media-player background video;
- Lacuna frame-border repainting; or
- a shader/particle performance rewrite.

Foreground presentation and the dedicated vignette are required 1.0 features.
A simple per-effect vignette also remains part of effects that already own one.

## Current Extraction Baseline

The ambience-stack implementation baseline is `lacuna.ambience-host/`, not the
eight fallback plugin windows. The dedicated vignette baseline is
`lacuna.background-vignette/`; Phase 0 must pin and test both sources. Together
they give the extraction:

- one deterministic `AmbienceStack` with lazy per-effect loaders;
- one Bottom or Overlay host surface per output;
- production effect copies under `effects/`;
- fullscreen suppression through `FullscreenGuard.qml`; and
- runtime behavior coverage in
  `tests/test_qml_behavior_ambience_order.py`.

The host is not standalone today:

- `manifest.json` declares `lacuna.state` as required;
- `Overlay.qml` reads
  `~/.config/omarchy/lacuna/settings.json`;
- foreground mode obtains Lacuna frame geometry from
  `lacuna.state.foregroundFrameSource()` and repaints it through
  `ForegroundFrameBorder.qml`;
- each effect reads settings from a different legacy plugin ID in
  `shell.shellConfig.plugins`;
- each effect watches Lacuna settings independently;
- theme-aware effects independently parse Omarchy `colors.toml`; and
- the host and effect files contain duplicated settings, theme, and file-watch
  adapters.

The ambience-host rendering baseline is approximately 5,365 lines of QML;
Phase 0 must record the additional vignette baseline separately. Preserve their
visual output during extraction. Optimization is a separate project because the
archived animation-pipeline experiment documents prior visual-parity failures.

## Target Layout

```text
jobo.desktop-ambience/
├── manifest.json
├── Panel.qml
├── BarWidget.qml
├── components/
│   ├── AmbienceStack.qml
│   ├── FullscreenGuard.qml
│   └── SettingsWindow.qml
├── effects/
│   ├── AuroraDriftEffect.qml
│   ├── CinematicLightEffect.qml
│   ├── CrtEffect.qml
│   ├── DustMotesEffect.qml
│   ├── FilmGrainEffect.qml
│   ├── GodRaysEffect.qml
│   ├── RainfallEffect.qml
│   ├── VhsEffect.qml
│   └── VignetteEffect.qml
├── services/
│   ├── AmbienceSettings.qml
│   ├── EffectRegistry.js
│   └── ThemeAdapter.qml
├── assets/
└── scripts/
    └── menu-entry.sh
```

All runtime imports must remain inside the plugin directory except supported
Omarchy/Quickshell modules such as `qs.Commons`, `Quickshell.*`, and `QtQuick.*`.

## Target State Contract

Own a versioned file at:

```text
$XDG_CONFIG_HOME/omarchy/jobo/desktop-ambience/settings.json
```

Recommended initial shape:

```json
{
  "version": 1,
  "enabled": true,
  "presentation": "background",
  "opacity": 1,
  "reduceMotion": false,
  "activeEffects": ["trackingLines"],
  "effects": {
    "trackingLines": {
      "enabled": true,
      "intensity": 0.68,
      "speed": 1
    }
  }
}
```

`AmbienceSettings.qml` must be the only file owner. It should:

- normalize unknown, missing, duplicate, and out-of-range values;
- preserve unknown JSON-safe fields for forward compatibility;
- serialize writes and atomically replace the destination;
- expose requested, confirmed, failed, and retryable persistence state;
- retain the last valid state after a malformed external edit; and
- publish one normalized object to the host, effects, and settings UI.

`EffectRegistry.js` should own IDs, labels, defaults, bounds, and enum values.
It must expose the eight reorderable renderers separately from dedicated
vignette metadata. `backgroundVignette` never appears in `activeEffects` or the
ordered effects map; it owns separate `enabled` and `intensity` state. VHS uses
the source contract's canonical persisted ID, `trackingLines`; `vhs` is not a
second persisted ID. Do not keep separate defaults in the manifest, stack, and
effect implementations.

## Theme Contract

Use stock Omarchy's `qs.Commons.Color` singleton for background, foreground,
accent, and other structural roles. Where an effect needs extended Base16 hues
that `Color` does not expose, one `ThemeAdapter.qml` may read
`$XDG_STATE_HOME/omarchy/current/theme/colors.toml` as a supplement.

The adapter must:

- react to native `Color` changes;
- retain the last valid extended palette while the theme path is replaced;
- retry a bounded number of times after a failed read; and
- provide palette values to every effect so effect files own no `FileView`.

## Presentation And Layer Policy

### Background mode

Use `WlrLayer.Bottom`, an empty input mask, no keyboard focus, and
`ExclusionMode.Ignore`. This is the version-one default and must work without
any Lacuna geometry or services.

### Foreground mode

Foreground presentation is required in 1.0. Ship it as an explicit
"above shell UI" option using a click-through `WlrLayer.Overlay` surface.
Document that it may cover the stock bar, menus, and other Overlay UI depending
on mapping order.

Stock Omarchy does not expose Lacuna's authoritative frame-border bridge. Do
not couple the standalone plugin to Lacuna frame APIs, private map order, or
invented stock-bar exclusion geometry. If a stable public host API is identified
before release, its geometry may be adopted through a host adapter without
rewriting effect bodies.

Fullscreen applications must suppress all foreground paint on their own output
without reserving space or accepting input.

## Independence Contract

The standalone plugin starts from its own defaults and never discovers, reads,
imports, migrates, watches, writes, enables, disables, or reports on Lacuna
plugins or Lacuna settings. Its runtime and tests must contain no Lacuna IDs,
paths, services, compatibility aliases, or migration fixtures.

Users moving from another ambience implementation configure this plugin as a
fresh install. Generic documentation may warn against running multiple desktop
effect systems simultaneously, but it must not name or inspect Lacuna plugins.

## Execution Plan

### Phase 0 — Pin the extraction source

- Record the exact source commit for both `lacuna.ambience-host/` and
  `lacuna.background-vignette/`, plus the Omarchy package revision and
  Quickshell revision.
- Run the existing ambience ordering, vignette contract, and live visual tests.
- Save the passing test output and current live configuration as extraction
  evidence.
- Optionally retain screenshots as regression evidence; they are not a recipe
  for recreating the effects.

**Gate:** the owned source revision and its passing baseline are fixed.

### Phase 1 — Copy the implementation intact

- Duplicate `lacuna.ambience-host/` as `jobo.desktop-ambience/` without changing
  the original Lacuna plugin.
- Preserve `AmbienceStack.qml`, `FullscreenGuard.qml`, all eight ordered effect
  files, and the dedicated vignette renderer intact in the first copy commit so
  provenance and later diffs are obvious.
- In a second mechanical commit, rename the manifest ID, IPC target, layer
  namespaces, and object names to the `jobo` namespace.
- Remove the Lacuna-specific `ForegroundFrameBorder.qml` bridge because stock
  Omarchy has no matching public frame API; host foreground and vignette paint
  on the selected full-output surface instead of newly invented frame geometry.
- Keep rendering code byte-for-byte except where a renamed injected property or
  full-output geometry adapter is required to sever a Lacuna dependency.

Phase 1 deliberately retains the source host's two per-output window trees—one
Bottom and one Overlay—with only the selected tree mapped. This is an interim
provenance contract, not the final surface architecture. Phase 3 replaces it
with one dynamically selected surface per output; Phase 1 tests that count both
windows must be revised in that commit rather than treated as permanent API.

**Gate:** the copied renderer still passes the existing ordering and lazy-load
behavior tests before settings or UI extraction begins.

### Phase 2 — Extract and retarget settings ownership

- Copy only the existing `backgroundEffects` defaults, normalization, bounds,
  ordering, and persistence behavior from `lacuna.state/Service.qml` into
  `AmbienceSettings.qml`.
- Copy the existing effect defaults and schema metadata into
  `EffectRegistry.js`, preserving values and labels.
- Retarget the copied logic to the plugin's own settings file; do not read or
  import Lacuna state.
- Add `ThemeAdapter.qml` by lifting the existing `Color` and extended-palette
  behavior out of the copied effects, then inject the resolved palette.
- Pass normalized per-effect settings, opacity, and reduced-motion values into
  the copied effects as properties.
- Delete effect-local Lacuna settings readers, old plugin-ID scans, palette
  parsers, and duplicate `FileView` instances only after equivalent injected
  values are covered by tests.
- Keep animation timers, repeaters, scene items, and visual math unchanged.

**Gate:** a structural test bans `/omarchy/lacuna`, `lacuna.`, and effect-local
`FileView` references from the entire standalone repository.

### Phase 3 — Build the persistent panel root

- Replace the Phase 1 dual-window baseline with one dynamically selected
  ambience surface per output and add one on-demand settings window.
- Preserve lazy effect loading and sibling-z ordering.
- Keep all surfaces input-transparent and non-exclusive.
- Add required per-output fullscreen suppression for foreground mode.
- Add an IPC `status()` method reporting mode, active order, loaded effect
  count, mapped surfaces, and persistence health.

**Gate:** enabling, disabling, reordering, monitor hotplug, shell restart, and
fullscreen transitions do not duplicate surfaces or leave stale input regions.

### Phase 4 — Extract the Animations settings UX

- Copy the existing Animations section, active-effect list, reorder behavior,
  per-effect rows, and save-state feedback from the Lacuna settings sources.
- Remove unrelated Appearance, Layout, Media, Preferred Apps, Tools, and About
  sections from the copied window.
- Retarget copied actions to `AmbienceSettings.qml` and the central registry.
- Preserve global enable, opacity, reduced-motion, presentation, add/remove,
  move-up/down, per-effect editing, save retry, and reset behavior.
- Restyle or rename only after the standalone copy is behaviorally complete.
- Ensure reset affects only this plugin's owned file.

**Gate:** every control round-trips through the versioned file, survives shell
restart, and does not modify `shell.json`, Lacuna settings, themes, Hyprland
configuration, or unrelated plugin state.

### Phase 5 — Extract to the standalone repository

- Move the proven candidate directory and its focused tests into a new Git
  repository with the plugin directory at repository root.
- Add README installation, upgrade, troubleshooting, and uninstall
  instructions.
- Add a check script for JSON, manifest validation, QML lint/load, unit tests,
  and forbidden runtime dependencies.
- Add a launcher-only bar widget that summons the persistent settings window;
  its icon is selected from the plugin settings view and stored as inline bar
  widget state owned by Omarchy's shell configuration.
- Add an idempotent opt-in Omarchy menu helper with exact marker-owned removal.
- Install from the repository source rather than a development symlink and
  verify `omarchy plugin validate`, `omarchy plugin enable`, bar placement, and
  both launcher paths.

**Gate:** a clean stock Omarchy profile can install, configure, update, and
remove the plugin without this Lacuna repository present.

### Phase 6 — Live validation and release

Test at minimum:

- one and multiple monitors;
- mixed resolution, scale, orientation, and refresh rate;
- every ordered effect alone, the dedicated vignette alone, and a three-effect
  stack with the vignette enabled;
- reorder without effect object recreation;
- theme switch while effects are active;
- malformed settings and interrupted-save recovery;
- monitor add/remove;
- normal, fake-fullscreen, and real fullscreen windows;
- shell restart and plugin rescan; and
- coexistence behavior when another desktop-effect system is running.

Capture CPU and frame-pacing measurements as release evidence, but do not block
the extraction on improving the inherited renderer unless it regresses from the
frozen baseline.

**Gate:** visual references match, no Lacuna runtime dependency remains, the
clean-profile install passes, and all documented acceptance criteria are met.

## Required Automated Coverage

- Manifest validation and safe relative entry points.
- QML load smoke for the panel root and every effect.
- Pure normalization tests for settings versions, bounds, unknown fields,
  duplicate order entries, and malformed input.
- Persistence behavior tests for latest-write-wins, confirmation, retry, and
  last-valid-state retention.
- Runtime ordering test retaining the current pixel/z assertion.
- Lazy-loading test: disabled or unselected effects instantiate no renderer.
- Fullscreen-guard behavior by output.
- Theme-adapter fallback/retry behavior.
- Forbidden-dependency scan for Lacuna imports, paths, services, IDs, and
  repository-relative runtime imports.
- Opt-in live visual and performance tests that restore all changed state.

## Acceptance Criteria

The extraction is complete when:

- one Omarchy plugin ID owns all eight ordered effects, the dedicated vignette,
  their settings, and both launcher paths;
- stock Omarchy is the only runtime dependency;
- installation does not require Lacuna files, services, menu, bar, or scripts;
- one selected host surface exists per output, not one surface per effect;
- effect order is deterministic and changes without recreating unchanged
  effect objects;
- settings persist atomically and failures are visible and retryable;
- theme changes propagate through one shared adapter;
- explicit foreground presentation works, remains click-through, documents its
  shell-chrome overlap behavior, and suppresses paint per output for real
  fullscreen applications;
- the dedicated vignette preserves its source behavior in both background and
  foreground presentation;
- current effect screenshots remain visually equivalent; and
- the bar icon and optional Omarchy menu row both open the same persistent
  settings window without duplicating runtime ownership;
- all documented bar-icon choices are selectable in plugin settings, persist in
  inline widget state, update live on every bar surface, and default to the
  Animation glyph; and
- install, update, disable, and uninstall—including exact menu-row and owned
  state cleanup—are documented and tested on a clean base Omarchy profile.

## Resolved Decisions

1. The persistent panel-root architecture is approved.
2. Version 1.0 includes background and explicit click-through foreground
   presentation.
3. Version 1.0 includes the dedicated background vignette.

## Follow-On Work

After direct extraction and regression validation are complete, open a separate
performance plan. That work may replace item-heavy repeaters, short timers, and
cursor subprocess polling with shaders, particles, frame-aligned animation, and
shared input services. It must not be mixed into the extraction because the archived
`lacuna-animation-pipeline-plan.md` records why architecture and renderer
changes made together were difficult to validate and were reverted.
