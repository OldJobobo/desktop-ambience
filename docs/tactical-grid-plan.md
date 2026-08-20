# Tactical Grid Implementation Plan

Status: implemented in the repository working tree; the effect remains opt-in and is not added to existing active stacks.

## Goal

Add `tacticalGrid` as a ninth ordered ambience effect. It should render a theme-aware screen grid, optionally shift the grid with subtle pointer-driven parallax, draw horizontal and vertical guides through the pointer, and place a configurable targeting reticle at their intersection.

The effect must use the existing stack, settings, theme, cursor, presentation, persistence, and multi-output contracts. It must not create its own settings reader, theme watcher, cursor subprocess, window, or input surface.

## Visual and interaction contract

- Render a tiled vertical and horizontal grid across the full output.
- Keep enough overflow lines around every edge that parallax never exposes an empty strip.
- Apply parallax only when enabled, a valid cursor sample is inside the current output, and reduced motion is off.
- Derive parallax from the pointer's normalized displacement from the output center. Clamp the translation to less than one grid cell so the effect remains subtle and bounded.
- Show pointer guides and the reticle only on the output containing the pointer. Hide them when the sample is unavailable or outside that output.
- Draw guide lines through the pointer's output-local coordinates.
- Initially support four reticle styles: `crosshair`, `brackets`, `ring`, and `diamond`.
- Use lightweight QML primitives and bounded repeaters for grid lines and reticle parts; avoid one object per grid intersection.
- Resolve colors through `ThemeAdapter.colorFor()`. Theme changes must update the effect live.
- Multiply all visual opacity by the normalized per-effect intensity and global opacity.
- In reduced-motion mode, keep a static grid and allow direct pointer guides, but disable parallax easing and reticle pulsing.
- Stop all autonomous animation and pointer work when the effect is hidden, disabled, fully transparent, removed from the stack, or unable to paint.

## Proposed settings schema

Add this definition to `services/EffectRegistry.js`:

| Field | Type and proposed bounds | Purpose |
| --- | --- | --- |
| `enabled` | bool, default `true` | Standard ordered-effect enablement. |
| `intensity` | real `0..1`, default `0.55` | Overall effect visibility. |
| `speed` | real `0.15..4`, default `1` | Reticle pulse and parallax easing speed. |
| `gridSpacing` | int `24..160`, default `64` | Distance between grid lines in pixels. |
| `gridLineWidth` | real `0.5..4`, default `1` | Grid stroke width. |
| `gridOpacity` | real `0..1`, default `0.28` | Grid visibility relative to intensity. |
| `guideOpacity` | real `0..1`, default `0.58` | Pointer guide visibility relative to intensity. |
| `parallaxEnabled` | bool, default `true` | Enables pointer-driven grid movement. |
| `mouseInfluence` | real `0..1`, default `0.22` | Controls maximum parallax displacement. |
| `mouseGuides` | bool, default `true` | Shows the crossing pointer guide lines. |
| `reticleStyle` | enum, default `brackets` | Selects `crosshair`, `brackets`, `ring`, or `diamond`. |
| `reticleSize` | int `12..120`, default `42` | Reticle diameter or bounding size. |
| `reticlePulse` | bool, default `true` | Enables a restrained opacity/scale pulse. |
| `colorRole` | enum, default `accent` | Selects `accent`, `foreground`, `color11`, `color12`, `color13`, or `color14`. |

Add a specific label and help text for every field so the registry-driven settings window can render the complete editor without Tactical Grid-specific UI code.

Adding defaults for `tacticalGrid` does not require inserting it into existing users' `activeEffects`. Existing settings documents should normalize with the new default payload while retaining their current active stack and schema version.

## Implementation phases

### 1. Pin contracts with failing tests

- Extend registry and normalization tests to expect `tacticalGrid`, its defaults, enum fallbacks, integer rounding, and upper/lower bounds.
- Extend stack contract tests to require a Tactical Grid loader, injected settings, theme, target screen, cursor tracker, global opacity, reduced motion, and runtime enablement.
- Update hard-coded ordered-effect sets and renderer counts from eight to nine only where they represent production effects.
- Add behavior-test fixtures for negative output origins and multi-output cursor placement before writing renderer logic.

### 2. Register the effect and settings metadata

Update `services/EffectRegistry.js` to:

- register `tacticalGrid` with the proposed fields;
- add labels and concrete hints for all new settings;
- rely on the existing generic default, normalization, known-key, and field-definition functions; and
- keep `backgroundVignette` separate from the ordered list.

Verify that `services/AmbienceSettings.qml` automatically includes normalized Tactical Grid defaults, preserves unknown JSON-safe fields, and does not add the effect to `activeEffects`.

