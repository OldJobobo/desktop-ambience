# Precipitation Styles Implementation Plan

Status: complete on `feat/precipitation-styles`. Production, persistence, settings, lifecycle, isolated visual, fullscreen, negative-origin multi-output, and one-/three-output performance coverage are integrated without adding another ordered effect or changing existing active stacks.

## Goal

Evolve `rainfall` into a style-aware precipitation renderer. The first production styles are `rain` and `snow`; the schema and renderer boundary should allow later variants without turning Rainfall into a collection of stale, interleaved animations.

Existing users must continue to receive the current rain treatment by default. The effect keeps the persisted ID `rainfall`, its position in `activeEffects`, its root renderer identity, and its shared intensity, speed, direction/slant, theme blending, presentation, reduced-motion, persistence, fullscreen, and multi-output behavior.

## Compatibility contract

- Add `precipitationStyle` with default `rain`. Old settings therefore normalize to their existing visual behavior without a version migration or active-stack rewrite.
- Retain existing keys: `dropCount`, `slant`, `mistAmount`, `splashAmount`, `accentBlend`, and `vignette`.
- Keep `dropCount` as the persisted population control for compatibility. Present it as **Precipitation Count** in the settings UI so it remains accurate for snow.
- Preserve current Rainfall defaults and bounds unless profiling or a failing behavior contract proves a change is necessary.
- Unknown JSON-safe keys and future style payloads must continue to survive normalization and saving.
- Switching styles may recreate the internal style delegate tree, but it must not recreate the ordered `RainfallEffect` object or disturb stack order.
- An invalid or future unsupported style falls back to `rain` through registry normalization.

## Shared and style-specific visual contract

### Shared behavior

- Every style consumes normalized `enabled`, `intensity`, `speed`, `dropCount`, `slant`, `accentBlend`, and `vignette` values.
- Seed initial particle progress across the full output so a newly enabled style does not begin with an empty lower half.
- Clip to the output and use bounded particle populations derived from `dropCount`.
- Resolve colors through the injected theme and update them live.
- Multiply all style opacity by normalized effect intensity and global opacity.
- Reduced motion must contain no autonomous animation. Each style renders a quiet static interpretation rather than silently disappearing.
- Hidden, disabled, transparent, removed, fullscreen-suppressed, or unpaintable styles must stop all timers and animations.

### Rain

- Preserve the current layered rain intent: background mist, seeded rain streaks, foreground streaks, splashes, and optional vignette.
- Preserve current `mistAmount` and `splashAmount` behavior and the distributed startup phase contract.
- Refactoring must not regress slant, full-height population, theme blending, or foreground/background presentation.

### Snow

- Render softly varied flakes rather than recolored rain streaks.
- Seed flake size, opacity, depth, fall speed, horizontal phase, and rotation so the field does not move in lockstep.
- Fall more slowly than rain and use bounded lateral flutter influenced by `slant` and `flutterAmount`.
- Use simple circles and restrained crystal variants built from lightweight QML primitives; do not attach a blur effect or animation clock to every flake.
- Use depth bands to vary size, speed, and opacity while keeping one bounded delegate per flake.
- In reduced motion, show a static distributed snowfall field with no flutter, fall, or rotation.
- Do not add accumulation simulation in the first version. It introduces persistent geometry, reset semantics, and unbounded-state risks that should be planned separately.

## Proposed settings schema

Extend the existing `rainfall` definition in `services/EffectRegistry.js`:

| Field | Type and proposed bounds | Applies to | Purpose |
| --- | --- | --- | --- |
| `enabled` | existing bool, default `true` | all | Standard enablement. |
| `intensity` | existing real `0..1`, default `0.72` | all | Overall visibility. |
| `speed` | existing real `0.15..4`, default `0.62` | all | Common motion multiplier. |
| `precipitationStyle` | enum, default `rain` | all | Selects `rain` or `snow`. |
| `dropCount` | existing int `16..320`, default `180` | all | Bounded particle population. |
| `slant` | existing real `-0.2..0.35`, default `0.08` | all | Wind direction; snow interprets it as lateral bias. |
| `accentBlend` | existing real `0..1`, default `0.42` | all | Theme-accent contribution. |
| `vignette` | existing bool, default `true` | all | Built-in edge darkening. |
| `mistAmount` | existing real `0..1`, default `0.34` | rain | Rain mist opacity. |
| `splashAmount` | existing real `0..1`, default `0.38` | rain | Rain splash population. |
| `flakeSize` | real `2..18`, default `6` | snow | Base snowflake diameter. |
| `flutterAmount` | real `0..1`, default `0.58` | snow | Lateral snow movement. |
| `flakeDetail` | enum, default `mixed` | snow | Selects `soft`, `crystal`, or `mixed`. |

### Generic conditional-field metadata

Add optional field metadata to the registry rather than hard-coding Rainfall checks in `SettingsWindow.qml`:

```js
visibleWhen: { field: "precipitationStyle", values: ["snow"] }
```

