# Presets Implementation Plan

**Status:** Planned
**Recommended release:** the first feature release after the combined `0.6.1` animation release

## Goal

Add two related but deliberately separate preset systems:

1. **Stack presets** restore an ordered animation composition and the settings of every animation in that composition.
2. **Effect presets** restore the settings of one animation without changing stack membership or order.

Both systems should ship with curated built-in presets and support user-saved presets. Applying a preset must be understandable before it happens, atomic once confirmed, reversible once, theme-portable, and compatible with the existing normalization, persistence, lazy-loading, fullscreen, reduced-motion, preview-pause, and multi-output contracts.

Presets are reusable content, not a second renderer state. Renderers continue to consume only the normalized live settings document.

## Product vocabulary

Use **Stack presets** and **Effect presets** everywhere in the interface. Avoid the ambiguous standalone label “Preset.”

- A **stack** means the ordered `activeEffects` composition plus the settings of the included effects.
- An **effect preset** means settings for exactly one known effect.
- A future full-environment preset that changes presentation or accessibility preferences should use a different name, such as **Scene**. Do not overload stack presets with that behavior.

The existing persisted `cinematicLight.stylePreset` field remains unchanged for compatibility, but its interface label stays **Light Style** so it is not confused with the new preset library.

## Scope contract

Preset application must have narrow, predictable ownership.

| State | Stack preset | Effect preset |
| --- | --- | --- |
| Active effect membership | Replace | Preserve |
| Front-to-back order | Replace | Preserve |
| Known settings of included/target effect | Replace from snapshot | Replace from snapshot |
| Per-effect `enabled` | Restore for included effects | Preserve |
| Settings of effects outside the applied stack | Preserve | Preserve |
| Global ambience `enabled` | Preserve | Preserve |
| Presentation (`background`/`foreground`) | Preserve | Preserve |
| Global opacity | Preserve | Preserve |
| Reduced motion | Preserve | Preserve |
| Dedicated vignette | Preserve | Preserve |
| Pause Preview | Preserve; session-only | Preserve; session-only |
| Bar icon or shell configuration | Never touch | Never touch |

This treats global opacity like a master volume: choosing a composition should not override the user’s preferred overall level. The dedicated vignette is intentionally outside `activeEffects`, so it is also outside a stack preset. A later Scene feature may explicitly include those values if real demand appears.

If ambience is globally disabled, applying a preset still updates the saved composition but does not silently enable it. The result message should say that ambience is off and offer a separate **Enable ambience** action.

If an effect preset targets an effect outside the active stack, its settings are updated without adding it. The result message should offer a separate **Add to stack** action.

## Snapshot semantics

Presets are deterministic snapshots, not loose slider patches.

- A built-in or user stack preset stores every known field for each included effect, including per-effect `enabled`.
- An effect preset stores every known field except `enabled`.
- Missing known fields resolve through the current `EffectRegistry` defaults. This lets an older preset adopt safe defaults for fields added by a newer release.
- Existing unknown JSON-safe fields in the live effect payload remain untouched when known fields are replaced. Applying an older preset must not erase forward-compatible data created by a newer plugin version.
- Stack application replaces `activeEffects` in one operation, then replaces known fields for only the included effects. Settings for effects removed from the stack remain available for later reuse.
- Persisted enum values remain stable registry IDs; human-readable labels are presentation only.
- Built-in stack definitions must be self-contained after resolution. They must not reference mutable effect-preset IDs at runtime.

`backgroundVignette` must never appear as an ordered effect or as a stack-preset effect payload.

## Architecture

### 1. `services/EffectRegistry.js` remains the effect schema authority

Keep effect IDs, labels, fields, defaults, bounds, enum IDs, enum labels, and normalization here. Add only the small helper surface needed by presets:

- known-field enumeration;
- snapshot of known values;
- merge of a normalized known-field snapshot over a live payload while retaining unknown fields;
- display formatting metadata used by preset summaries.

Do not place the preset catalogue inside `EffectRegistry.js`. Effect schemas and authored preset content have different ownership and review cadence.

### 2. Add `services/PresetRegistry.js`

This `.pragma library` module owns pure, side-effect-free preset behavior:

- immutable built-in stack and effect preset definitions;
- stable IDs, names, descriptions, source, and ordering;
- normalization and validation of preset entries;
- capture helpers for stack and effect snapshots;
- apply helpers that return one candidate live settings document;
- canonical comparison helpers for **Current**, **Modified**, and **Not applied** states;
- plain-language summary data derived from `EffectRegistry` metadata;
- validation of stable opaque user IDs supplied by the store/controller.

