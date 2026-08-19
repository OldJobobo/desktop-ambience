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