### 3. Build `effects/TacticalGridEffect.qml`

Follow the injected effect adapter used by the current production effects:

- properties: `effectSettings`, `globalOpacity`, `reducedMotion`, `theme`, `targetScreen`, `cursorTracker`, `runtimeEnabled`, and optional `runtimeIntensity`;
- normalized values are consumed directly from `overlaySettings` without duplicating registry defaults or bounds;
- convert global cursor coordinates to output-local coordinates using `targetScreen.x` and `targetScreen.y`;
- expose small testable helpers/properties for cursor-inside-output, local pointer position, parallax offsets, selected reticle style, and effective color;
- render grid lines with two repeaters sized from the current output dimensions and `gridSpacing`, including overflow lines for translated edges;
- render pointer guides as two rectangles and reticles through style-specific components selected by a loader;
- use a bounded animation clock only for reticle pulse; no frame timer should run when pulse animation is disabled or reduced motion is enabled; and
- preserve object identity across live setting, theme, stack-order, and pointer changes.

### 4. Integrate the ordered stack

Update `components/AmbienceStack.qml` to:

- include `tacticalGrid` in `supportedEffects`;
- add its component and lazy loader;
- inject the shared theme, target screen, and cursor tracker;
- include its loader in `activeProductionEffectCount` and `productionEffectObject()`; and
- retain the existing front-to-back z calculation and geometry-settle gate.

Do not load the renderer unless Tactical Grid is both in the active stack and enabled.

### 5. Share pointer sampling safely

Refactor the request logic in `Panel.qml` from Dust Motes-only activation to a shared cursor requirement:

- keep the existing Dust Motes request conditions;
- add a Tactical Grid request when it is selected, enabled, visible, able to paint, and either parallax, guides, or the reticle needs pointer coordinates;
- activate the single panel-owned `CursorTracker` when either effect requests it;
- never create one cursor process per output; and
- retain cursor health in the existing status payload.

Before settling the polling cadence, profile the current `hyprctl cursorpos -j` subprocess approach. Prefer a modest shared cadence plus visual interpolation over aggressive polling. If smoothing is required, add separate display coordinates to `CursorTracker` so velocity calculations continue to use raw samples and Dust Motes behavior does not regress.

### 6. Complete settings and documentation integration

Because `SettingsWindow.qml` is registry-driven, verify rather than special-case its controls:

- Tactical Grid appears in **Add Effect**;
- every bool, enum, integer, and real field uses the existing generic editor;
- changes save immediately and do not reset animation state unnecessarily; and
- reset restores the registry defaults.

Update `README.md` effect count/list, `CHANGELOG.md`, and the Tactical Grid entry in `TODO.md` when implementation is complete.

### 7. Verification matrix

#### Host-independent and QML behavior

- Registry defaults and normalization, including invalid enum and bound handling.
- Old settings documents gain a default `tacticalGrid` payload but preserve active order and unknown fields.
- Lazy loading, enable/disable, reordering, z-order, geometry settling, and object identity.
- Global-to-local cursor conversion on outputs with positive and negative origins.
- Guides and reticle appear only on the pointer's output and hide for invalid samples.
- Parallax remains bounded and never reveals uncovered edges.
- `mouseInfluence: 0`, disabled parallax, and reduced motion all produce a stationary grid.
- Live reticle style, size, palette role, theme, opacity, and spacing changes update without recreating the effect.
- Cursor tracking starts when required and stops when neither Tactical Grid nor Dust Motes needs it.
- No QML warnings, binding loops, effect-local `Process`, or effect-local `FileView`.

#### Visual review

Add Tactical Grid to the isolated visual harness and capture:

- each reticle style;
- pointer at center and near output edges;
- parallax on and off;
- reduced-motion output;
- foreground and background presentation;
- theme switch; and
- at least two outputs with the pointer present on only one.

#### Performance review

Add Tactical Grid to the one-output and three-output performance matrix. Record idle and active-pointer cases. Compare frame cadence, CPU ticks, memory, cursor-process launch count, grid population at minimum and maximum spacing, and reticle pulse on/off. The effect should not introduce per-intersection objects or per-output cursor processes.

## Definition of done

- `tacticalGrid` is a normalized, reorderable, lazily loaded production effect and is not enabled in existing active stacks by default.
- The grid, pointer guides, and all four reticle styles work on outputs with arbitrary origins.
- Theme, settings, presentation, reduced motion, fullscreen suppression, and stack-order changes apply live.
- One shared cursor sampler serves Dust Motes and Tactical Grid and goes idle when unused.
- Static, behavior, visual, multi-output, and performance checks pass through the repository's existing check scripts.
- Documentation and release notes describe the ninth ordered effect and its controls.
