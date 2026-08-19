import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_manifest_uses_persistent_panel_boundary():
    manifest = json.loads(read("manifest.json"))
    assert manifest["id"] == "jobo.desktop-ambience"
    assert manifest["kinds"] == ["panel", "bar-widget"]
    assert manifest["keepLoaded"] is True
    assert manifest["entryPoints"] == {"panel": "Panel.qml", "barWidget": "BarWidget.qml"}
    assert "lacuna" not in manifest


def test_phase3_host_owns_one_dynamic_surface_per_output():
    panel = read("Panel.qml")
    assert 'target: "jobo-desktop-ambience"' in panel
    assert panel.count("Variants {") == 1
    assert panel.count("PanelWindow {") == 1
    assert panel.count("AmbienceStack {") == 2  # one order probe plus one production stack
    assert panel.count("VignetteEffect {") == 1
    assert 'WlrLayershell.namespace: "jobo-desktop-ambience"' in panel
    assert panel.count("mask: Region {}") == 1
    assert panel.count("WlrLayershell.keyboardFocus: WlrKeyboardFocus.None") == 1
    assert panel.count("exclusionMode: ExclusionMode.Ignore") == 1
    assert "root.foregroundOverlay ? WlrLayer.Overlay : WlrLayer.Bottom" in panel
    assert "fullscreenGuard.activeOnScreen(modelData)" in panel
    assert "ScreenMoveRemap {" in panel
    assert "paintEnabled: ambienceSurface.paintAllowed" in panel
    assert "productionEffectsEnabled: root.ambienceEnabled" in panel
    assert "ForegroundFrameBorder" not in panel
    assert "foregroundFrameSource" not in panel
    assert not re.search(r"(?:/omarchy/lacuna|lacuna\.|lacuna-|lacunaState)", panel)


def test_vignette_maps_independently_without_enabling_ambience_paint():
    panel = read("Panel.qml")
    assert "readonly property bool visualSurfaceEnabled: ambienceEnabled || vignetteEnabled" in panel
    assert "readonly property string mappingMode: !visualSurfaceEnabled" in panel
    assert "productionEffectsEnabled: root.ambienceEnabled" in panel
    assert "settings: root.backgroundVignette" in panel
    assert panel.count("paintEnabled: ambienceSurface.paintAllowed") == 2


def test_vignette_is_a_hosted_full_output_renderer():
    vignette = read("effects/VignetteEffect.qml")
    assert "PanelWindow" not in vignette
    assert "Variants" not in vignette
    assert "FileView" not in vignette
    assert "IpcHandler" not in vignette
    assert "frameGeometry" not in vignette
    assert 'source: Qt.resolvedUrl("../assets/vignette.svg")' in vignette
    assert "sourceSize.width:" in vignette
    assert "sourceSize.height:" in vignette
    assert "fillMode: Image.Stretch" in vignette
    assert "asynchronous: true" in vignette
    assert "cache: true" in vignette
    assert "vignetteEnabled" in vignette
    assert "vignetteIntensity" in vignette
    assert "paintEnabled" in vignette

    asset = read("assets/vignette.svg")
    assert 'id="left-edge"' in asset
    assert 'id="right-edge"' in asset


def test_crt_foreground_mode_is_injected_from_the_host():
    panel = read("Panel.qml")
    stack = read("components/AmbienceStack.qml")
    crt = read("effects/CrtEffect.qml")

    assert panel.count("foregroundOverlay: root.foregroundOverlay") == 1
    assert "property bool foregroundOverlay: false" in stack
    assert "foregroundOverlay: root.foregroundOverlay" in stack
    assert "property bool foregroundOverlay: false" in crt
    assert "readonly property bool foregroundOverlay: backgroundForegroundOverlayEnabled()" not in crt
    assert "visible: root.foregroundOverlay && root.distortion" in crt


def test_registry_separates_ordered_effects_from_dedicated_vignette():
    registry = read("services/EffectRegistry.js")
    stack = read("components/AmbienceStack.qml")
    plan = read("PLAN.md")
    expected = [
        ("auroraDrift", "auroraDriftLoader"),
        ("cinematicLight", "cinematicLightLoader"),
        ("crt", "crtLoader"),
        ("dustMotes", "dustMotesLoader"),
        ("filmGrain", "filmGrainLoader"),
        ("godRays", "godRaysLoader"),
        ("rainfall", "rainfallLoader"),
        ("trackingLines", "vhsLoader"),
    ]

    for effect_id, loader_id in expected:
        assert f'"{effect_id}"' in stack
        assert f'id: {loader_id}' in stack
        assert f'root.productionEffectActive("{effect_id}")' in stack
        assert f'id: "{effect_id}"' in registry

    assert "var orderedEffects = [" in registry
    assert 'id: "trackingLines", label: "VHS",' in registry
    assert '{ id: "vhs", label: "VHS" }' not in registry
    assert "var dedicatedVignette = {" in registry
    assert 'id: "backgroundVignette"' in registry
    ordered_block = registry.split("var orderedEffects = [", 1)[1].split("]", 1)[0]
    assert "backgroundVignette" not in ordered_block
    assert 'VHS (`trackingLines`)' in plan
    assert '"activeEffects": ["trackingLines"]' in plan
    assert '"activeEffects": ["vhs"]' not in plan
