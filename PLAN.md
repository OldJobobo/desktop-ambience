# Desktop Ambience Standalone Plugin Extraction

Status: proposed; architecture ready, foreground policy requires approval

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

Ship one persistent **panel-kind plugin** in a dedicated repository, tentatively
named `jobo.desktop-ambience`. The `omarchy.*` namespace is reserved for
first-party Omarchy plugins; all plugin IDs, IPC targets, layer namespaces, and
owned state introduced here use the `jobo` namespace.

The panel entry point remains loaded and owns both:

- one selected click-through layer-shell ambience surface per output; and
- an on-demand settings window exposed through `open(payloadJson)`, `close()`,
  and `opened`.

This is preferable to declaring separate overlay and panel plugins. Omarchy's
current generic loader chooses one panel-like entry point per plugin, while a
persistent panel root can legally own the effect `PanelWindow` instances and
its settings window together. It also avoids requiring a configuration widget
in the bar.

The standalone repository should contain the plugin directory at its root so it
can be installed through the normal Omarchy repository-source workflow.

## Version-One Scope

Include the eight effects already composed by
`lacuna.ambience-host/AmbienceStack.qml`:

1. Aurora Drift (`auroraDrift`)
2. Cinematic Light (`cinematicLight`)
3. CRT (`crt`)
4. Dust Motes (`dustMotes`)
5. Film Grain (`filmGrain`)
6. God Rays (`godRays`)
7. Rainfall (`rainfall`)
8. VHS (`vhs`)

Preserve ordered composition: index 0 is frontmost, invalid IDs are ignored,
and duplicates collapse to the first occurrence.

Do not include these in version one:

- `lacuna.background-vignette`, which has Lacuna frame-content geometry and a
  separate non-animation lifecycle;
- `lacuna.desktop-clock`;
- media-player background video;
- Lacuna frame-border repainting; or
- a shader/particle performance rewrite.

A simple per-effect vignette remains part of effects that already own one.

## Current Extraction Baseline

The implementation baseline is `lacuna.ambience-host/`, not the eight fallback
plugin windows. It already gives the extraction:

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

The rendering baseline is approximately 5,365 lines of QML. Preserve its visual
output during extraction; optimization is a separate project because the
archived animation-pipeline experiment documents prior visual-parity failures.

## Target Layout

```text
jobo.desktop-ambience/
├── manifest.json
├── Panel.qml
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
│   └── VhsEffect.qml
├── services/
│   ├── AmbienceSettings.qml
│   ├── EffectRegistry.js
│   └── ThemeAdapter.qml
└── assets/
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
  "activeEffects": ["vhs"],
  "effects": {
    "vhs": {
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
Do not keep separate defaults in the manifest, stack, and effect
implementations.

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

### Foreground mode decision

Stock Omarchy does not expose Lacuna's authoritative frame-border bridge.
An Overlay ambience surface can also paint above the stock bar, menus, and
other Overlay UI depending on mapping order.

Choose one policy before implementation:

1. **Recommended for 1.0:** ship background mode only and hold foreground mode
   behind an experimental setting until bar/menu behavior is accepted live.
2. Ship foreground mode as an explicit "above shell UI" option, document that
   it is click-through but may cover shell chrome, and suppress it on fullscreen
   outputs.
3. Add stock-bar exclusion geometry only after identifying a stable public host
   API. Do not couple the standalone plugin to Lacuna frame APIs or private map
   order.

Regardless of the choice, fullscreen applications must suppress all foreground
paint on their own output without reserving space or accepting input.

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

- Record the exact source commit, Omarchy package revision, and Quickshell
  revision.
- Run the existing ambience ordering, contract, and live visual tests.
- Save the passing test output and current live configuration as extraction
  evidence.
- Optionally retain screenshots as regression evidence; they are not a recipe
  for recreating the effects.

**Gate:** the owned source revision and its passing baseline are fixed.

### Phase 1 — Copy the implementation intact

- Duplicate `lacuna.ambience-host/` as `jobo.desktop-ambience/` without changing
  the original Lacuna plugin.
- Preserve `AmbienceStack.qml`, `FullscreenGuard.qml`, and all eight effect files
  intact in the first copy commit so provenance and later diffs are obvious.
- In a second mechanical commit, rename the manifest ID, IPC target, layer
  namespaces, and object names to the `jobo` namespace.
- Remove `ForegroundFrameBorder.qml` only because stock Omarchy has no Lacuna
  frame bridge; do not replace it with newly invented geometry.
- Keep rendering code byte-for-byte except where a renamed injected property is
  required to sever a Lacuna dependency.

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

- Implement `Panel.qml` with one dynamically selected ambience surface per
  output and one on-demand settings window.
- Preserve lazy effect loading and sibling-z ordering.
- Keep all surfaces input-transparent and non-exclusive.
- Add per-output fullscreen suppression for any accepted foreground mode.
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
  and forbidden Lacuna dependencies.
- Install from the repository source rather than a development symlink and
  verify `omarchy plugin validate` and `omarchy plugin enable`.

**Gate:** a clean stock Omarchy profile can install, configure, update, and
remove the plugin without this Lacuna repository present.

### Phase 6 — Live validation and release

Test at minimum:

- one and multiple monitors;
- mixed resolution, scale, orientation, and refresh rate;
- every effect alone and a three-effect stack;
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

- one Omarchy plugin ID owns all eight effects and their settings;
- stock Omarchy is the only runtime dependency;
- installation does not require Lacuna files, services, menu, bar, or scripts;
- one selected host surface exists per output, not one surface per effect;
- effect order is deterministic and changes without recreating unchanged
  effect objects;
- settings persist atomically and failures are visible and retryable;
- theme changes propagate through one shared adapter;
- foreground behavior follows the approved explicit policy and real fullscreen
  suppression works per output;
- current effect screenshots remain visually equivalent; and
- install, update, disable, and uninstall are documented and tested on a clean
  base Omarchy profile.

## Decisions Needed Before Phase 1

1. Approve the persistent panel-root architecture.
2. Choose the version-one foreground policy; background-only is recommended.
3. Confirm that the dedicated background vignette remains out of version one.

## Follow-On Work

After direct extraction and regression validation are complete, open a separate
performance plan. That work may replace item-heavy repeaters, short timers, and
cursor subprocess polling with shaders, particles, frame-aligned animation, and
shared input services. It must not be mixed into the extraction because the archived
`lacuna-animation-pipeline-plan.md` records why architecture and renderer
changes made together were difficult to validate and were reverted.
