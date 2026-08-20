from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from qml_harness import HAVE_SESSION, parse_behave, qml_url, require_no_qml_errors, run_quickshell


SETTINGS = {
    "enabled": True,
    "intensity": 0.55,
    "speed": 1,
    "gridSpacing": 64,
    "gridLineWidth": 1,
    "gridOpacity": 0.28,
    "guideOpacity": 0.58,
    "parallaxEnabled": True,
    "mouseInfluence": 0.22,
    "mouseGuides": True,
    "reticleStyle": "brackets",
    "reticleSize": 42,
    "reticlePulse": True,
    "colorRole": "accent",
}


@unittest.skipUnless(HAVE_SESSION, "needs a quickshell binary and a Wayland session")
class TacticalGridBehaviorTests(unittest.TestCase):
    def test_pointer_is_output_local_parallax_is_bounded_and_reduced_motion_is_static(self):
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  id: root
  property var first: ({{}})
  property var moved: ({{}})
  QtObject {{ id: screenA; property real x: -400; property real y: -300 }}
  QtObject {{ id: screenB; property real x: 0; property real y: -300 }}
  QtObject {{
    id: tracker
    property real cursorX: -240
    property real cursorY: -210
    property real displayCursorX: -240
    property real displayCursorY: -210
    property bool hasCursorSample: true
  }}
  QtObject {{
    id: theme
    function colorFor(name, fallback) {{ return name === "accent" ? "#66ccff" : fallback }}
  }}
  Item {{
    id: hostA; width: 320; height: 180
    Loader {{
      id: gridA; anchors.fill: parent
      source: "{qml_url('effects/TacticalGridEffect.qml')}"
      onLoaded: {{ item.effectSettings = {json.dumps(SETTINGS)}; item.targetScreen = screenA; item.cursorTracker = tracker; item.theme = theme }}
    }}
  }}
  Item {{
    id: hostB; width: 320; height: 180
    Loader {{
      id: gridB; anchors.fill: parent
      source: "{qml_url('effects/TacticalGridEffect.qml')}"
      onLoaded: {{ item.effectSettings = {json.dumps(SETTINGS)}; item.targetScreen = screenB; item.cursorTracker = tracker; item.theme = theme }}
    }}
  }}
  Timer {{
    interval: 100; running: gridA.item !== null && gridB.item !== null
    onTriggered: {{
      root.first = {{
        insideA: gridA.item.cursorInsideOutput,
        insideB: gridB.item.cursorInsideOutput,
        localX: gridA.item.cursorLocalX,
        localY: gridA.item.cursorLocalY,
        offsetX: gridA.item.parallaxOffsetX,
        offsetY: gridA.item.parallaxOffsetY
      }}
      tracker.cursorX = -100; tracker.displayCursorX = -100
      tracker.cursorY = -140; tracker.displayCursorY = -140
      movedProbe.start()
    }}
  }}
  Timer {{
    id: movedProbe; interval: 220
    onTriggered: {{
      root.moved = {{
        inside: gridA.item.cursorInsideOutput,
        localX: gridA.item.cursorLocalX,
        localY: gridA.item.cursorLocalY,
        offsetX: gridA.item.parallaxOffsetX,
        offsetY: gridA.item.parallaxOffsetY,
        renderedX: gridA.item.renderedGridX,
        renderedY: gridA.item.renderedGridY
      }}
      var next = Object.assign({{}}, gridA.item.effectSettings)
      next.reticleStyle = "ring"
      gridA.item.effectSettings = next
      gridA.item.reducedMotion = true
      tracker.cursorX = 0
      tracker.cursorY = -210
      finalProbe.start()
    }}
  }}
  Timer {{
    id: finalProbe; interval: 40
    onTriggered: {{
      console.log("BEHAVE " + JSON.stringify({{
        first: root.first,
        moved: root.moved,
        reduced: {{
          offsetX: gridA.item.parallaxOffsetX,
          offsetY: gridA.item.parallaxOffsetY,
          scale: gridA.item.reticleScale,
          style: gridA.item.reticleStyle
        }},
        ownership: {{a: gridA.item.cursorInsideOutput, b: gridB.item.cursorInsideOutput}}
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
        self.assertEqual(payload["first"], {
            "insideA": True, "insideB": False,
            "localX": 160, "localY": 90, "offsetX": 0, "offsetY": 0,
        }, output[-2000:])
        self.assertTrue(payload["moved"]["inside"], output[-2000:])
        self.assertEqual((payload["moved"]["localX"], payload["moved"]["localY"]), (300, 160))
        self.assertLess(payload["moved"]["offsetX"], 0)
        self.assertLess(payload["moved"]["offsetY"], 0)
        maximum = SETTINGS["gridSpacing"] * SETTINGS["mouseInfluence"] * 0.6
        self.assertLessEqual(abs(payload["moved"]["offsetX"]), maximum)
        self.assertLessEqual(abs(payload["moved"]["offsetY"]), maximum)
        self.assertAlmostEqual(payload["moved"]["renderedX"], payload["moved"]["offsetX"], places=2)
        self.assertAlmostEqual(payload["moved"]["renderedY"], payload["moved"]["offsetY"], places=2)
        self.assertEqual(payload["reduced"], {
            "offsetX": 0, "offsetY": 0, "scale": 1, "style": "ring",
        })
        self.assertEqual(payload["ownership"], {"a": False, "b": True})

    def test_missing_cursor_sample_hides_targeting_and_stops_pulse(self):
        settings = dict(SETTINGS)
        settings["reticleStyle"] = "diamond"
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  QtObject {{ id: screen; property real x: 100; property real y: 50 }}
  QtObject {{
    id: tracker
    property real cursorX: 200
    property real cursorY: 100
    property bool hasCursorSample: false
  }}
  Item {{
    width: 320; height: 180
    Loader {{
      id: grid; anchors.fill: parent
      source: "{qml_url('effects/TacticalGridEffect.qml')}"
      onLoaded: {{ item.effectSettings = {json.dumps(settings)}; item.targetScreen = screen; item.cursorTracker = tracker; probe.start() }}
    }}
  }}
  Timer {{
    id: probe; interval: 100
    onTriggered: {{
      console.log("BEHAVE " + JSON.stringify({{
        inside: grid.item.cursorInsideOutput,
        phase: grid.item.pulsePhase,
        style: grid.item.reticleStyle,
        visible: grid.item.effectVisible
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
            "inside": False, "phase": 0, "style": "diamond", "visible": True,
        }, output[-2000:])


if __name__ == "__main__":
    unittest.main()