Use it for `flakeSize`, `flutterAmount`, and `flakeDetail`; use the corresponding `rain` condition for `mistAmount` and `splashAmount`. Shared fields have no condition.

`fieldDefinitions()` should preserve this JSON-safe metadata. The registry-driven settings editor should evaluate it against the selected effect's current normalized settings. Hidden controls retain their saved normalized values so switching styles restores the user's last rain or snow tuning. The condition system should remain generic enough for future effects and support only same-effect equality against a bounded enum in this first implementation.

## Renderer architecture

Keep `effects/RainfallEffect.qml` as the ordered adapter and split style rendering behind a loader:

- `RainfallEffect.qml` owns the standard injected adapter, normalization consumption, effective intensity, runtime lifecycle, theme-derived shared colors, payload `open()`/`close()`, and style selection.
- Extract the current rain visuals into `effects/RainPrecipitationStyle.qml` without changing their visual math during the first refactor.
- Add `effects/SnowPrecipitationStyle.qml` for snow.
- Inject a narrow set of already-normalized values into each style component; internal style components must not read settings or registry defaults independently.
- The internal loader selects one known component from normalized `precipitationStyle`. Do not construct a QML path from persisted input.
- A style change may replace only the loader's child. The root `RainfallEffect` remains stable, and the old component's animations must stop before destruction.
- Expose root test properties for selected style, loaded style object, style generation, effective colors, and whether autonomous motion is running.

Before extraction, pin the current rain output and startup behavior. Make the extraction a behavior-preserving phase, then add snow in a separate phase so regressions can be attributed correctly.

## Implementation phases

### 1. Pin current Rainfall behavior — complete

- Static and QML behavior coverage now pins current rain defaults, slant, mist, splash, bounded population, distributed full-height startup, reduced-motion static behavior, animation shutdown, and root identity across a future style payload and stack reorder.
- The isolated baseline harness records deterministic static and animated 1920×1080 images at a negative output origin in `docs/release/evidence/rainfall-baseline/`, with exact hashes pinned by `tests/baselines/rainfall-pre-extraction.json`.
- Three 3-second samples at one and three outputs are recorded in `docs/performance/evidence/rainfall-baseline.json`. Median CPU was 32.77% for one output and 45.02% for three; these are machine-local directional values rather than portable budgets.
- On the installed Qt 6.11.1 runtime, the current inner visual item's `enabled: false` disables input for its descendants but does not suppress rendering or autonomous animations. Runtime behavior coverage proves motion continues while that item and its descendants are disabled, then stops for reduced motion, runtime hiding, and zero global opacity.

### 2. Add schema and generic conditional metadata — complete

Update `services/EffectRegistry.js` to:

- add `precipitationStyle` and snow fields with enum fallbacks and bounds;
- add concrete labels and hints;
- attach generic `visibleWhen` metadata to rain-only and snow-only fields; and
- retain existing persisted rain keys and defaults.

Update the registry-driven field rendering in `components/SettingsWindow.qml` to evaluate same-effect enum visibility. Add tests proving hidden controls retain values, style switches reveal the correct controls immediately, reset restores both styles' defaults, and unrelated effects are unchanged.

Verify `services/AmbienceSettings.qml` needs no special migration: old documents normalize to `rain`, gain snow defaults, preserve unknown fields, and retain active order and schema version.

### 3. Extract rain without visual changes — complete

- Move current visual layers and animations into `RainPrecipitationStyle.qml`.
- Keep `RainfallEffect.qml` as the public ordered adapter and inject normalized rain properties into the internal component.
- Preserve current seeded startup, animation timing, object bounds, mist, splashes, colors, and vignette.
- Run static, behavior, visual-parity, and performance checks before beginning snow.

Do not combine cleanup or visual redesign with this extraction.

The isolated extraction comparison is pixel-exact for both pinned static and animated captures. Current one-output and three-output runtime samples retain 60 Hz frame cadence; see `docs/release/evidence/rainfall-extraction-parity.json` and `docs/performance/evidence/rainfall-post-extraction.json`.

### 4. Implement snow — complete

Build `SnowPrecipitationStyle.qml` with:

- one bounded repeater derived from `dropCount`;
- deterministic seeded position, size, depth, opacity, fall speed, flutter phase, and detail style;
- distributed initial progress across output height;
- long-running QML animations or a bounded shared clock, choosing the cheaper option through the performance harness;
- no process, polling, cursor use, particles, growing model, or per-frame allocation;
- static seeded flakes in reduced motion; and
- live theme, accent blend, population, size, flutter, detail, speed, slant, opacity, and geometry updates.

At `flakeDetail: mixed`, cap crystal delegates to a seeded subset so maximum population does not multiply primitive count unexpectedly.

A focused installed-runtime comparison at 320 flakes selected one 30 Hz shared `FrameAnimation` over 960 per-flake animations. Median process CPU was 10.50% for the shared clock versus 18.63% for per-flake animations on the recorded machine-local sample; see `docs/performance/evidence/snow-clock-selection.json`.

### 5. Integrate lifecycle and diagnostics — complete

