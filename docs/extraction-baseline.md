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

Live visual evidence remains a Phase 6 release gate. Phase 1 preserves the
renderer sources without visual or performance rewrites.
