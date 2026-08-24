# Desktop Ambience Final Polish Plan

Status: proposed execution plan for the path from the current pre-1.0 plugin to a flagship-quality Omarchy release

## Purpose

Desktop Ambience already has a strong technical foundation: centralized settings and effect metadata, atomic persistence, one persistent surface per output, lazy renderer loading, theme adaptation, fullscreen suppression, runtime health reporting, and unusually broad automated and live validation.

The remaining work is not primarily about adding renderers. It is about turning that depth into a coherent, comfortable, trustworthy product that is easy to understand, delightful to use, and compelling on `omarchyplugins.com`.

This plan therefore prioritizes:

1. repository and release truth;
2. a fast first-run success path;
3. a distinctive composition workflow;
4. accessibility and motion comfort;
5. visual and interaction refinement;
6. measurable runtime quality;
7. marketplace presentation and trust; and
8. a disciplined 1.0 release gate.

The target product position is an **ambient composition studio for Omarchy**: users begin with a coherent authored atmosphere, then reveal and tune the ordered effect stack as deeply as they want.

## Current Assessment

### Strengths to preserve

- One persistent ambience surface per output rather than one window per effect.
- Ordered front-to-back composition with lazy renderer ownership.
- Central effect defaults, fields, labels, bounds, enum values, and normalization.
- A sole runtime settings owner with serialized atomic writes, retry, and last-valid recovery.
- Shared theme and cursor services rather than renderer-local file or process ownership.
- Background and click-through foreground presentation.
- Per-output fullscreen suppression.
- Multi-output, lifecycle, theme-switch, visual, settings, and performance coverage.
- Runtime status exposing surfaces, loaded effects, persistence, theme, and cursor health.
- Pause Preview, persistence status, save retry, effect reset, and guarded full reset.

These are product assets. Final polish must simplify their presentation without weakening their contracts.

### Immediate repository risk

The current local worktree is based on `v0.6.0` and is eight commits behind `origin/main`, which contains `v0.7.0`. The local work overlaps upstream changes in core files including:

- `Panel.qml`;
- `components/AmbienceStack.qml`;
- `components/SettingsWindow.qml`;
- `services/EffectRegistry.js`;
- visual and performance harnesses; and
- settings, release, behavior, and load-smoke tests.

Upstream already includes Bokeh, Node Mesh, precipitation work, release evidence, and additional runtime fixes. Local work independently includes Bokeh and Drip. Continuing feature work before reconciliation risks duplicate implementations, lost fixes, stale tests, and misleading release evidence.

**No final-polish implementation begins until the worktree is reconciled with `origin/main`.**

## Product Principles

Every final-polish decision should follow these principles.

### Composition before configuration

Users should choose or audition an atmosphere before being asked to understand renderer settings. Advanced controls remain available but are not the first-run experience.

### Stack membership is visibility

The ordered stack is the primary model for whether an effect participates in the composition. Per-effect enablement must not contradict or obscure that model.

### Comfort is a contract

Reduced motion cannot mean “some animations happen more slowly.” Every effect must implement and document predictable Full, Reduced, and Still behavior.

### Technical truth is visible truth

Manifest version, README claims, preview media, release notes, generated evidence, tags, and marketplace verification must describe the same commit and product.

### Delight should be stable

Personality belongs in authored compositions, effect behavior, visual craft, and optional secondary copy. Primary control names and interaction rules must remain predictable.

### More effects are not the current success metric

No new renderer should displace presets, onboarding, accessibility, performance, or marketplace work. New effects resume only after the final-polish gates are satisfied.

## Phase 0 — Reconcile the Development Baseline

### Goal

Create one clean, current branch containing the intentional local work on top of `origin/main` without duplicating upstream features or regressing v0.7 behavior.

### Work

1. Preserve the current working tree in a recoverable branch or patch before integration.
2. Review all eight upstream commits and classify each overlapping local change as:
   - already upstream;
   - locally improved and worth replaying;
   - conflicting and requiring a new merged implementation; or
   - obsolete after upstream architecture changes.
3. Use `origin/main`/`v0.7.0` as the new baseline.
4. Port Drip as an isolated feature.
5. Drop the duplicate local Bokeh implementation unless it contains independently validated improvements not present upstream.
6. Reconcile the registry, active-effect normalization, stack loaders, status output, settings UI, visual cases, performance cases, and release tests as one coherent renderer inventory.
7. Preserve upstream Node Mesh, precipitation, lifecycle, focus-safety, and IPC fixes.
8. Run host-independent tests before any polish work.
9. Run focused live checks for every renderer whose integration changed during reconciliation.