ID generation is intentionally not a registry responsibility because time and entropy are side effects. `PresetStore.qml` should generate IDs from injected clock/entropy helpers, then ask `PresetRegistry.js` to validate syntax and collisions. Tests must inject deterministic values.

Recommended API:

```text
builtInStackPresets()
builtInEffectPresets(effectId)
normalizeUserLibrary(source)
captureStackPreset(document, metadata)
captureEffectPreset(document, effectId, metadata)
applyStackPreset(document, preset)
applyEffectPreset(document, preset)
stackPresetMatches(document, preset)
effectPresetMatches(document, preset)
presetDiff(document, preset)
```

Every returned object must be a deep copy. No caller may mutate the built-in catalogue.

### 3. Add a separate `services/PresetStore.qml`

User presets are reusable library content and should not be embedded in `settings.json`. Store them at:

```text
$XDG_CONFIG_HOME/omarchy/jobo/desktop-ambience/presets.json
```

`AmbienceSettings.qml` remains the sole owner of `settings.json`. `PresetStore.qml` becomes the sole owner of `presets.json`. Built-ins remain code-owned and are never copied into the user file.

Keeping the files separate provides important failure isolation:

- a malformed user library cannot unmap or change the active ambience;
- saving, renaming, or deleting a preset does not create runtime-settings revisions;
- resetting runtime settings does not destroy the user’s library;
- future import/export can operate on a content library without exposing the live settings document.

`Panel.qml` should instantiate one `PresetStore`, then inject it into the one `SettingsWindow`. Effects, surfaces, and `AmbienceStack` must never receive it.

### 4. Share the raw atomic-file primitive, not document semantics

Before adding a second writable JSON document, extract the path setup, atomic `FileView` writes, serialized revisions, retry state, and external-change suppression from `AmbienceSettings.qml` into a narrow reusable component such as `services/AtomicJsonStore.qml`.

The extraction should be a behavior-preserving commit with the full existing persistence suite passing before preset work continues.

`AtomicJsonStore.qml` owns bytes and revision state only. It must not know effect schemas, preset schemas, defaults, or JSON normalization. `AmbienceSettings.qml` and `PresetStore.qml` remain responsible for parsing, normalization, last-valid state, divergence messages, and public projections.

This avoids two drifting copies of the hardened persistence state machine without coupling the two documents into a cross-file transaction.

### 5. `components/SettingsWindow.qml` remains the interaction controller

The window should:

- request normalized preset data from `PresetStore`/`PresetRegistry`;
- ask `PresetRegistry` to produce one candidate live document;
- call `settings.save(candidate)` exactly once per apply or undo;
- call `PresetStore` exactly once per create, update, rename, or delete;
- own selection, confirmation, naming-form, and one-step undo state;
- never implement field bounds, preset normalization, or raw file I/O itself.

Do not create one save per included effect. That would expose intermediate compositions, churn loaders, and defeat the current queued-write contract.

## User library schema

Use a versioned, ordered, unified array:

```json
{
  "version": 1,
  "presets": [
    {
      "id": "user-m6m7y2-f4ac9d",
      "kind": "stack",
      "name": "Quiet Orbit",
      "description": "Dim lights and slow dust for an unobtrusive desktop.",
      "createdAt": "2026-08-20T12:00:00Z",
      "updatedAt": "2026-08-20T12:00:00Z",
      "activeEffects": ["bokeh", "dustMotes"],
      "effects": {
        "bokeh": { "enabled": true, "intensity": 0.3 },
        "dustMotes": { "enabled": true, "intensity": 0.22 }
      }
    },
    {
      "id": "user-m6m80p-1e02aa",
      "kind": "effect",
      "effectId": "bokeh",
      "name": "Distant lights",
      "description": "Large, quiet lights with almost no twinkle.",
      "createdAt": "2026-08-20T12:05:00Z",
      "updatedAt": "2026-08-20T12:05:00Z",
      "values": { "intensity": 0.28, "speed": 0.4 }
    }
  ]
}
```

The abbreviated payload above is illustrative. Captured and resolved presets must contain the full known snapshot required by the snapshot contract.

### Library normalization

