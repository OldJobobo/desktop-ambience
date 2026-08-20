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
        })
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  QtObject {{
    id: tracker
    property real cursorX: 101
    property real cursorY: 202
    property bool hasCursorSample: true
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
        speed: effect.cursorSpeed, kick: effect.cursorKick,
        mouseInfluence: effect.mouseInfluence, moteCount: effect.moteCount
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
            {
                "x": 101, "y": 202, "vx": 3, "vy": 4, "speed": 5,
                "kick": 0.75, "mouseInfluence": 0.28, "moteCount": 0,
            },
            output[-2000:],
        )

    def test_mouse_influence_pushes_nearby_motes_after_cursor_impulse_decays(self):
        settings = json.dumps({
            "enabled": True,
            "intensity": 1,
            "speed": 1,
            "moteCount": 1,
            "moteSize": 4,
            "accentBlend": 0,
            "mouseReactive": True,
            "mouseInfluence": 1,
        })
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  id: root
  property var mote: null
  QtObject {{
    id: screen
    property real x: -400
    property real y: -300
  }}
  QtObject {{
    id: tracker
    property real cursorX: -1
    property real cursorY: -1
    property bool hasCursorSample: false
    property real cursorVelocityX: 0
    property real cursorVelocityY: 0
    property real cursorKick: 0
  }}
  function findPersistentMote(item) {{
    if (!item) return null
    if ("airOffsetX" in item && "airVelocityX" in item) return item
    var children = item.children || []
    for (var i = 0; i < children.length; i++) {{
      var found = findPersistentMote(children[i])
      if (found) return found
    }}
    return null
  }}
  Item {{
    width: 320
    height: 180
    Loader {{
      id: effectLoader
      anchors.fill: parent
      source: "{qml_url('effects/DustMotesEffect.qml')}"
      onLoaded: {{
        item.effectSettings = {settings}
        item.cursorTracker = tracker
        item.targetScreen = screen
        locate.start()
      }}
    }}
  }}
  Timer {{
    id: locate
    interval: 180
    onTriggered: {{
      root.mote = root.findPersistentMote(effectLoader.item)
      tracker.cursorX = screen.x + root.mote.x + root.mote.width / 2 - 80
      tracker.cursorY = screen.y + root.mote.y + root.mote.height / 2
      tracker.hasCursorSample = true
      inspect.start()
    }}
  }}
  Timer {{
    id: inspect
    interval: 330
    onTriggered: {{
      console.log("BEHAVE " + JSON.stringify({{
        offsetX: root.mote.airOffsetX,
        offsetY: root.mote.airOffsetY,
        cursorX: effectLoader.item.cursorX,
        cursorY: effectLoader.item.cursorY,
        speed: effectLoader.item.cursorSpeed,
        kick: effectLoader.item.cursorKick
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
        self.assertLess(payload["cursorX"], 0, output[-2000:])
        self.assertLess(payload["cursorY"], 0, output[-2000:])
        self.assertEqual(payload["speed"], 0, output[-2000:])
        self.assertEqual(payload["kick"], 0, output[-2000:])
        self.assertGreater(abs(payload["offsetX"]) + abs(payload["offsetY"]), 1, output[-2000:])

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
        })
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

    def test_god_rays_motion_clock_survives_live_speed_and_count_changes(self):
        settings = {
            "enabled": True, "intensity": 0.8, "speed": 0.8, "rayCount": 7,
            "raySpread": 0.72, "blurSoftness": 0.88, "accentBlend": 0.58,
            "shimmer": True, "vignette": True, "origin": "top-left",
        }
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  property real beforeClock: -1
  Item {{
    width: 320
    height: 180
    Loader {{
      id: effectLoader
      anchors.fill: parent
      source: "{qml_url('effects/GodRaysEffect.qml')}"
      onLoaded: {{ item.effectSettings = {json.dumps(settings)}; firstProbe.start() }}
    }}
  }}
  Timer {{
    id: firstProbe
    interval: 180
    onTriggered: {{
      beforeClock = effectLoader.item.motionClock
      var next = Object.assign({{}}, effectLoader.item.effectSettings)
      next.speed = 3.5
      next.rayCount = 12
      effectLoader.item.effectSettings = next
      finalProbe.start()
    }}
  }}
  Timer {{
    id: finalProbe
    interval: 220
    onTriggered: {{
      console.log("BEHAVE " + JSON.stringify({{
        beforeClock: beforeClock,
        afterClock: effectLoader.item.motionClock,
        speed: effectLoader.item.speed,
        rayCount: effectLoader.item.rayCount
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
        self.assertGreater(payload["beforeClock"], 0, output[-2000:])
        self.assertGreater(payload["afterClock"], payload["beforeClock"], output[-2000:])
        self.assertEqual(payload["speed"], 3.5)
        self.assertEqual(payload["rayCount"], 12)

    def test_cursor_tracker_handles_negative_origins_and_invalidates_stale_samples(self):
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  property var motion: ({{}})
  Loader {{
    id: trackerLoader
    source: "{qml_url('services/CursorTracker.qml')}"
    onLoaded: {{
      item.applyPayload('{{"x":-400,"y":-200}}')
      item.applyPayload('{{"x":-370,"y":-180}}')
      motionProbe.start()
    }}
  }}
  Timer {{
    id: motionProbe
    interval: 180
    onTriggered: {{
      var tracker = trackerLoader.item
      motion = {{
        valid: tracker.hasCursorSample,
        vx: tracker.cursorVelocityX,
        vy: tracker.cursorVelocityY,
        kick: tracker.cursorKick
      }}
      tracker.invalidateSample()
      console.log("BEHAVE " + JSON.stringify({{
        motion: motion,
        invalid: {{valid: tracker.hasCursorSample, x: tracker.cursorX, y: tracker.cursorY,
          displayX: tracker.displayCursorX, displayY: tracker.displayCursorY}}
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
        self.assertTrue(payload["motion"]["valid"], output[-2000:])
        self.assertGreater(payload["motion"]["vx"], 0, output[-2000:])
        self.assertGreater(payload["motion"]["vy"], 0, output[-2000:])
        self.assertGreater(payload["motion"]["kick"], 0, output[-2000:])
        self.assertEqual(payload["invalid"], {
            "valid": False, "x": -1, "y": -1, "displayX": -1, "displayY": -1,
        })

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
