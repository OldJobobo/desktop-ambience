# Drip Implementation Plan

Status: implementation-complete and validated in the repository working tree. The effect remains opt-in and is not added to existing active stacks. Final combined release evidence is deferred until the other animations in the next release candidate are complete.

Release target: the maintainer-requested combined animation release is `0.6.1`, an explicit exception to the usual minor-version guidance for new features. Per the repository release process, `manifest.json` remains at `0.6.0` and Drip remains under **Unreleased** until that full release candidate is assembled.

## Goal

Add `drip` as a tenth ordered ambience effect. It should form water-like droplets along the screen edge facing the active horizontal bar, let each droplet lengthen and detach, then fall away from a top bar or rise away from a bottom bar. When usable bar geometry is unavailable, it should use the corresponding top or bottom screen edge.

The effect must use the existing stack, settings, theme, presentation, persistence, geometry-settle, fullscreen, and multi-output contracts. It must not read shell configuration, inspect the bar, create a window, or own a file/process service itself.

## Visual and motion contract

- Place a bounded set of droplets at deterministic, distributed positions along the output width.
- Give every droplet a seeded size, formation delay, and travel speed so the population does not move in lockstep.
- Animate each cycle through four phases: proportional teardrop formation, restrained lengthening, detachment and travel, then an off-screen reset delay.
- For a visible top bar, straddle its inner edge so the teardrop emerges from within the bar surface before traveling downward.
- For a visible bottom bar, straddle its inner edge so the teardrop emerges from within the bar surface before traveling upward.
- Clip the bar-side portion at the inner edge so foreground presentation still makes the real bar occlude the forming droplet; only the portion emerging beyond the bar is painted.
- Treat a hidden bar, a vertical bar, an invalid bar size, or a missing shell/bar object as unavailable horizontal geometry.
- When horizontal bar geometry is unavailable, use the top screen edge for downward travel and the bottom screen edge for upward travel. `auto` defaults to the top edge and downward travel when no horizontal position can be resolved.
- Clip the renderer to its output. A droplet must complete its travel beyond the opposite edge before resetting.
- Use one solid cubic teardrop plus a matching offset teardrop shadow and restrained curved light reflection with a stable body and tapered end per bounded delegate. Keep the main and shadow paths at fixed geometry and animate transforms instead of retessellating their paths each frame. Disable the decorative shadow and reflection above 40 configured droplets so maximum-density mode stays bounded. Avoid blur, offscreen effects, `Canvas`, shaders, particles, or frame-by-frame JavaScript.
- Default to the projected bar background color at full opacity. Keep optional accent blending available, and update existing droplets live when the bar or theme changes.
- Provide an opt-in blood mode that overrides droplets with opaque oxblood red, deepens the matching shadow, and strengthens the warm reflection. Its settings-window label is a short blood-themed phrase selected without immediate repetition whenever the window opens or the toggle changes.
- Multiply formed-droplet opacity by normalized per-effect intensity and global opacity; formation itself may fade in from transparent.
- In reduced-motion mode, show a quiet row of fully formed edge teardrops but do not lengthen, detach, travel, or run autonomous animation.
- Stop all animation when the effect is hidden, disabled, fully transparent, removed from the stack, fullscreen-suppressed, or unable to paint.

## Direction and bar-geometry contract

Use a normalized bar-state projection owned by `Panel.qml`, rather than handing the renderer the full shell or bar object. The projection should contain only JSON-safe values needed by the effect:

```qml
{
  available: true,
  position: "top",
  size: 28,
  hidden: false,
  color: "#101315"
}
```

The projection is usable only when the bar exists, is visible, has `position` equal to `top` or `bottom`, and has a finite positive size smaller than the output height. Resolve the source edge as follows:

| `direction` | Usable bar state | Effective source and travel |
| --- | --- | --- |
| `auto` | top bar | `y = bar size`, downward |
| `auto` | bottom bar | `y = output height - bar size`, upward |
| `auto` | unavailable | `y = 0`, downward |
| `down` | top bar | `y = bar size`, downward |
| `down` | any other state | `y = 0`, downward |
| `up` | bottom bar | `y = output height - bar size`, upward |
| `up` | any other state | `y = output height`, upward |