- Use opaque stable IDs independent of mutable names. IDs must never become paths or QML component names.
- Trim names; require `1..48` characters. Descriptions are optional and limited to 160 characters.
- Enforce case-insensitive name uniqueness across the combined built-in/user stack scope and across the combined built-in/user scope for each effect. The same name may exist for different effects. Default copy names should use a visible suffix such as “Quiet Orbit copy.”
- Accept only `stack` and `effect` kinds.
- Only known effect IDs are applicable. Unknown effect payloads remain JSON-safe and round-trippable but never become renderable.
- Preserve unknown JSON-safe top-level and per-entry metadata for forward compatibility.
- Quarantine invalid entries from the visible/applicable catalogue while retaining them on round-trip and exposing a repairable warning.
- Malformed JSON or an invalid root retains the last valid in-memory library and reports divergence, matching the safety posture of runtime settings.
- A missing first-run `presets.json` is a healthy, loaded, empty catalogue with no divergence, failure, or retry state. Create it only on the first catalogue mutation.
- Reject new user-created presets once 128 valid user entries exist. If an externally edited file already exceeds 128 valid entries, retain and expose every entry through a virtualized list, warn that the supported limit was exceeded, and reject further creation until the user deletes enough entries. Never hide or serialize only the first 128 entries.

Built-in definitions are trusted code but must pass stricter release tests: duplicate IDs, duplicate scoped names, unknown effects, missing snapshots, out-of-range values, or forbidden global/vignette keys fail the suite.

## Apply, create, update, and delete flows

### Apply a stack preset

1. Normalize the current live document.
2. Capture one session-only undo snapshot.
3. Resolve and validate the selected preset against the current `EffectRegistry`.
4. Replace `activeEffects` with the valid preset order.
5. Replace known settings for included effects while preserving unknown live keys.
6. Preserve every global value, the dedicated vignette, inactive effect payloads, bar icon, and Pause Preview.
7. Record the candidate’s canonical signature, call `settings.save(candidate)` once, and retain the resulting `requestedSaveRevision`.
8. Keep the selected preset visible and show a keyboard-reachable result strip whose state follows that revision: **Applying…**, **Quiet Orbit applied and saved · Undo**, or **Applied for this session; save failed · Retry · Undo**. If Undo or another edit supersedes the apply revision, the older completion must not replace the newest message.

The detail view must show additions, removals, and final front-to-back order before application. Selecting a preset never applies it.

### Apply an effect preset

1. Capture one session-only undo snapshot.
2. Replace known fields for the target effect except `enabled`.
3. Preserve stack membership, order, globals, vignette, and every other effect.
4. Record the candidate’s canonical signature, call `settings.save(candidate)` once, and retain the resulting `requestedSaveRevision`.
5. Drive the same pending/saved/failed/retry/superseded result-strip state machine used by stack application. Only after confirmation report **“Settings applied and saved. Bokeh is not in the active stack.” · Add to stack · Undo**; a failed write must instead say that settings are applied for this session and offer **Retry** and **Undo**.

### Save current stack

Capture the normalized `activeEffects` order and full known settings for those effects. An empty stack cannot be saved as a stack preset. Saving a preset does not change runtime settings because the current state is already applied.

### Save current effect settings

Capture the selected effect’s known fields except `enabled`. Saving does not add, enable, or reorder the effect.

### Update, rename, and delete

- User presets offer **Update from current**, **Rename**, and **Delete**.
- Updating replaces the relevant saved snapshot only after an explicit named confirmation.
- Renaming validates inline before save.
- Deleting requires explicit named confirmation and restores keyboard focus to the nearest remaining row.
- Built-ins are immutable. A user can apply a built-in, modify the result, and choose **Save as new preset**.
- Applying a preset supports one-step runtime undo. Update and delete use confirmation in the first release; catalogue undo may be added later if usage shows it is needed.
- Store undo state as `{ beforeSnapshot, appliedSignature, requestedRevision }`. Retain it while the live canonical signature still equals the applied candidate or that revision remains pending. Clear it only when a different live signature/revision wins, an external reload changes owned state, Undo succeeds, or the window closes. A generic `dataChanged` handler must not clear the snapshot created by its own apply.
- Undo creates one newer `settings.save(beforeSnapshot)` intent. If the apply write is still in flight, the existing newest-intent queue must allow Undo to supersede it cleanly.

There is intentionally no cross-file transaction. Catalogue mutations affect only `presets.json`; applying and undoing affect only `settings.json`.

## Settings-window design

### Organizing idea

