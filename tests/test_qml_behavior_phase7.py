from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from qml_harness import HAVE_SESSION, parse_behave, qml_url, require_no_qml_errors, run_quickshell


@unittest.skipUnless(HAVE_SESSION, "needs a quickshell binary and a Wayland session")
class Phase7BehaviorTests(unittest.TestCase):
    def test_dust_motes_consumes_injected_cursor_state_without_owning_it(self):
        settings = json.dumps({
            "enabled": True,
            "intensity": 1,
            "speed": 1,
            "moteCount": 0,
            "moteSize": 1,
            "accentBlend": 0,
            "mouseReactive": True,
            "mouseInfluence": 0.28,
        }).lower()
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  QtObject {{
    id: tracker
    property real cursorX: 101
    property real cursorY: 202
    property real cursorVelocityX: 3
    property real cursorVelocityY: 4
    property real cursorKick: 0.75
  }}
  Loader {{
    id: effectLoader
    source: "{qml_url('effects/DustMotesEffect.qml')}"
    onLoaded: {{
      item.cursorTracker = tracker
      item.effectSettings = {settings}
      probe.start()
    }}
  }}
  Timer {{
    id: probe
    interval: 30
    onTriggered: {{
      var effect = effectLoader.item
      console.log("BEHAVE " + JSON.stringify({{
        x: effect.cursorX, y: effect.cursorY,
        vx: effect.cursorVelocityX, vy: effect.cursorVelocityY,
        speed: effect.cursorSpeed, kick: effect.cursorKick
      }}))
      Qt.quit()
    }}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as config_home:
            output = run_quickshell(qml, config_home=Path(config_home), timeout=10)
        require_no_qml_errors(output)
        payload = parse_behave(output)[-1]
        self.assertEqual(
            payload,
            {"x": 101, "y": 202, "vx": 3, "vy": 4, "speed": 5, "kick": 0.75},
            output[-2000:],
        )

    def test_stack_waits_for_nonzero_stable_geometry_before_painting(self):
        settings = json.dumps({
            "enabled": True,
            "intensity": 1,
            "speed": 1,
            "dropCount": 4,
            "slant": 0,
            "mistAmount": 0,
            "splashAmount": 0,
            "accentBlend": 0,
            "vignette": False,
        }).lower()
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  id: root
  QtObject {{
    id: state
    property real opacity: 1
    property bool reduceMotion: false
    property var effects: ({{rainfall: {settings}}})
  }}
  Item {{
    id: host
    width: 0
    height: 0
    Loader {{
      id: stackLoader
      anchors.fill: parent
      source: "{qml_url('components/AmbienceStack.qml')}"
      onLoaded: {{
        item.settings = state
        item.activeEffects = ["rainfall"]
        item.productionEffectsEnabled = true
        zeroProbe.start()
      }}
    }}
  }}
  Timer {{
    id: zeroProbe
    interval: 30
    onTriggered: {{
      var stack = stackLoader.item
      root.zeroReady = stack.animationGeometryReady
      root.zeroRuntime = stack.productionEffectObject("rainfall").runtimeEnabled
      host.width = 320
      host.height = 180
      settlingProbe.start()
      readyProbe.start()
    }}
  }}
  property bool zeroReady: true
  property bool zeroRuntime: true
  property bool settlingReady: true
  Timer {{
    id: settlingProbe
    interval: 25
    onTriggered: root.settlingReady = stackLoader.item.animationGeometryReady
  }}
  Timer {{
    id: readyProbe
    interval: 130
    onTriggered: {{
      var stack = stackLoader.item
      console.log("BEHAVE " + JSON.stringify({{
        zeroReady: root.zeroReady,
        zeroRuntime: root.zeroRuntime,
        settlingReady: root.settlingReady,
        ready: stack.animationGeometryReady,
        runtime: stack.productionEffectObject("rainfall").runtimeEnabled
      }}))
      Qt.quit()
    }}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as config_home:
            output = run_quickshell(qml, config_home=Path(config_home), timeout=10)
        require_no_qml_errors(output)
        payload = parse_behave(output)[-1]
        self.assertEqual(payload, {
            "zeroReady": False,
            "zeroRuntime": False,
            "settlingReady": False,
            "ready": True,
            "runtime": True,
        }, output[-2000:])

    def test_cursor_tracker_stays_idle_until_activated(self):
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  Loader {{
    id: trackerLoader
    source: "{qml_url('services/CursorTracker.qml')}"
    onLoaded: probe.start()
  }}
  Timer {{
    id: probe
    interval: 300
    onTriggered: {{
      var tracker = trackerLoader.item
      console.log("BEHAVE " + JSON.stringify({{
        active: tracker.active,
        running: tracker.running,
        launchCount: tracker.launchCount
      }}))
      Qt.quit()
    }}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as config_home:
            output = run_quickshell(qml, config_home=Path(config_home), timeout=10)
        require_no_qml_errors(output)
        payload = parse_behave(output)[-1]
        self.assertEqual(payload, {"active": False, "running": False, "launchCount": 0}, output[-2000:])