- Keep the existing `rainfall` stack loader, supported ID, z-order, active count, and lazy-load conditions unchanged.
- Ensure style changes do not change `activeProductionEffectCount` or the root object returned by `productionEffectObject("rainfall")`.
- Add selected precipitation style and internal animation state to test/status data only where useful; avoid exposing every particle.
- Confirm style replacement, global disable, fullscreen suppression, reduced motion, and zero opacity stop the old and current internal animations.

### 6. Complete documentation and release integration — complete

`README.md`, `CHANGELOG.md`, `TODO.md`, release evidence, release harness contracts, and this plan now describe the completed rain/snow renderer. `dropCount` remains the backward-compatible on-disk population key while the UI labels it **Precipitation Count**. Rain and snow remain styles of one ordered `rainfall` effect, so the eleven-renderer release count is unchanged.

## Verification matrix

### Registry, persistence, and settings UI

- Old rain settings normalize to `precipitationStyle: rain` with all existing values unchanged.
- Invalid styles and flake details fall back to defaults; all numeric fields clamp and integers round.
- Unknown root, effect, and future style fields survive save/reload.
- Rain-only and snow-only controls show at the correct time and hidden values are retained.
- Reset restores defaults for both styles without changing active order.

### QML behavior and lifecycle

- The root Rainfall object remains stable across repeated rain/snow switches.
- Exactly one internal style component is loaded at a time.
- The replaced component stops all animation and leaves no timer or model alive.
- Rain retains full-height startup coverage, slant, mist, splash, and vignette behavior.
- Snow has distributed startup, bounded flutter, depth variation, and no synchronized empty-screen phase.
- `dropCount` bounds both styles; snow detail does not create an unbounded primitive multiplier.
- Reduced motion is static for both styles and runs no autonomous clock.
- Hidden, disabled, transparent, removed, and fullscreen-suppressed cases perform no autonomous work.
- Theme and settings changes apply live without replacing the root ordered effect.
- No QML warnings, binding loops, effect-local `Process`, effect-local `FileView`, cursor sampler, or growing particle model.

### Visual review

Extend the isolated visual harness with:

- rain before/after extraction for parity;
- rain at mist and splash extremes;
- snow at minimum/default/maximum population and size;
- snow with low/high flutter and negative/positive slant;
- soft, crystal, and mixed flake detail;
- reduced-motion rain and snow;
- foreground and background presentation;
- a live theme switch; and
- one-output and multi-output cases, including a negative origin.

### Performance review

Extend the one-output and three-output matrix with rain and snow as separate cases. Record defaults, maximum population, snow maximum size/detail, rain mist/splash extremes, reduced motion, style-switch churn, hidden, and fullscreen-suppressed states. Compare frame cadence, CPU ticks, memory, delegate/primitive count, animation count, and shutdown behavior against the pinned rain baseline.

## Implemented verification coverage

- The Phase 6 isolated visual matrix covers extracted-rain parity evidence, rain mist/splash extremes, snow population and size bounds, flutter/slant extremes, all detail modes, static reduced motion, presentation modes, and a motion-free snow theme switch on a negative-origin output.
- The dedicated precipitation multi-output probe renders rain and snow simultaneously on two temporary negative-origin outputs, validates compositor screenshot assignment, and records bounded particle/primitive and stopped-clock metrics.
- The real fullscreen harness keeps a snow renderer and its ordered Rainfall root alive across fake/real fullscreen suppression and foreground/background presentation changes, while proving its shared clock stops only for the suppressed interval.
- The Phase 7 matrix records rain and snow defaults, maxima, snow maximum size/crystal detail, rain mist/splash extremes, reduced motion, repeated style churn, hidden state, and fullscreen suppression at one and three outputs. It enforces delegate, primitive, animation, clock, root-identity, and shutdown bounds in addition to frame cadence, CPU ticks, and RSS. The recorded 28-cell, 4-second matrix retained 240–241 callbacks per cell with 16.45–18.52 ms mean frame intervals; every shutdown sample reported zero autonomous outputs.
- Machine-local CPU/frame evidence is directional, not a portable performance budget. The recorded CPU range was 2.05–76.11% and peak RSS was 334.61–440.64 MiB across isolated processes. Physical mixed-scale/refresh/rotation displays and subjective foreground layering remain manual release-review risks.

## Definition of done

- Existing `rainfall` settings and active stacks retain rain behavior by default with no special migration.
- Rain and snow are selectable through a normalized, registry-driven style field with appropriate generic conditional controls.
- Rain visual parity is preserved through extraction, and snow has distinct bounded fall, flutter, depth, and detail behavior.
- Style changes preserve the root ordered effect and cleanly replace only one internal renderer.
- Reduced motion, theme changes, presentation, fullscreen suppression, output geometry, and stack order work for both styles.
- The architecture can add a future style by registering fields and adding one bounded internal component rather than interleaving another animation tree into Rainfall.
- Static, persistence, settings, behavior, visual, multi-output, and performance checks pass through the repository's existing scripts.