### Gate

- The branch is based on current `origin/main`.
- No effect has two implementations, aliases, or competing defaults.
- README, registry, stack, smoke tests, and visual matrix agree on the renderer inventory.
- The full host-independent suite passes.
- Focused live checks show no regression in Bokeh, Node Mesh, precipitation, or Drip.
- No release evidence from an older version was overwritten.

## Phase 1 — Establish One Truthful Product Snapshot

### Goal

Prevent release metadata and evidence from describing different products.

### Work

1. Choose the next release version only after Phase 0 stabilizes.
2. Treat `manifest.json` as the canonical runtime version.
3. Add release assertions that compare:
   - manifest version;
   - changelog section;
   - release evidence document;
   - tag, when present;
   - current renderer inventory;
   - visual evidence inventory; and
   - marketplace preview version, if the preview contains visible version text.
4. Make tagged release evidence immutable:
   - refuse to write into an existing tagged release directory from a different commit;
   - refuse to write stable evidence when `HEAD`, manifest, and tag disagree; and
   - use an explicit candidate directory for unreleased runs.
5. Add a machine-readable renderer manifest to visual evidence so coverage is compared by stable effect ID rather than inferred filenames.
6. Ensure human-facing evidence labels use display names, not raw IDs such as `trackingLines` or `threeEffectStackThemeSwitch`.
7. Regenerate README claims, release notes, contact sheet, and preview only from the final candidate.

### Gate

- Manifest, changelog, README, release notes, preview, contact sheet, tag, and checked commit describe the same product.
- Every ordered renderer appears in smoke, behavior, visual, and performance inventory checks.
- Historical release evidence cannot be silently replaced.

## Phase 2 — Make the Stack the Signature Interaction

### Goal

Turn ordered composition into the plugin’s most memorable and usable feature.

### Interaction model

Use a numbered vertical **layer spine** representing the actual front-to-back order. Each row should communicate:

- position;
- effect name;
- current participation/visibility;
- selection;
- optional compact intensity state; and
- available reorder/remove actions.

### Work

1. Replace bare `MouseArea` stack selection and action controls with keyboard-capable controls or action-backed buttons.
2. Support:
   - pointer selection;
   - drag-and-drop reordering;
   - keyboard reorder alternatives;
   - Enter/Space activation;
   - remove with a reversible result action; and
   - visible focus throughout.
3. Use minimum 40–44 pixel action targets.
4. Give every action a contextual accessible name, for example:
   - “Move Rainfall toward front”;
   - “Move CRT toward back”; and
   - “Remove Bokeh from stack.”
5. Announce stack position, membership, selection, and disabled state.
6. Scroll focused rows and actions into view.
7. Preserve effect objects during reorder.
8. Add one-step undo for add, remove, and reorder.
9. Consider an optional temporary Solo/Audition action only if it can remain session-local and obvious.

### Tests

- Pointer reorder.
- Keyboard reorder.
- Enter/Space activation.
- Focus restoration after remove.
- Focus-follow scrolling.
- Accessible names and states.
- Reorder without effect recreation.
- Undo restores exact order and settings state.

### Gate

A user can create, select, reorder, remove, and restore a composition without a pointer, without losing focus, and without ambiguity about front/back order.

## Phase 3 — Resolve Membership and Enablement Semantics

### Goal

Ensure users always understand whether an effect is visible and why.

### Required model

- **Stack membership** determines whether an effect participates in composition.
- **Visible in stack** may temporarily suppress an in-stack effect without removing its position.
- Effects outside the stack retain settings but are not visible.

### Work

1. For an effect outside the stack, show:
   - “Saved settings · Not currently visible”; and
   - one primary **Add to stack** action.
2. Hide or disable the visibility toggle outside the stack.
3. Rename generic **Enabled** to **Visible in stack** when membership makes it meaningful.
4. Do not silently set `enabled = true` when editing another field.
5. Preserve settings for removed effects.
6. Add a clear result strip after membership changes:
   - “Bokeh added to position 3 · Undo”;
   - “Rainfall removed · Undo”; or
   - “CRT hidden in stack.”
7. Ensure presets follow the same semantics.
8. Document the distinction in README configuration guidance.

### Gate

No UI state can simultaneously imply that an effect is inactive and visibly enabled without explaining the distinction.

## Phase 4 — Curated Presets and First-Run Onboarding

### Goal

Let a first-time user reach an attractive, comfortable composition in under 30 seconds.

### Direction

Implement `docs/presets-plan.md` as the primary onboarding and repeat-use workflow, not as an advanced add-on.

