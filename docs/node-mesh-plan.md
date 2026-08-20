# Node Mesh Implementation Plan

Status: implemented and covered by automated settings, visual, fullscreen, multi-output, and performance matrices; Node Mesh remains opt-in. Physical mixed-output and subjective visual sign-off remain manual release work.

## Goal

Add `nodeMesh` as an ordered ambience effect after Bokeh. This branch is stacked on Bokeh but does not contain the unfinished Drip effect, so Node Mesh is currently the eleventh production effect here. It is intended to become twelfth only after later Drip integration. It should animate a bounded field of drifting nodes, connect nearby nodes into a responsive geometric mesh, and optionally let the pointer attract or repel the local field.

The effect must use the existing stack, settings, theme, shared cursor, presentation, persistence, geometry-settle, fullscreen, and multi-output contracts. It must not create its own cursor subprocess, settings reader, theme watcher, process, file service, window, or input surface.

## Visual and motion contract

- Distribute a deterministic, bounded set of nodes across the full output with seeded positions, velocities, sizes, opacity, and phases.
- Move nodes slowly and continuously. Wrap at an overscan boundary or reflect velocity without visibly clustering at screen edges.
- Connect nodes only when their current distance is within `connectionDistance`.
- Fade each connection by distance so nearby links are clearer and links at the cutoff reach zero opacity.
- Limit each node to a small number of nearest connections and draw each undirected pair only once. Dense settings must not create an uncontrolled complete graph.
- Render connections beneath nodes. Nodes should remain legible at low line opacity without becoming bright ornaments.
- Resolve node and line colors from selectable theme roles through `ThemeAdapter.colorFor()`. Theme changes must recolor the existing mesh live.
- Multiply node and line opacity by normalized per-effect intensity and global opacity.
- Pointer interaction applies only on the output containing the shared cursor sample. `attract` pulls nearby nodes toward the pointer, `repel` pushes them away, and `off` performs no pointer work.
- Clamp pointer acceleration, node velocity, and displacement so nodes cannot explode across the output after a fast cursor movement or delayed sample.
- In reduced-motion mode, render a deterministic static mesh and disable pointer force, node integration, and autonomous animation.
- Stop frame updates and pointer work when the effect is hidden, disabled, fully transparent, removed from the stack, fullscreen-suppressed, or unable to paint.

## Bounded mesh-rendering contract

A proximity mesh needs shared current node positions, so independent `NumberAnimation`s are not sufficient. Use one bounded simulation and one connection-drawing surface:

- Store node state in a fixed-size JavaScript array owned by the renderer; rebuild it only when population or output geometry requires it.
- Publish array mutation through an explicit reactive `simulationRevision` property. Increment it once after each accepted update, and make delegate position accessors depend on that revision so QML bindings cannot remain stale after in-place JavaScript-array changes.
- Advance the simulation with one `FrameAnimation`, but cap integration and repaint to a target of 30 updates per second. Accumulate `frameTime`, clamp large deltas after stalls, and perform no work while stopped.
- Use a uniform spatial grid keyed by `connectionDistance` to discover nearby candidates. Do not scan every possible pair at maximum density on every frame.
- Cap connections at four nearest neighbors per node and enforce a hard derived edge ceiling of `nodeCount * 4 / 2`.
- Draw all connection lines in one retained `Shape` backed by eight declarative `ShapePath`/`PathMultiline` opacity buckets. The paths must exist during the Shape lifecycle; do not dynamically parent paths after Shape completion or allocate/destroy ShapePath objects during steady-state simulation.
- Publish path coordinate, opacity, geometry, theme/color, and setting changes only after an accepted simulation or explicit invalidation. Do not create one QML object per possible complete-graph edge.
- Use one bounded `Repeater` for visible node discs. Delegates read positions through revision-aware accessors from the same accepted simulation snapshot used by the Shape.
- Avoid a second timer, particles, effect-local models that grow over time, and per-node animation objects.

### Phase 1 renderer decision: render-proven declarative ShapePath buckets

