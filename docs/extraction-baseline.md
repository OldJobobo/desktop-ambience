# Extraction Baseline

Recorded before Phase 1 of the standalone extraction.

## Source

- Repository: `/home/oldjobobo/Projects/lacuna-shell`
- Commit: `27c73022bcf6e24d8de471b25d321864704902d4`
- Commit subject: `Restore AUR installation guidance`
- Ambience source: `lacuna.ambience-host/`
- Vignette source: `lacuna.background-vignette/`
- Both source directories were clean at the pinned commit. The source worktree
  had unrelated changes outside those directories; they were not copied.

## Runtime revisions

- Omarchy: `4.0.0-1`
- Quickshell: `0.3.0`
- Quickshell revision: `28771c7c74b42e20afca0b1b63980cb46515537c`
- Quickshell package: `quickshell-git` (AUR)

## Baseline verification

Run from the Lacuna source repository:

```bash
python -m pytest -q \
  tests/test_qml_behavior_ambience_order.py \
  tests/test_qml_contracts.py::QmlContractTests::test_background_animations_use_single_selected_effect_contract \
  tests/test_qml_contracts.py::QmlContractTests::test_ambience_host_orders_siblings_and_suppresses_fallback_windows \
  tests/test_plugin_kind_contracts.py::PluginKindContractTests::test_ambience_host_is_bundle_renderer_not_a_standalone_surface
```

Result: `5 passed`.

The modified source test file only contained an unrelated tray submenu contract
change; the selected ambience and vignette test methods matched the pinned
commit.

The existing ambience live-visual test was also run against the pinned source:

```bash
LACUNA_LIVE_VISUAL=1 python -m pytest -q -rA \
  tests/test_live_visual.py::LiveVisualTests::test_ambience_reorder_changes_pixels_without_remapping_host_surfaces
```

Result: passed. The captured output is in
[`baseline/source-live-visual.txt`](baseline/source-live-visual.txt). The test
verified reorder pixel changes, stable host surfaces, background-to-foreground
mapping, and disable cleanup. The settings file SHA-256 was identical before
and after the test, confirming restoration.

The relevant pre-extraction settings snapshot is stored in
[`baseline/current-ambience-settings.json`](baseline/current-ambience-settings.json).
It intentionally contains only reduced-motion, ambience, and vignette state,
not unrelated personal shell configuration.

Phase 6 still requires release-level visual coverage across every effect and
monitor scenario. Phase 0 now has the source baseline evidence required to gate
the mechanical extraction.

## Phase 1 audit boundary

Behavior carried forward from the source host includes its per-output Bottom
and Overlay window trees, `FullscreenGuard`, production-stack bookkeeping,
ordered lazy loaders, and `status()` diagnostics. Their appearance in the
standalone host is copied behavior, although Phase 3 will replace the dual
window trees with one dynamically selected surface per output.

Standalone adaptations in Phase 1 are limited to the panel manifest/root,
`jobo` namespaces and IPC target, in-memory defaults pending Phase 2, removal of
the private frame bridge, hosting the vignette inside the selected ambience
surface, and one injected CRT foreground property. This distinction preserves
auditability between source behavior and new host-boundary work.