### Built-in stack presets

Start with four to six carefully art-directed compositions, for example:

- **Quiet Orbit** — restrained Bokeh, subtle Dust Motes, gentle vignette.
- **Northern Veil** — Aurora Drift with soft God Rays.
- **Analog Afterimage** — Film Grain, CRT, and restrained VHS texture.
- **Rain Room** — precipitation, soft light, and edge treatment guidance.
- **Cathedral Light** — Cinematic Light and God Rays.
- **Tactical Glass** — low-opacity Tactical Grid with subtle supporting texture.

Names are candidates; final presets require visual authorship and performance validation.

### First-run flow

1. Explain the product in one sentence.
2. Present authored atmospheres with concise descriptions.
3. Let selection audition a preset live without immediately persisting it.
4. Provide **Use this composition** and **Keep current setup** actions.
5. Preserve global opacity, presentation, motion preference, and dedicated vignette unless the preset explicitly states otherwise.
6. After application, reveal the ordered layer spine and selected effect controls.
7. Never force onboarding after a valid existing settings document is found.

### Preset requirements

Preserve the existing preset plan’s key contracts:

- separate stack and effect presets;
- isolated `presets.json` ownership;
- atomic application through one runtime save;
- unknown-field preservation;
- deterministic normalization;
- one-step runtime undo;
- keyboard-complete catalogue and actions;
- clear application scope and diff; and
- separate runtime and preset-library persistence health.

### Default state

Replace VHS-only first-run state with either:

- the onboarding chooser before any preset is committed; or
- a restrained, low-cost, two-effect default if the shell requires immediate rendering.

The default must be visually pleasant, low motion, theme-portable, and safe on modest hardware.

### Gate

In an uncoached usability test, at least four of five new users can select, apply, understand, and later modify a composition within 30 seconds.

## Phase 5 — Motion Comfort and Accessibility Contract

### Goal

Make comfort behavior predictable across every renderer.

### Motion modes

Replace the binary reduced-motion promise with:

1. **Full motion**
   - complete authored animation behavior.
2. **Reduced motion**
   - slower drift;
   - no sharp pulses, flashes, glitch jumps, or aggressive tracking movement;
   - restrained pointer reaction;
   - stable spatial relationships where practical.
3. **Still**
   - static representative rendering;
   - animation timers stopped;
   - cursor sampling stopped;
   - no hidden background work.

### Registry metadata

Add effect-level motion metadata sufficient to describe:

- continuous drift;
- pulse/shimmer;
- glitch/flicker;
- pointer reaction;
- precipitation or repeated travel;
- reduced-mode behavior; and
- still-mode behavior.

Use this metadata for UI explanations and contract tests. Do not duplicate motion policy text in individual settings components.

### Accessibility work

1. Replace pointer-only controls.
2. Add visible focus to every interactive element.
3. Ensure meaningful tab order across header, global controls, stack, catalogue, details, and footer actions.
4. Wrap essential help text; do not rely on elided hints or hover-only tooltips.
5. Add accessible names, roles, checked/selected states, and contextual action descriptions.
6. Ensure focused items scroll into view.
7. Restore focus after add, remove, reset, preset apply, preset delete, and mode changes.
8. Keep stable primary control labels.
9. Validate minimum window size and scaled displays.

### Blood mode copy

Keep **Blood mode** as the stable control name. If rotating horror copy remains:

- render it as optional secondary flavor text;
- choose it at most once per window session;
- retain the practical explanatory hint; and
- include a concise content note where the feature is introduced.

### Gate

- Every workflow is keyboard-operable.
- Essential information remains readable without hover.
- Full, Reduced, and Still behavior is defined and tested for every effect.
- Still mode produces no renderer animation or cursor polling.

## Phase 6 — Settings Window Product Redesign

### Goal

Make the interface feel like a composition tool rather than a uniformly dense settings matrix.

### Proposed hierarchy

#### Header

- Product name and concise purpose.
- Persistence health only when useful.
- Pause/Resume Preview.
- Close.

Move Donate to About/Support so it does not compete with primary work.

#### Persistent global strip

- Ambience on/off.
- Background/foreground presentation.
- Global opacity.
- Full/Reduced/Still motion.

#### Workspace switch

- **Compose**
- **Presets**

Place this below the header divider, matching the preset plan.

#### Compose workspace

- Left: ordered layer spine and Add Effect catalogue.
- Right: selected effect identity, membership action, reset, preset shortcut, and controls.

#### Secondary plugin settings

Move these away from composition:

- bar icon;
- dedicated vignette/edge treatment, unless design testing shows it belongs in Compose;
- support/about;
- diagnostics shortcut; and
- full reset.

