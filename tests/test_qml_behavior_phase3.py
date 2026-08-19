from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from qml_harness import HAVE_SESSION, parse_behave, qml_url, require_no_qml_errors, run_quickshell


@unittest.skipUnless(HAVE_SESSION, "needs a quickshell binary and a Wayland session")
class Phase3BehaviorTests(unittest.TestCase):
    def test_fullscreen_guard_resolves_each_output_independently(self):
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  QtObject {{ id: screenA }}
  QtObject {{ id: screenB }}
  QtObject {{ id: workspaceA; property bool hasFullscreen: true; property var lastIpcObject: ({{}}) }}
  QtObject {{ id: workspaceB; property bool hasFullscreen: false; property var lastIpcObject: ({{fullscreen: 0}}) }}
  QtObject {{ id: monitorA; property var activeWorkspace: workspaceA }}
  QtObject {{ id: monitorB; property var activeWorkspace: workspaceB }}
  QtObject {{
    id: fakeBackend
    property var focusedWorkspace: workspaceB
    property var workspaces: null
    function monitorFor(screen) {{ return screen === screenA ? monitorA : (screen === screenB ? monitorB : null) }}
  }}
  Loader {{
    id: guardLoader
    source: "{qml_url('components/FullscreenGuard.qml')}"
    onLoaded: {{ item.backend = fakeBackend; probe.start() }}
  }}
  Timer {{
    id: probe; interval: 50
    onTriggered: {{
      var guard = guardLoader.item
      var first = guard.activeOnScreen(screenA)
      var second = guard.activeOnScreen(screenB)
      workspaceA.hasFullscreen = false
      workspaceA.lastIpcObject = {{hasfullscreen: true}}
      var legacy = guard.activeOnScreen(screenA)
      console.log("BEHAVE " + JSON.stringify({{first: first, second: second, legacy: legacy,
        focusedFallback: guard.activeOnScreen(null)}}))
      Qt.quit()
    }}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as config_home:
            output = run_quickshell(qml, config_home=Path(config_home), timeout=10)
        require_no_qml_errors(output)
        row = parse_behave(output)[-1]
        self.assertTrue(row["first"], output[-2000:])
        self.assertFalse(row["second"], output[-2000:])
        self.assertTrue(row["legacy"], output[-2000:])
        self.assertFalse(row["focusedFallback"], output[-2000:])

    def test_settings_window_open_close_and_user_close_are_synchronized(self):
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  property int stage: 0
  property bool openedOnce: false
  property bool hostCloseStayedSilent: false
  QtObject {{
    id: fakeShell
    property int hideCalls: 0
    property string hiddenId: ""
    function hide(pluginId) {{ hideCalls += 1; hiddenId = pluginId; windowLoader.item.close() }}
  }}
  Loader {{
    id: windowLoader
    source: "{qml_url('components/SettingsWindow.qml')}"
    onLoaded: {{ item.shell = fakeShell; probe.start() }}
  }}
  Timer {{
    id: probe; interval: 60; repeat: true
    onTriggered: {{
      var window = windowLoader.item
      if (stage === 0) {{ window.open("{{}}"); stage = 1 }}
      else if (stage === 1 && window.opened) {{
        openedOnce = true
        window.close()
        stage = 2
      }} else if (stage === 2 && !window.opened) {{
        hostCloseStayedSilent = fakeShell.hideCalls === 0
        window.open("{{}}"); stage = 3
      }} else if (stage === 3 && window.opened) {{
        window.requestClose(); stage = 4
      }} else if (stage === 4 && !window.opened) {{
        stop()
        console.log("BEHAVE " + JSON.stringify({{openedOnce: openedOnce,
          hostCloseStayedSilent: hostCloseStayedSilent, hideCalls: fakeShell.hideCalls,
          hiddenId: fakeShell.hiddenId, opened: window.opened}}))
        Qt.quit()
      }}
    }}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as config_home:
            output = run_quickshell(qml, config_home=Path(config_home), timeout=10)
        require_no_qml_errors(output)
        row = parse_behave(output)[-1]
        self.assertTrue(row["openedOnce"], output[-2000:])
        self.assertTrue(row["hostCloseStayedSilent"], output[-2000:])
        self.assertEqual(row["hideCalls"], 1, output[-2000:])
        self.assertEqual(row["hiddenId"], "jobo.desktop-ambience", output[-2000:])
        self.assertFalse(row["opened"], output[-2000:])

    def test_presentation_switch_keeps_one_surface_and_renderer_tree_per_output(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as state_dir:
            config_home = Path(config_dir)
            settings_file = config_home / "omarchy/jobo/desktop-ambience/settings.json"
            settings_file.parent.mkdir(parents=True)
            settings_file.write_text(
                json.dumps({
                    "version": 1,
                    "enabled": True,
                    "presentation": "background",
                    "activeEffects": ["trackingLines"],
                    "effects": {"trackingLines": {"enabled": True, "intensity": 0}},
                    "backgroundVignette": {"enabled": False},
                }),
                encoding="utf-8",
            )
            state_home = Path(state_dir)
            palette = state_home / "omarchy/current/theme/colors.toml"
            palette.parent.mkdir(parents=True)
            palette.write_text('color11 = "#aabbcc"\ncolor15 = "#ffffff"\n', encoding="utf-8")
            qml = f'''
import Quickshell
import Quickshell.Wayland
import QtQuick
ShellRoot {{
  property int stage: 0
  property var surfaces: []
  property var stacks: []
  property var effects: []
  property bool modeIdentityStable: true
  property bool disabledIdentityStable: true
  property bool suppressionObserved: false
  property var suppressedScreen: null
  QtObject {{ id: fullscreenWorkspace; property bool hasFullscreen: false; property var lastIpcObject: ({{}}) }}
  QtObject {{ id: fullscreenMonitor; property var activeWorkspace: fullscreenWorkspace }}
  QtObject {{
    id: fakeFullscreenBackend
    property var focusedWorkspace: null
    property var workspaces: null
    function monitorFor(screen) {{ return screen === suppressedScreen ? fullscreenMonitor : null }}
  }}
  Loader {{ id: panelLoader; source: "{qml_url('Panel.qml')}"; onLoaded: probe.start() }}

  function capture(panel) {{
    surfaces = []; stacks = []; effects = []
    for (var i = 0; i < panel.productionSurfaces.length; i++) {{
      var surface = panel.surfaceAt(i)
      surfaces.push(surface)
      stacks.push(surface.stackObject)
      effects.push(surface.stackObject.productionEffectObject("trackingLines"))
    }}
  }}

  function identitiesMatch(panel, includeEffect) {{
    if (panel.productionSurfaces.length !== surfaces.length) return false
    for (var i = 0; i < surfaces.length; i++) {{
      var surface = panel.surfaceAt(i)
      if (surface !== surfaces[i] || surface.stackObject !== stacks[i]) return false
      if (includeEffect && surface.stackObject.productionEffectObject("trackingLines") !== effects[i]) return false
    }}
    return true
  }}

  function saveField(panel, name, value) {{
    var next = panel.settingsService.normalize(panel.settingsService.data)
    next[name] = value
    panel.settingsService.save(next)
  }}

  Timer {{
    id: probe; interval: 40; repeat: true; property int attempts: 0
    onTriggered: {{
      attempts += 1
      var panel = panelLoader.item
      if (!panel || !panel.settingsService.hasLoaded) return
      var expected = Quickshell.screens.length
      if (stage === 0 && panel.productionSurfaces.length === expected
          && panel.mappedSurfaceCount() === expected && panel.loadedEffectCount() === expected) {{
        panel.registerProductionSurface(panel.surfaceAt(0))
        if (panel.productionSurfaces.length !== expected) {{
          console.log("BEHAVE_ERR duplicate surface registration was accepted")
          Qt.quit()
          return
        }}
        capture(panel)
        suppressedScreen = panel.surfaceAt(0).modelData
        panel.fullscreenService.backend = fakeFullscreenBackend
        fullscreenWorkspace.hasFullscreen = true
        panel.fullscreenService.refresh()
        saveField(panel, "presentation", "foreground")
        stage = 1
      }} else if (stage === 1 && panel.presentation === "foreground"
          && panel.mappedSurfaceCount() === expected && panel.surfaceAt(0).fullscreenSuppressed) {{
        suppressionObserved = !panel.surfaceAt(0).paintAllowed
          && panel.surfaceAt(0).stackObject.activeProductionEffectCount === 1
        modeIdentityStable = identitiesMatch(panel, true)
        for (var i = 0; i < panel.productionSurfaces.length; i++)
          modeIdentityStable = modeIdentityStable
            && panel.surfaceAt(i).effectiveLayer === WlrLayer.Overlay
        fullscreenWorkspace.hasFullscreen = false
        panel.fullscreenService.refresh()
        stage = 11
      }} else if (stage === 11 && !panel.surfaceAt(0).fullscreenSuppressed
          && panel.surfaceAt(0).paintAllowed) {{
        modeIdentityStable = modeIdentityStable && identitiesMatch(panel, true)
        saveField(panel, "presentation", "background")
        stage = 2
      }} else if (stage === 2 && panel.presentation === "background"
          && panel.mappedSurfaceCount() === expected) {{
        modeIdentityStable = modeIdentityStable && identitiesMatch(panel, true)
        saveField(panel, "enabled", false)
        stage = 3
      }} else if (stage === 3 && panel.mappingMode === "none"
          && panel.mappedSurfaceCount() === 0 && panel.loadedEffectCount() === 0) {{
        disabledIdentityStable = identitiesMatch(panel, false)
        saveField(panel, "enabled", true)
        stage = 4
      }} else if (stage === 4 && panel.mappingMode === "bottom"
          && panel.mappedSurfaceCount() === expected && panel.loadedEffectCount() === expected) {{
        disabledIdentityStable = disabledIdentityStable && identitiesMatch(panel, false)
        var status = panel.statusObject()
        stop()
        console.log("BEHAVE " + JSON.stringify({{expected: expected,
          surfaceCount: panel.productionSurfaces.length,
          mappedSurfaceCount: panel.mappedSurfaceCount(), loadedEffectCount: panel.loadedEffectCount(),
          modeIdentityStable: modeIdentityStable, disabledIdentityStable: disabledIdentityStable,
          suppressionObserved: suppressionObserved,
          statusSurfaceCount: status.surfaceCount, statusMapped: status.mappedSurfaceCount,
          statusMode: status.mode, persistenceHealthy: status.persistence.healthy}}))
        Qt.quit()
      }} else if (attempts > 150) {{
        console.log("BEHAVE_ERR phase 3 surface lifecycle did not settle at stage " + stage)
        Qt.quit()
      }}
    }}
  }}
}}
'''
            output = run_quickshell(
                qml,
                config_home=config_home,
                env_overrides={"XDG_STATE_HOME": str(state_home)},
                timeout=15,
            )
        require_no_qml_errors(output)
        row = parse_behave(output)[-1]
        self.assertGreaterEqual(row["expected"], 1, output[-2000:])
        self.assertEqual(row["surfaceCount"], row["expected"], output[-2000:])
        self.assertEqual(row["mappedSurfaceCount"], row["expected"], output[-2000:])
        self.assertEqual(row["loadedEffectCount"], row["expected"], output[-2000:])
        self.assertTrue(row["modeIdentityStable"], output[-2000:])
        self.assertTrue(row["disabledIdentityStable"], output[-2000:])
        self.assertTrue(row["suppressionObserved"], output[-2000:])
        self.assertEqual(row["statusSurfaceCount"], row["expected"], output[-2000:])
        self.assertEqual(row["statusMapped"], row["expected"], output[-2000:])
        self.assertEqual(row["statusMode"], "bottom", output[-2000:])
        self.assertTrue(row["persistenceHealthy"], output[-2000:])

    def test_panel_restarts_with_one_fresh_surface_per_output(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as state_dir:
            config_home = Path(config_dir)
            settings_file = config_home / "omarchy/jobo/desktop-ambience/settings.json"
            settings_file.parent.mkdir(parents=True)
            settings_file.write_text(json.dumps({
                "version": 1,
                "enabled": True,
                "presentation": "background",
                "activeEffects": ["trackingLines"],
                "effects": {"trackingLines": {"enabled": True, "intensity": 0}},
                "backgroundVignette": {"enabled": False},
            }), encoding="utf-8")
            state_home = Path(state_dir)
            palette = state_home / "omarchy/current/theme/colors.toml"
            palette.parent.mkdir(parents=True)
            palette.write_text('color11 = "#aabbcc"\n', encoding="utf-8")
            qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  Loader {{ id: panelLoader; source: "{qml_url('Panel.qml')}"; onLoaded: probe.start() }}
  Timer {{
    id: probe; interval: 40; repeat: true; property int attempts: 0
    onTriggered: {{
      attempts += 1
      var panel = panelLoader.item
      var expected = Quickshell.screens.length
      if (panel && panel.settingsService.hasLoaded && panel.productionSurfaces.length === expected
          && panel.mappedSurfaceCount() === expected && panel.loadedEffectCount() === expected) {{
        stop()
        console.log("BEHAVE " + JSON.stringify({{expected: expected,
          surfaces: panel.productionSurfaces.length, mapped: panel.mappedSurfaceCount()}}))
        Qt.quit()
      }} else if (attempts > 80) {{ console.log("BEHAVE_ERR panel restart did not settle"); Qt.quit() }}
    }}
  }}
}}
'''
            rows = []
            for _ in range(2):
                output = run_quickshell(
                    qml,
                    config_home=config_home,
                    env_overrides={"XDG_STATE_HOME": str(state_home)},
                    timeout=10,
                )
                require_no_qml_errors(output)
                rows.append(parse_behave(output)[-1])
        for row in rows:
            self.assertGreaterEqual(row["expected"], 1)
            self.assertEqual(row["surfaces"], row["expected"])
            self.assertEqual(row["mapped"], row["expected"])


if __name__ == "__main__":
    unittest.main()