This keeps explicit direction predictable: forcing `down` never starts from a bottom bar, and forcing `up` never starts from a top bar. A bar move, hide/show transition, or size change should update the source edge live and restart droplet cycles in a controlled way rather than allowing delegates to teleport mid-flight.

## Proposed settings schema

Add this definition to `services/EffectRegistry.js`:

| Field | Type and proposed bounds | Purpose |
| --- | --- | --- |
| `enabled` | bool, default `true` | Standard ordered-effect enablement. |
| `intensity` | real `0..1`, default `1` | Overall droplet visibility; formed droplets are opaque by default. |
| `speed` | real `0.15..4`, default `1` | Standard multiplier for formation and travel timing. |
| `dropletCount` | int `6..72`, default `28` | Number of pooled droplet delegates per output. |
| `dropletSize` | real `4..32`, default `12` | Base bead diameter before seeded variation. |
| `formationTime` | int `600..12000`, default `3800` | Base time in milliseconds for a bead to form and stretch. |
| `fallSpeed` | real `40..900`, default `260` | Base travel speed in pixels per second; also applies to upward travel. |
| `direction` | enum, default `auto` | Selects `auto`, `down`, or `up`. |
| `accentBlend` | real `0..1`, default `0` | Optionally blends the projected bar background color toward the theme accent. |
| `bloodMode` | bool, default `false` | Overrides the normal bar-derived treatment with cinematic blood styling. |

`speed` remains the common animation-speed control used by every ordered renderer. `formationTime / speed` determines the formation phase, while `fallSpeed * speed` determines travel duration from the actual output distance. Changes to `speed`, `formationTime`, or `fallSpeed` must retime each delegate’s current formation, stretch, or travel phase from its present value rather than waiting for its next cycle. The UI label for `fallSpeed` can remain **Fall Speed** even though it controls either travel direction.

Add specific labels and help text for `dropletCount`, `dropletSize`, `formationTime`, `fallSpeed`, `direction`, and `bloodMode`. Reuse the existing `accentBlend` metadata. The settings surface owns blood mode's randomized display phrase; the registry retains a stable fallback label and persistence key.

Adding normalized `drip` defaults must not insert it into existing users' `activeEffects`. Existing settings documents should gain the default payload while preserving active order, unknown JSON-safe fields, and schema version.

## Implementation phases

### 1. Pin contracts with failing tests

- Extend registry and normalization tests to expect `drip`, its defaults, enum fallback, integer rounding, and upper/lower bounds.
- Extend ordered-effect, renderer-count, stack injection, load-smoke, and settings-window expectations from nine to ten production effects.
- Add behavior fixtures for top, bottom, hidden, vertical, missing, and invalid bar-state projections.
- Pin explicit `down` and `up` override behavior before implementing the renderer.
- Add a lifecycle test proving bar changes restart cycles without replacing the loaded effect object.

### 2. Register settings metadata

Update `services/EffectRegistry.js` to:

- register `drip` with the proposed fields;
- add concrete labels and hints for all Drip-specific settings;
- rely on the generic defaults, normalization, known-key, and field-definition functions; and
- keep `backgroundVignette` separate from the ordered list.

Verify that `services/AmbienceSettings.qml` automatically normalizes Drip defaults, retains forward-compatible unknown fields, and leaves `activeEffects` unchanged for existing documents.

### 3. Project bar state at the panel boundary

Update `Panel.qml` to derive a narrow `barState` object from `root.shell.bar`:

- expose only `available`, `position`, `size`, `hidden`, and the serialized bar background `color`;
- avoid importing stock bar implementation files or reading `shell.json`;
- make bar position, size, visibility, bar replacement, and shell availability reactive;
- pass the same projection to every output stack; and
- include the projection in status output for diagnostics without exposing the full shell object.

The panel should not create a bar watcher or polling loop. The injected shell/bar properties are already live QML state. The effect should continue working from screen-edge fallbacks when this host integration is absent, including isolated test harnesses.

### 4. Build `effects/DripEffect.qml`

Follow the injected adapter used by existing production effects:

- properties: `effectSettings`, `globalOpacity`, `reducedMotion`, `theme`, `barState`, `runtimeEnabled`, and optional `runtimeIntensity`;
- consume normalized values directly from `overlaySettings` without duplicating registry bounds or defaults;
- expose testable properties for usable bar geometry, effective direction, source edge, travel distance, effective color, and running animation state;
- use a bounded `Repeater` with deterministic seeded variation for x position, size, opacity, delay, and speed;
- compute travel duration from output height, source edge, seeded speed, `fallSpeed`, and the standard speed multiplier;
- distribute seeded startup delays so enabling Drip does not make the population form and detach in lockstep;
- use direction-aware transforms or endpoints so the same delegate supports upward and downward travel;
- show static mature beads in reduced-motion mode; and
- preserve renderer identity across live setting, theme, presentation, stack-order, and bar-state changes.

Use a controlled generation/restart mechanism when direction, resolved source edge, or output height changes. Existing delegates may restart, but the loader and effect object must remain stable.

### 5. Integrate the ordered stack

Update `components/AmbienceStack.qml` to:

- include `drip` in `supportedEffects`;
- add its component and lazy loader;
- inject the shared theme and projected bar state;
- include its loader in `activeProductionEffectCount` and `productionEffectObject()`; and
- retain the existing front-to-back z calculation and geometry-settle gate.

Do not load the renderer unless Drip is both in the active stack and enabled. Drip does not require cursor tracking, a process, or a new runtime service.

### 6. Complete settings and documentation integration

Keep Drip's controls registry-driven, with one deliberate presentation-only exception for the blood-mode easter egg:

- Drip appears in **Add Effect**;
- bool, integer, real, and enum fields use the existing generic editors;
- blood mode retains a stable persisted key while its title rotates without immediate repetition on window open and toggle;
- changes save immediately without recreating the effect unnecessarily; and
- reset restores registry defaults.

When implementation is complete, update `README.md` effect count/list, `CHANGELOG.md`, release evidence, and the Drip entry in `TODO.md`.

### 7. Verification matrix

#### Host-independent and QML behavior

- Registry defaults and normalization, including invalid direction and bounded numeric fields.
- Old settings documents gain a default `drip` payload but preserve active order and unknown fields.
- Lazy loading, enable/disable, reordering, z-order, geometry settling, and object identity.
- Correct source edge and direction for top, bottom, hidden, vertical, missing, and malformed bar state.
- Explicit `down` and `up` settings override incompatible bar positions using the corresponding screen-edge fallback.
- Bar move, hide/show, and size changes restart cycles cleanly without stale bindings or mid-flight teleportation.
- Formation and travel timing react independently to `formationTime`, `fallSpeed`, and the common `speed` multiplier.
- Reduced motion renders static teardrops and runs no autonomous animation.
- Theme, accent blend, intensity, global opacity, and droplet population update live.
- No QML warnings, binding loops, effect-local `Process`, effect-local `FileView`, or `Canvas`.

#### Visual review

Add Drip to the isolated visual harness and capture:

- top-bar downward and bottom-bar upward cases;
- `auto`, forced `down`, and forced `up` direction;
- early formation, stretched pre-detachment, and detached travel phases;
- minimum and maximum droplet size/count combinations;
- reduced-motion output;
- foreground and background presentation;
- theme switch and accent blend extremes; and
- at least two outputs, including one with a negative global origin.

#### Performance review

Add Drip to the one-output and three-output performance matrix. Record idle/reduced-motion and active animation cases at default and maximum droplet count. Compare frame cadence, CPU ticks, memory, loaded delegate count, and animation shutdown while hidden or fullscreen-suppressed. Drip should add no processes, polling, per-frame JavaScript clock, or unbounded object population.

## Definition of done

- `drip` is a normalized, reorderable, lazily loaded tenth production effect and is not enabled in existing active stacks by default.
- Droplets form, stretch, detach, and travel with stable seeded variation instead of synchronized cycles.
- Top and bottom horizontal bar geometry resolve correctly; hidden, vertical, missing, and invalid bar states fall back predictably to screen edges.
- Direction, theme, settings, presentation, reduced motion, fullscreen suppression, output geometry, and stack-order changes apply live.
- The renderer owns no shell configuration, process, file watcher, cursor sampler, window, or unbounded animation source.
- Static, behavior, visual, multi-output, and performance checks pass through the repository's existing check scripts.