Reuse the existing two-panel window as a catalogue/detail workspace. Add a keyboard-focusable mode switch directly below the header divider:

```text
[ Compose ] [ Presets ]
```

Do not add preset navigation to the crowded header action row.

The memorable visual element is an **ordered layer spine**: a compact numbered vertical sequence that shows a stack preset’s real front-to-back effect order. It is informative, theme-aware, and more durable than screenshot thumbnails.

### Presets mode: left catalogue

Reuse the 260–310px composition panel:

1. Type switch: **Stack presets** / **Effect presets**.
2. In Effect presets, an effect selector initialized from `selectedEffectId`.
3. **Built-in** section.
4. **My presets** section.
5. Contextual capture action:
   - **Save current stack**
   - **Save Bokeh settings**

Use compact selectable rows, not a card grid. Each row includes name, source badge, a concise scope summary, and **Current** when the live state canonically matches. Use a virtualized list so externally edited catalogues above the supported creation limit remain inspectable and repairable.

Empty state copy should teach the next action:

> No saved stack presets yet. Set up the stack you want, then choose Save current stack.

### Presets mode: right detail

Show:

- source/type eyebrow, such as **BUILT-IN STACK** or **MY BOKEH PRESET**;
- name and one-sentence description;
- **Current**, **Modified**, or **Not applied** state;
- ordered layer spine for stack presets;
- two or three meaningful, human-formatted settings for effect presets;
- a plain-language scope block:
  - **Changes:** stack order and listed effect settings;
  - **Keeps:** ambience on/off, presentation, opacity, reduced motion, and vignette;
- an **Off in preset** badge for any included effect whose saved per-effect `enabled` value is false;
- additions/removals diff for stack application;
- primary **Apply stack** or **Apply settings** action;
- immutable built-in affordance or user management actions.

Preset summaries must use registry labels and formatted values. Never show raw IDs such as `lightLeak`, `color13`, or internal field keys.

### Compose-mode entry points

- Add a compact **Effect presets…** action below the selected effect title/status, rather than adding a third full-width button beside **Reset effect** and **Add to stack**.
- Add **Save current stack** near the **ACTIVE STACK · FRONT TO BACK** heading.
- Both actions switch to Presets mode with the appropriate type and selection.

### Naming and confirmation forms

Use an inline detail-panel form rather than another top-level window:

- required Name;
- optional Description;
- immediate duplicate and length feedback;
- explicit **Save preset** / **Cancel** actions.

Stack application does not need a second modal if the persistent detail view already displays its exact diff and scope. Destructive catalogue operations require inline confirmation with the preset’s name.

### Accessibility and minimum-size behavior

- Build mode tabs, preset rows, and actions from keyboard-capable controls, not bare `MouseArea`.
- Support visible focus, Enter/Space activation, stable tab order, and descriptive accessible names.
- Never communicate source/current/error state by color alone.
- Keep approximately 40px action targets.
- Restore focus after apply, delete, cancel, and mode changes.
- Focused catalogue rows must scroll into view inside the `Flickable`/list. Mode controls need tab semantics, and preset rows must announce selected/current/source state through accessible text or roles.
- At the existing 720×560 minimum, keep a 260px catalogue, a single-column detail panel, wrapped action rows, and wrapped layer labels.
- Do not introduce thumbnail grids or invent a below-720px responsive contract in this feature.

## Built-in catalogue authoring

Start small enough to validate visually but broad enough to demonstrate both systems.

### Candidate stack presets

Author approximately six, each with no more than three effects until the performance matrix proves a larger composition safe:

- **Quiet Orbit** — Bokeh and Dust Motes.
- **Northern Veil** — Aurora Drift, God Rays, and Bokeh.
- **Analog Afterimage** — VHS, CRT, and Film Grain.
- **Cinema Haze** — Cinematic Light, Film Grain, and Bokeh.
- **Storm Glass** — Rainfall and Bokeh.
- **Red Protocol** — Tactical Grid and blood-mode Drip.

These names and memberships are candidates, not release evidence. Each must be tuned against multiple themes, background and foreground presentation, one and three outputs, reduced motion, and the maximum supported stack cost before inclusion.

### Candidate effect presets

Target two to four distinctive presets per effect, with names grounded in that effect rather than generic “Low/Medium/High” tiers:

- Aurora Drift: **Quiet Veil**, **Boreal**, **Solar Storm**.
- Cinematic Light: **Soft Leak**, **Wide Flare**, **Anamorphic**.
- CRT: **Fine Scan**, **Tube Bloom**, **Damaged Tube**.
- Dust Motes: **Sparse Room**, **Sunlit Dust**, **Swarm**.
- Drip: **Sparse**, **Heavy Weather**, **Bloodletting**.
- Bokeh: **Distant Lights**, **Dreamy**, **Glitter**.
- Film Grain: **Fine Stock**, **16mm**, **Rough Stock**.
- God Rays: **Dawn**, **Cathedral**, **Shimmer**.
- Rainfall: **Mist**, **Steady Rain**, **Downpour**.
- Tactical Grid: **Survey**, **Target Lock**, **Red Alert**.
- VHS: **Clean Tape**, **Tracking**, **Worn Dub**.

Exact values should be authored through screenshot and performance review, then pinned in `PresetRegistry.js` and covered by catalogue validation tests.

## Current and modified-state derivation

Do not persist a “currently applied preset ID.” Manual edits would make it stale immediately.

Instead, compare canonical normalized snapshots:

- **Current**: every owned value and, for a stack, exact membership/order match.
- **Modified**: the preset was applied this session but an owned value now differs.
- **Not applied**: neither condition holds.

This comparison ignores global values that the preset does not own and unknown live fields that it intentionally preserves.

## Testing plan

### Registry and schema tests

- Built-in IDs and scoped names are unique and stable.
- Every referenced effect is ordered and known.
- Every built-in snapshot resolves to complete in-range known fields.
- Effect presets exclude `enabled`; stack snapshots include it.
- Stack definitions exclude globals and `backgroundVignette`.
- Built-in accessors return deep copies.
- Human summaries never expose raw enum IDs.

### Preset transformation tests

- Stack apply replaces membership and order in one candidate document.
- Included settings are deterministic; inactive effect payloads remain untouched.
- Effect apply preserves `enabled`, membership, and order.
- Both kinds preserve global enabled state, presentation, opacity, reduced motion, vignette, unknown live fields, and bar configuration boundaries.
- Unknown preset effect IDs never become active.
- Capture/apply round trips are canonical and idempotent.
- Current/Modified comparison owns only the documented scope.
- Undo restores the exact prior normalized runtime document through one save.

### Preset-store tests

Mirror the proven persistence cases for `presets.json`:

- serialized rapid saves and newest-intent wins;
- atomic replacement;
- write failure and retry;
- missing first-run file reports a healthy empty library without creating bytes;
- malformed external edit retains last valid data;
- valid external edit reloads;
- invalid entries are quarantined and retained;
- unknown metadata round-trips;
- limits, names, combined built-in/user duplicate names, timestamps, and opaque IDs normalize safely;
- reserved object keys such as `__proto__`, `constructor`, and `prototype` cannot alter prototypes and normalize idempotently;
- oversized external libraries expose all entries for repair but reject new creation;
- runtime `settings.json` remains byte-for-byte unchanged during catalogue-only operations;
- Reset All leaves `presets.json` and the in-memory preset catalogue unchanged, and its confirmation copy states that saved presets are kept.

### QML interaction tests

- Browse built-in and user sections for both kinds.
- Selecting never applies.
- Stack apply emits one settings save and no intermediate active order.
- Effect apply does not add an inactive effect.
- Save, duplicate-name rejection, rename, update confirmation, and delete confirmation persist across restart.
- Built-ins cannot be renamed, updated, or deleted.
- Apply/Undo integrates with requested and confirmed save revisions.
- Apply reports pending, confirmed, failed, retrying, and superseded outcomes accurately.
- Undo while apply is in flight becomes the newest intent; failure/retry and external-edit races retain the correct snapshot and message.
- Undo clears on a different canonical signature/revision, external owned-state change, successful undo, or window close, but not on its own apply mutation.
- Ambience-off and inactive-effect result actions are accurate.
- Compose-mode contextual entry points select the correct preset type/effect.
- Preset rows and tabs are keyboard operable with visible focus, tab semantics, accessible state announcements, and focus-follow scrolling.

### Visual and live validation

- Capture Presets mode at 920×760 and the existing 720×560 minimum.
- Check long names, maximum description length, empty custom sections, warnings, confirmations, save failure, and narrow wrapped actions.
- Render every shipping built-in stack in representative light/dark themes, background/foreground presentation, reduced motion, and one/three-output configurations.
- Verify one atomic stack switch does not show an intermediate composition or leave stale loaders.
- Add the heaviest built-in stack to the performance matrix.
- Verify Pause Preview still halts rendering and cursor sampling while catalogue operations remain usable.