### Visual refinement

1. Reduce nested border density.
2. Use spacing, headings, and grouped surfaces to establish hierarchy.
3. Reserve accent borders for selection, focus, warnings, and actionable state.
4. Increase contrast for secondary copy where the current theme treatment becomes too faint.
5. Avoid presenting every field as equal importance; group advanced controls where appropriate.
6. Keep the selected effect’s most meaningful controls visible before secondary tuning.
7. Use responsive widths rather than optimizing only for the 920×760 target.
8. Verify 720×560 minimum size, fractional scale, and long translated-like labels even if localization is not yet shipped.

### Gate

Five-second inspection tells a user:

- whether ambience is active;
- which composition or effects are active;
- which effect is selected;
- where to add/reorder effects; and
- how to pause the preview.

## Phase 7 — Runtime Performance and Frame-Pacing Quality

### Goal

Turn the existing strong performance harness into explicit product-quality budgets without sacrificing visual character.

### Work

1. Re-establish baselines after repository reconciliation.
2. Measure every effect and representative preset at:
   - one output;
   - three outputs;
   - reduced motion; and
   - still mode.
3. Record:
   - process CPU;
   - RSS;
   - frame callback cadence;
   - frame-time percentiles where observable;
   - active object/delegate counts;
   - timer/process launch counts; and
   - hidden/suppressed work.
4. Separate cold-start, transition, and steady-state measurements.
5. Define hardware-relative release budgets only after repeated baseline data exists.
6. Prioritize the highest measured renderer cost rather than the newest effect.
7. Keep each renderer optimization isolated and visually reviewable.
8. Require visual parity or an explicitly approved visual improvement.
9. Ensure:
   - removed effects unload;
   - zero-opacity effects do no unnecessary work;
   - fullscreen-suppressed foreground surfaces suspend renderer work;
   - Pause Preview stops renderer work and cursor sampling;
   - Reduced mode eliminates disallowed motion; and
   - Still mode is genuinely idle.
10. Add representative preset performance cases so preset authors cannot accidentally create pathological defaults.

### Gate

- No hidden, paused, still, or fully suppressed composition performs animation or polling work.
- No default or built-in preset exceeds the approved repeated steady-state budget.
- Multi-output cost scales within documented expectations.
- Performance results are repeatable enough to distinguish real improvements from sample noise.

## Phase 8 — Marketplace and README Presentation

### Goal

Communicate the outcome users want, not merely the settings machinery.

### Positioning

Recommended short marketplace direction:

> Layer theme-aware auroras, rain, light, grain, CRT and VHS texture across every Omarchy display.

Recommended README opening direction:

> Compose a desktop atmosphere that moves with your Omarchy theme. Start from an authored composition, then layer and tune effects from subtle light and dust to rain, CRT and VHS texture.

Final wording must reflect the released renderer count and must not advertise presets before they ship.

### Root preview

Replace the stale portrait settings image with a current 16:9 hero showing:

- a real Omarchy desktop;
- a restrained, legible composition;
- visible theme integration;
- enough context to understand that the effect spans the desktop; and
- no stale version text.

### README media set

1. Hero desktop composition.
2. Composer crop showing the ordered stack.
3. Theme adaptation comparison.
4. Human-labelled effect sampler.
5. Short optimized video or GIF applying a preset and showing the result.

Release contact sheets remain QA evidence and should not substitute for promotional media.

### README structure

1. Outcome-led headline and hero.
2. Three concise benefits:
   - authored compositions and ordered layers;
   - theme-aware, multi-output behavior;
   - comfort and performance controls.
3. Install command.
4. Quick start.
5. Preset/composition showcase.
6. Effect overview.
7. Configuration and ownership details.
8. Troubleshooting.
9. Development and release evidence.
10. License and support.

### Marketplace trust and metadata

1. Submit the final stable commit for marketplace verification.
2. Avoid pushing another release commit until verification is processed, or verify the newer SHA.
3. Resolve the listing’s “See repository” license projection through supported marketplace metadata or a maintainer refresh.
4. Add GitHub topics such as:
   - `omarchy`;
   - `omarchy-plugin`;
   - `quickshell`;
   - `desktop-effects`;
   - `hyprland`; and
   - `wayland`.
5. Set the GitHub repository homepage to the marketplace detail page.
6. Request benefit-oriented marketplace tags if supported.
7. Publish a concise release clip in relevant Omarchy community channels.
8. Ask for GitHub stars or marketplace hearts only after successful use, not during first-run setup.

### Measurement