Final review found that dynamically parenting retained `ShapePath` objects to an already-completed `Shape` produced no connection pixels. The corrected renderer declares eight `ShapePath` objects with retained `PathMultiline` opacity buckets inside the Shape lifecycle. A pixel probe proves visible production lines, visible connection-distance and line-opacity changes, and 99.93% overlap of the smaller Canvas/Shape geometry mask. The equivalent-output benchmark still found Shape materially cheaper in every default/maximum and one/three-output matrix cell, so Canvas remains rejected. See `docs/performance/evidence/node-mesh-pixels.json`, `docs/performance/node-mesh-renderer-selection.md`, and `docs/performance/evidence/node-mesh-renderer.json`.

The proposed 120-node maximum and 30 Hz cadence remain accepted for production. The completed effect must rerun the performance matrix with node delegates and pointer interaction before release.

## Proposed settings schema

Add this definition to `services/EffectRegistry.js`:

| Field | Type and proposed bounds | Purpose |
| --- | --- | --- |
| `enabled` | bool, default `true` | Standard ordered-effect enablement. |
| `intensity` | real `0..1`, default `0.48` | Overall mesh visibility. |
| `speed` | real `0.15..4`, default `0.7` | Common multiplier for node drift. |
| `nodeCount` | int `12..120`, default `54` | Number of pooled nodes per output. |
| `nodeSize` | real `1..10`, default `3` | Base node diameter before seeded variation. |
| `connectionDistance` | int `40..260`, default `132` | Maximum distance at which nodes may connect. |
| `lineWidth` | real `0.5..3`, default `1` | Connection stroke width. |
| `lineOpacity` | real `0..1`, default `0.3` | Connection visibility relative to intensity. |
| `driftAmount` | real `0..1`, default `0.38` | Magnitude of autonomous node movement. |
| `pointerMode` | enum, default `off` | Selects `off`, `attract`, or `repel`. |
| `mouseInfluence` | real `0..1`, default `0.3` | Strength and radius of pointer force. |
| `nodeColorRole` | enum, default `accent` | Theme role for nodes. |
| `lineColorRole` | enum, default `color12` | Theme role for connections. |

Use the palette-role values already exposed for theme-aware effects: `accent`, `foreground`, `color09`, `color10`, `color11`, `color12`, `color13`, and `color14`. Add specific labels and hints for every Node Mesh field.

Adding normalized `nodeMesh` defaults must not insert it into existing users' `activeEffects`. Existing documents should gain the default payload while preserving active order, unknown JSON-safe fields, and schema version.

## Cursor and multi-output contract

Reuse the single `services/CursorTracker.qml` instance owned by `Panel.qml`.

- Inject `targetScreen` and `cursorTracker` into Node Mesh through `components/AmbienceStack.qml`.
- Convert global cursor coordinates to output-local coordinates using the target screen's `x` and `y`, including negative monitor origins.
- Determine cursor ownership from the raw sample; smoothed display coordinates may drive the visual force only after ownership is known.
- Extend `Panel.qml` cursor-request aggregation rather than creating a new tracker. Request tracking only when Node Mesh is active, paintable, visible, not reduced-motion, `pointerMode` is not `off`, and `mouseInfluence` is nonzero.
- Keep one polling cadence selected from the combined Dust Motes, Tactical Grid, and Node Mesh requirements. Do not multiply cursor processes by effect or output.
- Pointer state becoming unavailable must decay or clear force without leaving nodes displaced indefinitely.

## Implementation phases

### 1. Resolve and pin the rendering strategy — complete

- [x] Built isolated Canvas and Shape prototypes at default and maximum node counts.
- [x] Measured update cost on one and three outputs on Qt 6.11.1 / Quickshell 0.3.0.
- [x] Selected eight render-proven declarative ShapePath/PathMultiline buckets and pinned the maximum 120 nodes, four neighbors, 240 edges, and 30 Hz cadence in contract tests.
- [x] Confirmed no bounded schema reduction is required before production implementation.