## Implementation phases and gates

### Phase 0 — Pin semantics and persistence reuse

- Approve the scope matrix, snapshot behavior, separate-file decision, and catalogue limits.
- Extract `AtomicJsonStore.qml` without changing settings behavior.
- Preserve `AmbienceSettings` public projections and behavior as compatibility aliases, including `settingsDir`, `settingsFile`, requested/confirmed revisions, retry state, divergence state, watcher behavior, and existing IPC output.
- Run the complete existing normalization, persistence-race, malformed-edit, retry, and live settings suite.

**Gate:** `settings.json` bytes, public service API, IPC status, and all persistence behavior remain compatible before preset code lands.

### Phase 1 — Pure registry and transformation layer

- Add `PresetRegistry.js` with schema validators, built-in accessors, capture/apply/diff/compare helpers, and initial test-only fixtures.
- Add the minimal known-field and formatting helpers to `EffectRegistry.js`.
- Pin the scope and forward-compatibility tests before adding UI.

**Gate:** preset transformations are deterministic, idempotent, and incapable of mutating globals or unknown renderer state.

### Phase 2 — User preset store

- Add `PresetStore.qml` on the shared atomic primitive.
- Implement missing/malformed/external-edit/retry behavior and the versioned library schema.
- Instantiate it once in `Panel.qml` and inject it only into `SettingsWindow`.

**Gate:** catalogue operations cannot change runtime settings, and preset-file failures cannot change or suppress ambience.

### Phase 3 — Browse, inspect, apply, and undo

- Add Compose/Presets mode switching.
- Build catalogue rows, type/effect filters, detail scope, layer spine, diff, Current/Modified state, and apply actions.
- Add one-step runtime undo and inactive/off-state follow-up actions.
- Ship built-ins as read-only in this phase if necessary.

**Gate:** both preset kinds apply through one save, expose no intermediate state, and are fully keyboard operable.

### Phase 4 — Create and manage user presets

- Add inline naming, save-current, update-from-current, rename, and delete-confirmation flows.
- Keep runtime-settings persistence health in the existing header. Show preset-library health and Retry locally in Presets mode, and add a separate `presetLibrary` object to `Panel.statusObject()`/IPC so the two failure domains are never collapsed into one ambiguous status.
- Add persistence warnings and recovery actions specific to the preset library.
- Add restart and external-edit behavior tests.

**Gate:** user presets survive restart, malformed edits are non-destructive, and built-ins remain immutable.

### Phase 5 — Author and validate the release catalogue

- Tune the candidate built-ins through live screenshots and performance runs.
- Remove weak or redundant presets rather than padding the catalogue.
- Document preset scope, paths, backup behavior, and recovery.
- Add release evidence only after the combined feature candidate is complete.

**Gate:** every shipping built-in has visual evidence, bounded performance, reduced-motion behavior, and accurate interface summaries.

## Explicit deferrals

Do not include these in the first preset release:

- hover-to-preview or temporary unsaved renderer overrides;
- screenshot thumbnails, which become inaccurate across themes;
- import/export, community sharing, remote catalogues, or downloaded code;
- search, tags, folders, favorites, or drag-reordering the preset library;
- schedules, random rotation, per-output presets, or automatic theme switching;
- fine-grained “apply only these fields” checklists;
- a separate general-purpose preset editor;
- full Scene presets that change presentation, opacity, reduced motion, vignette, or global enablement.

The architecture leaves room for these without making the first release depend on them.

## Definition of done

- Stack and effect presets have distinct, documented, test-enforced ownership.
- Built-ins are immutable, normalized, theme-portable, and independently authored.
- User presets live in a versioned library isolated from runtime settings.
- Applying either kind creates one normalized live document and one save intent.
- Stack apply preserves global preferences and inactive effect payloads.
- Effect apply preserves membership, order, and `enabled`.
- Unknown future data survives preset application and library round trips.
- Selection never applies; exact scope and stack diff are visible before apply.
- One-step runtime undo is keyboard reachable and persistence-aware.
- The Presets mode remains usable at 720×560 and does not crowd the existing header or effect actions.
- Runtime and preset-library persistence expose separate, accurate UI and IPC health states.
- Reset All explicitly keeps saved presets.
- Existing render, persistence, fullscreen, reduced-motion, Pause Preview, multi-output, and release checks remain green.
