from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_settings_window_contains_only_standalone_animations_scope():
    window = read("components/SettingsWindow.qml")
    assert 'title: "Desktop Ambience"' in window
    assert 'text: "Compose the atmosphere"' in window
    assert "property var settings: null" in window
    assert 'import "../services/EffectRegistry.js" as EffectRegistry' in window
    assert "FileView" not in window
    for unrelated in (
        "Preferred Apps", "Media Player", "Desktop Clock", "Appearance",
        "Workspaces", "Restart Confirmation",
    ):
        assert unrelated not in window
    assert 'text: "Layout"' not in window


def test_global_stack_vignette_and_persistence_actions_are_owned_by_window():
    window = read("components/SettingsWindow.qml")
    for function_name in (
        "setEnabled", "setPresentation", "setOpacity", "setReduceMotion",
        "addEffect", "removeEffect", "moveEffect", "setEffectField",
        "setVignetteField", "retryPersistence", "resetAll",
    ):
        assert f"function {function_name}(" in window
    assert "settings.normalize(settings.data)" in window
    assert "settings.save(next)" in window
    assert "settings.retryPersistence()" in window
    assert 'if (key === "intensity") next.backgroundVignette.enabled = true' in window
    assert "commit(settings.defaultData())" in window
    assert "ACTIVE STACK · FRONT TO BACK" in window
    assert "ADD EFFECT" in window
    assert "DEDICATED VIGNETTE" in window
    assert "Place Behind Animations" in window
    assert "Confirm reset" in window


def test_effect_editor_is_driven_by_registry_metadata_for_every_field_type():
    window = read("components/SettingsWindow.qml")
    registry = read("services/EffectRegistry.js")
    assert "function fieldDefinitions(value)" in registry
    assert "function vignetteFieldDefinitions()" in registry
    assert "function fieldLabel(key)" in registry
    assert "function fieldHint(key)" in registry
    assert "function stepForField(field)" in registry
    assert 'model: EffectRegistry.fieldDefinitions(root.selectedEffectId)' in window
    assert 'modelData.type === "bool"' in window
    assert 'modelData.type === "enum"' in window
    assert "numericFieldComponent" in window
    assert "ToggleSwitch" in window
    assert "PanelSlider" in window
    assert "Dropdown" in window


def test_reset_and_controls_never_target_unrelated_configuration():
    window = read("components/SettingsWindow.qml")
    assert "shell.json" not in window
    assert "hypr" not in window.lower()
    assert "themes/" not in window
    assert "settings.settingsFile" not in window
    assert "defaultData()" in window
    assert "Reset restores ambience and launcher defaults." in window


def test_toggle_copy_reserves_space_for_the_switch():
    window = read("components/SettingsWindow.qml")
    assert "anchors.right: toggle.left" in window
    assert "anchors.right: toggle.right" not in window