Capture a baseline before the presentation update, then review at fixed intervals:

- marketplace views;
- install-command copies;
- hearts;
- copy/view rate;
- GitHub stars;
- issues by installation versus product-use category; and
- repeat user feedback about presets, comfort, and performance.

Marketplace interactions are directional signals, not verified installs or retention.

### Gate

- Preview, copy, version, and verified commit are current.
- The listing demonstrates the visual outcome before showing controls.
- README quick start produces an attractive result without requiring manual JSON editing.

## Phase 9 — Release Hardening and 1.0 Gate

### Goal

Ship a stable public contract rather than using 1.0 as a cosmetic milestone.

### Required validation

#### Installation and ownership

- Clean install from the public Git URL.
- Enable and correct bar placement.
- Settings and optional menu launchers open the same owner.
- Update from the previous two stable releases.
- Disable/re-enable without duplicate surfaces.
- Uninstall removes only plugin-owned integration.
- Optional state cleanup is documented and exact.

#### Runtime

- One and multiple outputs.
- Mixed resolution, scale, orientation, and refresh rate.
- Monitor add/remove.
- Theme replacement and malformed theme retry.
- Background and foreground presentation.
- Real and fake fullscreen.
- Shell restart and plugin rescan.
- Settings corruption and interrupted-save recovery.
- Preset-library corruption and interrupted-save recovery.
- Pause, Reduced, and Still behavior.

#### Visual

- Every effect alone.
- Every built-in stack preset.
- Dedicated vignette above and below the stack.
- Theme adaptation across at least two contrasting themes.
- Minimum window size and fractional scaling.
- Promotional media generated from the same release candidate.

#### Accessibility

- Complete keyboard walkthrough.
- Visible focus.
- Focus-follow scrolling.
- Accessible action names and state.
- No essential hover-only information.
- Motion-mode behavior for every renderer.

#### Performance

- Per-effect and per-preset repeated measurements.
- One and three outputs.
- Hidden, fullscreen-suppressed, paused, Reduced, and Still cases.
- No polling multiplication by output count.
- No default preset exceeding approved budgets.

### 1.0 acceptance criteria

Desktop Ambience reaches 1.0 only when:

- the repository baseline is current and clean;
- all release surfaces describe the same commit;
- a new user can reach an attractive result within 30 seconds;
- presets provide a coherent first-run and repeat-use workflow;
- the ordered layer spine is clear, memorable, and fully keyboard-operable;
- stack membership and visibility cannot contradict each other;
- Full, Reduced, and Still motion behavior is defined for every effect;
- paused, still, hidden, and fully suppressed renderers are idle;
- every built-in preset passes visual and performance gates;
- install, update, disable, restart, and removal are reliable;
- the marketplace preview and copy demonstrate the result rather than only the controls;
- the final marketplace commit is verified; and
- five uncoached usability participants can complete the primary workflow with no critical failure.

## Recommended Execution Order

1. Reconcile the local worktree with `origin/main`.
2. Complete Drip as an isolated addition without duplicating upstream Bokeh.
3. Establish release/evidence consistency guards.
4. Fix stack keyboard access and visibility semantics.
5. Implement curated stack presets and first-run onboarding.
6. Define and implement Full, Reduced, and Still motion.
7. Redesign settings hierarchy around Compose and Presets.
8. Rebaseline and optimize runtime performance.
9. Produce current promotional media and benefit-led copy.
10. Run the complete 1.0 matrix and submit the final commit for marketplace verification.

## Deliberate Non-Goals During Final Polish

Until the 1.0 gates are met, do not prioritize:

- additional renderers beyond already approved/in-progress work;
- per-output compositions;
- schedules or automatic preset rotation;
- theme switching owned by this plugin;
- a general-purpose preset editor;
- search, folders, tags, or favorites inside the preset catalogue;
- architectural rewrites without measured runtime need; or
- promotional claims not backed by the current release candidate.

## Success Measures

Final polish is successful when the plugin is not merely feature-rich, but demonstrably:

- **Immediate:** a beautiful result in under 30 seconds.
- **Understandable:** users can explain stack order and visibility after first use.
- **Comfortable:** motion behavior is predictable and controllable.
- **Accessible:** the full workflow works without a pointer.
- **Efficient:** inactive work is truly idle and built-in compositions meet measured budgets.
- **Trustworthy:** code, evidence, documentation, preview, version, and verification agree.
- **Distinctive:** the authored compositions and ordered layer spine are recognizable as Desktop Ambience.
- **Compelling:** the marketplace listing shows why someone wants the plugin before explaining how it is built.