### 2. Pin contracts with failing tests — complete

- Extend registry and normalization tests for `nodeMesh`, enum fallbacks, integer rounding, palette roles, and numeric bounds.
- Extend ordered-effect sets, renderer counts, stack injection, load-smoke, settings-window, and shared-cursor expectations.
- Add behavior fixtures for negative output origins, pointer ownership across adjacent outputs, attract/repel direction, force clamping, reduced motion, and invalid cursor samples.
- Pin lazy-loading, frame-clock shutdown, bounded edge count, and renderer identity.

### 3. Register settings metadata — complete

Update `services/EffectRegistry.js` to:

- register `nodeMesh` with the proposed fields;
- add concrete labels and hints;
- rely on generic defaults, normalization, known-key, and field-definition functions; and
- keep `backgroundVignette` separate from ordered effects.

Verify that `services/AmbienceSettings.qml` automatically normalizes Node Mesh defaults, preserves unknown JSON-safe fields, and leaves `activeEffects` unchanged.

### 4. Build `effects/NodeMeshEffect.qml` — complete

Follow the injected production adapter:

- properties: `effectSettings`, `globalOpacity`, `reducedMotion`, `theme`, `targetScreen`, `cursorTracker`, `runtimeEnabled`, and optional `runtimeIntensity`;
- consume normalized values directly from `overlaySettings`;
- expose testable properties for local cursor coordinates, cursor ownership, simulation-running state, `simulationRevision`, update count, node count, edge count, edge ceiling, and effective colors;
- keep deterministic initial state for stable tests and visual startup;
- rebuild state in a controlled generation only for node-count or geometry changes;
- preserve the root effect object across live settings, theme, stack-order, presentation, and cursor changes;
- update node delegates and the line surface from the same accepted simulation snapshot; and
- clear or suspend stale motion cleanly after geometry, reduced-motion, visibility, or cursor-availability changes.

### 5. Integrate stack and shared cursor requests — complete

Update `components/AmbienceStack.qml` to add the supported ID, component, lazy loader, injected target screen/theme/cursor, active count, and object lookup while retaining z-order and geometry settling.

Update `Panel.qml` to add a Node Mesh cursor request to the existing shared aggregation. Keep Dust Motes and Tactical Grid behavior unchanged, preserve one tracker, and expose enough status data to diagnose whether Node Mesh requested tracking and which output owns the pointer.

### 6. Complete settings and documentation integration — complete

Verify the registry-driven settings UI shows Node Mesh in **Add Effect**, renders all generic field types, saves immediately, and resets to defaults without Node Mesh-specific editor code.

When implementation is complete, update `README.md`, `CHANGELOG.md`, release evidence, effect counts, and the Node Mesh entry in `TODO.md`.

### 7. Verification matrix — automated coverage complete

#### Host-independent and QML behavior

- Registry defaults, bounds, integer rounding, and invalid enum/role fallback.
- Existing documents gain defaults without changing active order or unknown fields.
- Lazy loading, reordering, z-order, geometry settling, enablement, and object identity.
- Deterministic startup and bounded node/edge populations at every setting.
- Connections occur only within the cutoff, fade by distance, obey the neighbor cap, and are not duplicated.
- Pointer attraction and repulsion have the correct sign only on the pointer's output.
- Global-to-local conversion works on positive and negative output origins.
- Pointer mode off, zero influence, invalid samples, and reduced motion perform no pointer updates.
- Reduced motion renders a static mesh and stops the simulation clock.
- Theme, role, opacity, size, distance, and line settings update live.
- No QML warnings, binding loops, effect-local `Process`, effect-local `FileView`, extra cursor tracker, unbounded model, or per-edge QML object.

#### Visual review

Add Node Mesh to the isolated visual harness and capture:

- minimum, default, and maximum node populations;
- short and long connection distances;
- low and high line opacity;
- pointer mode off, attract, and repel;
- pointer near the center and edges;
- reduced-motion output;
- foreground and background presentation;
- a theme switch; and
- at least two outputs with different origins and pointer ownership on only one.

