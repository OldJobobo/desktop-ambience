# Bokeh Implementation Plan

Status: implemented on `feat/bokeh`; the effect remains opt-in and is not added to existing active stacks. Live release evidence remains a release gate.

## Goal

Add `bokeh` as the tenth ordered ambience effect after VHS on the current-main branch. Drip remains separate future work and is not a dependency of this implementation. Bokeh should render a restrained field of softly blurred, theme-aware light discs at several apparent depths, with configurable population, size, softness, drift, speed, and palette roles.

The effect must use the existing stack, settings, theme, presentation, persistence, geometry-settle, fullscreen, and multi-output contracts. It must not create a settings reader, theme watcher, cursor sampler, process, file service, window, or input surface.

## Visual and motion contract

- Render a bounded population of circular light sources distributed deterministically across the full output.
- Split lights across three fixed depth bands. Far lights are smaller, dimmer, softer, and slower; near lights are larger, brighter, and move farther.
- Seed each light's position, size, opacity, depth, phase, and route so enabling Bokeh does not produce synchronized motion or a visibly repeated grid.
- Move lights along long, slow two-axis paths. Wrap or reset them beyond an overscan margin so no light visibly pops at an output edge.
- Add restrained opacity breathing, controlled by `twinkleAmount`; avoid fast blinking.
- Derive each light from one of two selectable theme palette roles. Alternate and blend the roles with seeded variation rather than assigning random arbitrary colors.
- Update colors live when the active theme or either selected role changes. Existing delegates must not be recreated solely for a theme change.
- Multiply all visual opacity by normalized per-effect intensity and global opacity.
- In reduced-motion mode, render the seeded field in static positions with no drift or autonomous opacity animation.
- Stop every animation when the effect is hidden, disabled, fully transparent, removed from the stack, fullscreen-suppressed, or unable to paint.

## Blur and rendering contract

Use ordinary QML items plus `MultiEffect`, which is already used by Aurora Drift, Cinematic Light, CRT, and God Rays.

- Group lights into at most three depth-layer items and apply one blur effect per depth layer; do not attach a separate `MultiEffect` to every light.
- Keep one bounded delegate per configured light and avoid `Canvas`, particles, shaders authored by the plugin, frame-by-frame JavaScript, or unbounded transient objects.
- Render each source disc with a soft core and faint highlight before the shared layer blur.
- Derive blur radius and source padding from `blurSoftness` and the depth band. Clamp overscan so maximum blur and drift cannot clip at the output edge.
- Verify the grouped blur on the installed Qt/Quickshell version before relying on layer caching or private effect properties.
- If three live blur layers fail the performance budget, retain depth variation but collapse to one shared blurred source layer before reducing the effect's visual population.

## Proposed settings schema

Add this definition to `services/EffectRegistry.js`:

| Field | Type and proposed bounds | Purpose |
| --- | --- | --- |
| `enabled` | bool, default `true` | Standard ordered-effect enablement. |
| `intensity` | real `0..1`, default `0.52` | Overall Bokeh visibility. |
| `speed` | real `0.15..4`, default `0.65` | Common multiplier for drift and breathing timing. |
| `lightCount` | int `6..72`, default `28` | Number of pooled light delegates per output. |
| `lightSize` | real `20..240`, default `88` | Base disc diameter before seeded depth variation. |
| `blurSoftness` | real `0..1`, default `0.82` | Softness of the grouped depth layers. |
| `driftAmount` | real `0..1`, default `0.42` | Distance each depth band moves from its seeded origin. |
| `twinkleAmount` | real `0..1`, default `0.18` | Amount of slow opacity breathing. |
| `primaryColorRole` | enum, default `accent` | First theme role: `accent`, `foreground`, `color09` through `color14`. |
| `secondaryColorRole` | enum, default `color13` | Second role from the same allowed palette set. |

Use the shared role values `accent`, `foreground`, `color09`, `color10`, `color11`, `color12`, `color13`, and `color14`. Add concrete labels and hints for all Bokeh-specific fields. Do not reuse the Tactical Grid `colorRole` key because Bokeh intentionally exposes two roles.

Adding normalized `bokeh` defaults must not insert it into existing users' `activeEffects`. Existing documents should gain its default payload while preserving active order, unknown JSON-safe fields, and schema version.

## Implementation phases

### 1. Pin contracts with failing tests

- Extend registry and normalization tests to expect `bokeh`, defaults, palette-role fallbacks, integer rounding, and numeric bounds.
- Extend ordered-effect sets, renderer counts, stack injection, load-smoke, and settings-window expectations by one.
- Add behavior fixtures for minimum and maximum light counts, zero drift, zero twinkle, maximum blur, reduced motion, and live theme-role changes.
- Pin lazy-loading and object-identity behavior before writing the renderer.

### 2. Register settings metadata

Update `services/EffectRegistry.js` to:

- register `bokeh` with the proposed fields;
- add specific labels and hints for population, size, softness, drift, twinkle, and both palette roles;
- rely on generic defaults, normalization, known-key, and field-definition functions; and
- keep `backgroundVignette` outside the ordered list.

Verify that `services/AmbienceSettings.qml` normalizes the new payload automatically, retains forward-compatible unknown fields, and leaves existing `activeEffects` unchanged.

### 3. Build `effects/BokehEffect.qml`

Follow the injected adapter used by production effects:

- properties: `effectSettings`, `globalOpacity`, `reducedMotion`, `theme`, `runtimeEnabled`, and optional `runtimeIntensity`;
- consume normalized settings directly from `overlaySettings` without duplicating registry defaults or bounds;
- expose testable properties for effective color roles, active blur-layer count, animation-running state, overscan, and bounded delegate count;
- assign each delegate to one deterministic depth band and derive seeded geometry and timing from its index;
- use shared layer-level blur rather than one effect object per delegate;
- distribute initial animation phase so startup already fills the output; and
- preserve renderer and delegate identity across live theme, opacity, presentation, stack-order, and non-population setting changes.

Changing `lightCount` may add or remove bounded delegates. Other settings should update existing objects live.

### 4. Integrate the ordered stack

Update `components/AmbienceStack.qml` to:

- include `bokeh` in `supportedEffects`;
- add its component and lazy loader;
- inject theme, global opacity, reduced motion, and runtime enablement;
- include the loader in `activeProductionEffectCount` and `productionEffectObject()`; and
- retain front-to-back z calculation and the geometry-settle gate.

Do not load the renderer unless Bokeh is both in the active stack and enabled. Bokeh needs no cursor tracking or new panel-owned service.

### 5. Complete settings and documentation integration

Because `SettingsWindow.qml` is registry-driven, verify rather than special-case its editor:

- Bokeh appears in **Add Effect**;
- bool, integer, real, and enum fields use existing generic controls;
- changes save immediately without unnecessary renderer resets; and
- reset restores registry defaults.

When implementation is complete, update `README.md`, `CHANGELOG.md`, release evidence, ordered-effect counts, and the Bokeh entry in `TODO.md`.

### 6. Verification matrix

#### Host-independent and QML behavior

- Registry defaults and normalization, including invalid role names and bounded numbers.
- Existing settings gain a default Bokeh payload without changing active order or unknown fields.
- Lazy loading, enable/disable, reordering, z-order, geometry settling, and object identity.
- Deterministic population across reloads with distributed size, opacity, route, phase, and depth.
- Zero drift produces stationary lights; zero twinkle removes opacity breathing.
- Reduced motion renders a static field and runs no autonomous animations.
- Theme and role changes recolor existing lights live.
- Maximum blur and drift remain covered by overscan with no clipped glow at output edges.
- No QML warnings, binding loops, effect-local `Process`, effect-local `FileView`, `Canvas`, or per-light `MultiEffect`.

#### Visual review

Add Bokeh to the isolated visual harness and capture:

- minimum, default, and maximum populations;
- small/sharp and large/soft treatments;
- low and high drift;
- twinkle off and on;
- two contrasting palette-role combinations;
- reduced-motion output;
- foreground and background presentation;
- a live theme switch; and
- one-output and multi-output cases, including a negative output origin.

#### Performance review

Add Bokeh to the one-output and three-output performance matrix. Record reduced-motion, default animation, maximum population, maximum size/blur, and hidden/fullscreen-suppressed cases. Compare frame cadence, CPU ticks, memory, delegate count, blur-layer count, and shutdown behavior. The effect should add no process, polling loop, per-frame JavaScript clock, or unbounded object population.

## Implemented verification coverage

- The isolated visual matrix captures every Bokeh treatment above and performs a reduced-motion Bokeh-only theme switch so changed pixels cannot be attributed to motion.
- The fullscreen/presentation harness keeps one Bokeh renderer alive while switching the real panel surface from foreground to background, and verifies fullscreen suppression without object replacement.
- The performance matrix renders Bokeh on one and three temporary outputs positioned at negative origins and records output geometry, delegate count, blur-layer count, visibility, and animation shutdown.
- Manual release review is still required for side-by-side compositor screenshots of foreground and background Bokeh over representative application windows, plus physical mixed-output layouts. The automated harnesses prove those lifecycle and geometry contracts but do not replace subjective visual sign-off.

## Definition of done

- `bokeh` is the tenth normalized, reorderable, lazily loaded production effect and is not enabled in existing active stacks by default.
- The output shows a stable, softly layered field rather than synchronized discs or clipped glow.
- Population, size, softness, drift, speed, twinkle, and both theme roles update predictably.
- Theme, presentation, reduced motion, fullscreen suppression, geometry, and stack order apply live.
- Blur work is grouped into a bounded number of layers and passes the one-output and three-output performance matrix.
- Static, behavior, visual, multi-output, and performance checks pass through the repository's existing scripts.
