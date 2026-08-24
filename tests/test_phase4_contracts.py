from pathlib import Path
import re


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


def test_blood_mode_uses_randomized_non_repeating_toggle_copy():
    registry = read("services/EffectRegistry.js")
    window = read("components/SettingsWindow.qml")
    assert 'bloodMode: boolField(false)' in registry
    assert '"There Will Be Blood"' in window
    assert '"Blood for the Blood God!"' in window
    assert '"Fangs Out!"' in window
    assert '"If It Bleeds, We Can Kill It!"' in window
    assert "function refreshBloodModeLabel()" in window
    assert 'key === "bloodMode"' in window
    assert "fieldLabelFor(root.selectedEffectId, parent.modelData)" in window
    assert "fieldHintFor(root.selectedEffectId, parent.modelData)" in window
    assert 'visible: text !== ""' in window


def test_header_shows_manifest_version_and_offers_verified_support_link():
    panel = read("Panel.qml")
    window = read("components/SettingsWindow.qml")
    assert 'readonly property string pluginVersion: String(root.manifest && root.manifest.version || "")' in panel
    assert "pluginVersion: root.pluginVersion" in panel
    assert "version: root.pluginVersion" in panel
    assert 'property string pluginVersion: ""' in window
    assert 'readonly property url donationUrl: "https://ko-fi.com/oldjobobo"' in window
    assert 'text: "Donate"' in window
    assert 'tooltipText: "Support OldJobobo on Ko-fi"' in window
    assert "Qt.openUrlExternally(donationUrl)" in window


def test_global_stack_vignette_and_persistence_actions_are_owned_by_window():
    window = read("components/SettingsWindow.qml")
    for function_name in (
        "setEnabled", "setPresentation", "setOpacity", "setReduceMotion",
        "addEffect", "removeEffect", "moveEffect", "setEffectField", "resetEffect",
        "setVignetteField", "setPreviewPaused", "retryPersistence", "resetAll",
    ):
        assert f"function {function_name}(" in window
    assert "settings.normalize(settings.data)" in window
    assert "settings.save(next)" in window
    assert "settings.retryPersistence()" in window
    assert 'text: "Reset effect"' in window
    assert 'text: root.previewPaused ? "Resume preview" : "Pause preview"' in window
    assert 'if (key === "intensity") next.backgroundVignette.enabled = true' in window
    assert "commit(settings.defaultData())" in window
    assert "ACTIVE STACK · FRONT TO BACK" in window
    assert 'text: "AVAILABLE  " + root.availableEffectCount' in window
    assert "DEDICATED VIGNETTE" in window
    assert "Place Behind Animations" in window
    assert "Confirm reset" in window


def test_every_effect_setting_has_a_specific_description():
    registry = read("services/EffectRegistry.js")
    schema = registry.split("var fieldLabels", 1)[0]
    hints = registry.split("var fieldHints = {", 1)[1].split("\n}", 1)[0]
    field_keys = set(re.findall(r"(\w+): (?:bool|real|int|enum)Field\(", schema))
    hint_keys = set(re.findall(r'^  (\w+): "', hints, re.MULTILINE))
    assert field_keys <= hint_keys
    for vague in (
        "Controls how many source elements are rendered.",
        "Controls the renderer's source geometry.",
        "Tunes this part of the visual treatment.",
        "Adjusts the source renderer setting.",
    ):
        assert vague not in hints


def test_enum_metadata_separates_persisted_values_from_labels():
    registry = read("services/EffectRegistry.js")
    window = read("components/SettingsWindow.qml")
    assert "function enumOptionLabel(value)" in registry
    assert "field.options = enumOptions(field)" in registry
    assert 'lightLeak: "Light leak"' in registry
    assert "options: parent.modelData.options || parent.modelData.values" in window


def test_effect_editor_is_driven_by_registry_metadata_for_every_field_type():
    window = read("components/SettingsWindow.qml")
    registry = read("services/EffectRegistry.js")
    assert "function fieldDefinitions(value)" in registry
    assert "function vignetteFieldDefinitions()" in registry
    assert "function fieldLabel(key, effectId)" in registry
    assert "function fieldHint(key, effectId)" in registry
    assert "function stepForField(field)" in registry
    assert 'model: EffectRegistry.fieldDefinitions(root.selectedEffectId)' in window
    assert 'modelData.type === "bool"' in window
    assert 'modelData.type === "enum"' in window
    assert "numericFieldComponent" in window
    assert "ToggleSwitch" in window
    assert "DragOnlySlider" in window
    assert "Dropdown" in window


def test_slider_wheel_input_scrolls_the_panel_without_changing_values():
    window = read("components/SettingsWindow.qml")
    drag_only = read("components/DragOnlySlider.qml")
    slider = window.split("component SliderSetting:", 1)[1].split("component EnumSetting:", 1)[0]
    assert "property var scrollTarget: null" in slider
    assert "function forwardWheel(pixelDeltaY, angleDeltaY)" in slider
    assert "scrollTarget.contentY" in slider
    assert "DragOnlySlider {" in slider
    assert "onWheelScrolled: function(pixelDeltaY, angleDeltaY)" in slider
    assert "sliderRow.forwardWheel(pixelDeltaY, angleDeltaY)" in slider
    assert "function snapValue(candidate)" in drag_only
    assert "Math.round((snapped - minimum) / configuredStep) * configuredStep" in drag_only
    assert "return root.snapValue(raw)" in drag_only
    wheel_handler = drag_only.split("onWheel: function(wheel)", 1)[1]
    assert "root.wheelScrolled(wheel.pixelDelta.y, wheel.angleDelta.y)" in wheel_handler
    assert "wheel.accepted = true" in wheel_handler
    assert "root.liveValue" not in wheel_handler
    assert "root.moved" not in wheel_handler
    assert "root.released" not in wheel_handler
    assert "scrollTarget: compositionFlickable" in window
    assert window.count("scrollTarget: detailFlickable") == 2


def test_reset_and_controls_never_target_unrelated_configuration():
    window = read("components/SettingsWindow.qml")
    assert "shell.json" not in window
    assert "hypr" not in window.lower()
    assert "themes/" not in window
    assert "settings.settingsFile" not in window
    assert "defaultData()" in window
    assert "Reset restores ambience and launcher defaults." in window


def test_selected_available_effect_uses_the_button_selection_color():
    window = read("components/SettingsWindow.qml")
    available_effects = window.split('text: "AVAILABLE  " + root.availableEffectCount', 1)[1].split("id: iconFooter", 1)[0]
    assert "selected: root.selectedEffectId === modelData.id" in available_effects


def test_selected_stack_row_uses_one_outer_selection_surface():
    window = read("components/SettingsWindow.qml")
    stack_row = window.split("component EffectStackRow:", 1)[1]
    assert 'selected ? "selected" : rowHover.hovered ? "hover-cursor" : "normal"' in stack_row
    assert "rowHover.hovered ? Style.hoverFillFor" in stack_row
    assert "Behavior on color { ColorAnimation { duration: 120 } }" in stack_row
    assert "selected: stackRow.selected" not in stack_row
    assert "Style.selectedStateColor(Color.foreground, Color.accent)" in stack_row
    assert "onClicked: stackRow.selectedEffect()" in stack_row
    assert "component StackAction: Item" in window
    assert "StackAction {" in stack_row


def test_toggle_copy_reserves_space_for_the_switch():
    window = read("components/SettingsWindow.qml")
    assert "anchors.right: toggle.left" in window
    assert "anchors.right: toggle.right" not in window