#### Performance review

Add Node Mesh to the one-output and three-output performance matrix. Record idle/static, default animation, maximum node count and distance, pointer off, active attraction/repulsion, hidden, and fullscreen-suppressed cases. Compare frame cadence, CPU ticks, memory, simulation updates, paint requests, node count, edge count, and cursor-process launch count. Confirm the update cap and that one shared cursor sampler serves all requesting effects.

## Implemented verification coverage

- The registry-driven SettingsWindow behavior test adds Node Mesh, enumerates all 13 fields across bool, real, int, and enum editors, confirms immediate atomic persistence, and proves reset restores Node Mesh defaults without any `nodeMesh` branch in `SettingsWindow.qml`.
- The isolated visual matrix captures minimum/default/maximum populations, short/long connection distances, low/high line opacity, pointer off, attract/repel at center and edge positions, reduced motion, foreground/background stack presentation, and a static theme switch. The latest safe headless run completed 38 captures with no QML errors, a 16.67 ms mean frame callback, 18.91 ms maximum, and zero callbacks over 20 ms.
- The dedicated pixel probe records 2,779 changed production pixels for line opacity, 14,112 for connection distance, and 99.93% smaller-mask geometry overlap between visibly rendering Canvas and Shape prototypes.
- Renderer CPU ticks and RSS sampling begin only at the post-warmup `BENCH_READY` boundary and end at an independent three-second deadline. The latest 24 samples measured 3.00002–3.00011 seconds separately from 4.638–5.078 second total process lifetimes.
- Runtime behavior probes prove a one-second stalled frame accepts exactly one fixed step with zero retained backlog, and prove toggling `enabled` preserves the resident Node Mesh root while accepting zero updates during the disabled interval.
- The real Panel fullscreen harness keeps Bokeh and Node Mesh renderer identities alive while switching foreground/background presentation and proves Node Mesh simulation stops during real fullscreen suppression while the surface remains mapped.
- The reversible two-output visual probe records `docs/release/evidence/node-mesh-multi-output.json`, captures both 1920×1080 outputs at distinct negative origins, and proves one shared pointer sample activates force on exactly one renderer. Per-output diagnostic markers produce the assignment matrix `[[true, false], [false, true]]`, and the harness explicitly proves swapped captures are rejected before attesting compositor placement.
- The production performance evidence in `docs/performance/evidence/node-mesh-production.json` covers one and three 1920×1080 outputs at negative origins. It records static, default, maximum density/distance, pointer off, attract, repel, hidden, and fullscreen-suppressed cases with updates, path publications, node/edge/path populations, pointer ownership, frame cadence, CPU, RSS, and cursor launch count.
- The maximum production sample remained bounded at 120 nodes, 240 accepted edges, and eight retained ShapePaths per output. Three-output maximum density averaged 23.43% of one CPU core in the recorded directional sample; static, hidden, and suppressed cases accepted zero simulation updates.
- One deterministic fake shared cursor sample owned exactly one output in both the one- and three-output attraction/repulsion samples. The one shared real cursor sampler launched 16 times in each 1.8-second pointer sample regardless of output count, while pointer-off launched zero samplers.
- Physical mixed-scale/rotated-output screenshots and subjective review over representative application windows remain manual; automated headless evidence does not replace that sign-off.

## Definition of done

- `nodeMesh` is a normalized, reorderable, lazily loaded production effect and is not enabled in existing active stacks by default.
- Nodes drift in a stable bounded simulation and nearby connections form a responsive mesh without uncontrolled pair growth.
- Pointer attraction and repulsion work on arbitrary multi-output coordinates through the one shared cursor tracker.
- Reduced motion is static; hidden or suppressed renderers perform no simulation or paint work.
- Theme, settings, presentation, geometry, fullscreen suppression, and stack-order changes apply live.
- The selected line renderer passes the one-output and three-output performance matrix at maximum supported density.
- Static, behavior, visual, multi-output, and performance checks pass through the repository's existing scripts.
