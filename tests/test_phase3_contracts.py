from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_one_registered_dynamic_surface_per_output_contract():
    panel = read("Panel.qml")
    assert panel.count("Variants {") == 1
    assert panel.count("PanelWindow {") == 1
    assert panel.count('objectName: "joboDesktopAmbienceSurface"') == 1
    assert 'model: Quickshell.screens' in panel
    assert 'screen: modelData' in panel
    assert 'WlrLayershell.namespace: "jobo-desktop-ambience"' in panel
    assert 'WlrLayershell.layer: root.foregroundOverlay ? WlrLayer.Overlay : WlrLayer.Bottom' in panel
    assert 'visible: root.visualSurfaceEnabled && !remapGuard.remapping' in panel
    assert "ScreenMoveRemap {" in panel
    assert "registerProductionSurface(this)" in panel
    assert "unregisterProductionSurface(this)" in panel
    assert "productionSurfaces = next" in panel


def test_ambience_surface_is_click_through_nonexclusive_and_suppresses_paint_only():
    panel = read("Panel.qml")
    assert panel.count("mask: Region {}") == 1
    assert panel.count("WlrLayershell.keyboardFocus: WlrKeyboardFocus.None") == 1
    assert panel.count("exclusionMode: ExclusionMode.Ignore") == 1
    assert "readonly property bool fullscreenSuppressed: root.foregroundOverlay" in panel
    assert "&& fullscreenGuard.activeOnScreen(modelData)" in panel
    assert "readonly property bool paintAllowed: visible && !fullscreenSuppressed" in panel
    assert panel.count("paintEnabled: ambienceSurface.paintAllowed") == 2
    assert "productionEffectsEnabled: root.ambienceEnabled" in panel
    assert "updatesEnabled: true" in panel


def test_settings_window_is_one_persistent_on_demand_floating_window():
    panel = read("Panel.qml")
    window = read("components/SettingsWindow.qml")
    assert panel.count("SettingsWindow {") == 1
    assert "readonly property bool opened: settingsWindow.opened" in panel
    assert "settingsWindow.open(payloadJson)" in panel
    assert "settingsWindow.close()" in panel
    assert window.count("FloatingWindow {") == 1
    assert "visible: false" in window
    assert "property bool closingFromHost" in window
    assert 'shell.hide(pluginId)' in window
    assert 'shell.hide(root.pluginId)' in window


def test_fullscreen_guard_has_testable_backend_and_per_output_resolution():
    guard = read("components/FullscreenGuard.qml")
    assert "property var backend: Hyprland" in guard
    assert "service.monitorFor(screen)" in guard
    assert "monitor.activeWorkspace" in guard
    assert "function activeOnScreen(screen)" in guard
    assert guard.count("ignoreUnknownSignals: true") == 2


def test_status_reports_actual_surface_and_persistence_health():
    panel = read("Panel.qml")
    assert "function statusObject()" in panel
    assert "function statusJson()" in panel
    assert "mappedSurfaceCount: root.mappedSurfaceCount()" in panel
    assert "surfaceCount: root.productionSurfaces.length" in panel
    assert "expectedSurfaceCount: Quickshell.screens.length" in panel
    assert "surfaces: root.surfaceStatus()" in panel
    assert "fullscreenSuppressed: surface.fullscreenSuppressed" in panel
    assert "settingsOpened: root.opened" in panel
    assert "healthy: ambienceSettings.persistenceReady" in panel
    assert "return root.statusJson()" in panel
