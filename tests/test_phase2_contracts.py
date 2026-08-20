import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILES = [
    ROOT / "manifest.json",
    ROOT / "Panel.qml",
    *sorted((ROOT / "components").glob("*.qml")),
    *sorted((ROOT / "effects").glob("*.qml")),
    *sorted((ROOT / "services").glob("*.qml")),
    *sorted((ROOT / "services").glob("*.js")),
]
ORDERED_EFFECTS = {
    "auroraDrift": "AuroraDriftEffect.qml",
    "cinematicLight": "CinematicLightEffect.qml",
    "crt": "CrtEffect.qml",
    "dustMotes": "DustMotesEffect.qml",
    "filmGrain": "FilmGrainEffect.qml",
    "godRays": "GodRaysEffect.qml",
    "rainfall": "RainfallEffect.qml",
    "tacticalGrid": "TacticalGridEffect.qml",
    "trackingLines": "VhsEffect.qml",
    "bokeh": "BokehEffect.qml",
}


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_panel_owns_one_settings_service_and_one_theme_adapter():
    panel = read("Panel.qml")
    assert panel.count("AmbienceSettings { id: ambienceSettings }") == 1
    assert panel.count("ThemeAdapter { id: themeAdapter }") == 1
    assert panel.count("settings: ambienceSettings") == 3  # settings window, order probe, production stack
    assert len(re.findall(r"^\s+theme: themeAdapter$", panel, re.MULTILINE)) == 2
    assert "readonly property bool ambienceEnabled: ambienceSettings.enabled" in panel
    assert "readonly property var activeEffects: ambienceSettings.activeEffects" in panel
    assert "persistenceState" in panel
    assert "retryAvailable" in panel
    assert "loadError: ambienceSettings.loadError" in panel
    assert "diskDiverged: ambienceSettings.diskDiverged" in panel
    assert "recoveredFromMalformedEdit: ambienceSettings.recoveredFromMalformedEdit" in panel


def test_stack_injects_normalized_state_without_duplicate_defaults():
    stack = read("components/AmbienceStack.qml")
    assert "property var settings: null" in stack
    assert "property var theme: null" in stack
    assert "function settingsFor(effectId)" in stack
    assert "defaultSettings" not in stack

    for effect_id in ORDERED_EFFECTS:
        assert f'effectSettings: root.settingsFor("{effect_id}")' in stack
    assert stack.count("globalOpacity: root.settings ? root.settings.opacity : 1") == 10
    assert stack.count("reducedMotion: root.settings ? root.settings.reduceMotion : false") == 10
    assert stack.count("theme: root.theme") == 8
    assert "foregroundOverlay: root.foregroundOverlay" in stack
    assert 'effectSettings: root.settingsFor("tacticalGrid")' in stack
    assert stack.count("targetScreen: root.targetScreen") == 2
    assert stack.count("cursorTracker: root.cursorTracker") == 2


def test_effects_have_only_injected_adapters_and_no_file_owners():
    for effect_id, filename in ORDERED_EFFECTS.items():
        effect = read(f"effects/{filename}")
        assert "property var effectSettings: ({})" in effect
        assert "property real globalOpacity: 1" in effect
        assert "property bool reducedMotion: false" in effect
        assert "overlaySettings.enabled === true" in effect
        assert "configuredEnabled && runtimeEnabled" in effect
        assert "* clamp(globalOpacity, 0, 1)" in effect
        adapter = effect.split("function parsePayload", 1)[0]
        assert "numberSetting" not in adapter
        assert "boolSetting" not in adapter
        assert "settingValue" not in adapter
        assert "normalizeStylePreset" not in adapter
        assert "normalizeOrigin" not in adapter
        assert "property string omarchyPath" not in effect
        assert "property var shell" not in effect
        assert "property var manifest" not in effect
        for line in adapter.splitlines():
            if "overlaySettings." not in line:
                continue
            assert "clamp(" not in line
            assert "Math.max(" not in line
            assert "Math.min(" not in line
            assert " ? " not in line
            assert " || " not in line
        assert "FileView" not in effect
        assert "defaultSettings" not in effect
        assert "pluginSettings" not in effect
        assert "backgroundEffect" not in effect
        assert "settingsFile" not in effect
        assert "colorsPath" not in effect
        assert "lacuna" not in effect.lower()
        if effect_id not in {"crt", "trackingLines"}:
            assert "property var theme: null" in effect


def test_dedicated_vignette_stays_separate_and_changes_sibling_z():
    panel = read("Panel.qml")
    stack = read("components/AmbienceStack.qml")
    vignette = read("effects/VignetteEffect.qml")
    registry = read("services/EffectRegistry.js")

    assert panel.count("settings: root.backgroundVignette") == 1
    assert panel.count("z: root.vignetteBehindEffects ? -10000 : 10000") == 1
    assert "ignoreBackgroundAnimationLayer" in vignette
    assert "backgroundVignette" not in stack
    ordered_block = registry.split("var orderedEffects = [", 1)[1].split("]", 1)[0]
    assert "backgroundVignette" not in ordered_block


def test_only_services_own_the_two_runtime_file_watchers():
    owners = []
    for path in RUNTIME_FILES:
        text = path.read_text(encoding="utf-8")
        if "FileView" in text:
            owners.append(path.relative_to(ROOT).as_posix())
    assert owners == ["services/AmbienceSettings.qml", "services/ThemeAdapter.qml"]
    assert read("services/AmbienceSettings.qml").count("property FileView") == 1
    assert read("services/ThemeAdapter.qml").count("property FileView") == 1


def test_runtime_has_no_forbidden_dependencies_or_external_absolute_imports():
    forbidden = re.compile(r"lacuna|/home/|Projects/|compatibility alias", re.IGNORECASE)
    for path in RUNTIME_FILES:
        text = path.read_text(encoding="utf-8")
        assert not forbidden.search(text), path
        for imported in re.findall(r'^import\s+"([^"]+)"', text, re.MULTILINE):
            resolved = (path.parent / imported).resolve()
            assert resolved == ROOT or ROOT in resolved.parents, (path, imported)
