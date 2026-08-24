from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from qml_harness import HAVE_SESSION, parse_behave, qml_url, require_no_qml_errors, run_quickshell


SETTINGS = {
    "enabled": True,
    "intensity": 1,
    "speed": 1,
    "dropletCount": 28,
    "dropletSize": 12,
    "formationTime": 3800,
    "fallSpeed": 260,
    "direction": "auto",
    "accentBlend": 0,
    "bloodMode": False,
}


@unittest.skipUnless(HAVE_SESSION, "needs a quickshell binary and a Wayland session")
class DripBehaviorTests(unittest.TestCase):
    def test_bar_geometry_direction_fallbacks_and_reduced_motion(self):
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  id: root
  property var top: ({{}})
  property var bottom: ({{}})
  property var forcedDown: ({{}})
  property var forcedUp: ({{}})
  property var hidden: ({{}})
  QtObject {{
    id: theme
    function colorFor(name, fallback) {{
      return name === "accent" ? "#55bbdd" : (name === "foreground" ? "#e8edf2" : fallback)
    }}
  }}
  Item {{
    width: 320; height: 180
    Loader {{
      id: drip; anchors.fill: parent
      source: "{qml_url('effects/DripEffect.qml')}"
      onLoaded: {{
        item.effectSettings = {json.dumps(SETTINGS)}
        item.theme = theme
        item.barState = {{available: true, position: "top", size: 28, hidden: false}}
        probe.start()
      }}
    }}
  }}
  Timer {{
    id: probe; interval: 60
    onTriggered: {{
      root.top = root.capture()
      drip.item.barState = {{available: true, position: "bottom", size: 28, hidden: false}}
      next.restart()
    }}
  }}
  Timer {{
    id: next; interval: 20
    onTriggered: {{
      root.bottom = root.capture()
      root.setDirection("down")
      forcedDownProbe.restart()
    }}
  }}
  Timer {{
    id: forcedDownProbe; interval: 20
    onTriggered: {{
      root.forcedDown = root.capture()
      root.setDirection("up")
      forcedUpProbe.restart()
    }}
  }}
  Timer {{
    id: forcedUpProbe; interval: 20
    onTriggered: {{
      root.forcedUp = root.capture()
      drip.item.barState = {{available: false, position: "bottom", size: 28, hidden: true}}
      hiddenProbe.restart()
    }}
  }}
  Timer {{
    id: hiddenProbe; interval: 20
    onTriggered: {{
      root.hidden = root.capture()
      drip.item.reducedMotion = true
      finalProbe.restart()
    }}
  }}
  Timer {{
    id: finalProbe; interval: 20
    onTriggered: {{
      console.log("BEHAVE " + JSON.stringify({{
        top: root.top,
        bottom: root.bottom,
        forcedDown: root.forcedDown,
        forcedUp: root.forcedUp,
        hidden: root.hidden,
        reduced: {{animationsRunning: drip.item.animationsRunning,
          firstY: drip.item.firstDropletY, source: drip.item.sourceEdge,
          beadProgress: drip.item.firstDropletBeadProgress,
          count: drip.item.allocatedDropletCount}}
      }}))
      Qt.quit()
    }}
  }}
  function setDirection(value) {{
    var nextSettings = Object.assign({{}}, drip.item.effectSettings)
    nextSettings.direction = value
    drip.item.effectSettings = nextSettings
  }}
  function capture() {{
    return {{direction: drip.item.effectiveDirection, source: drip.item.sourceEdge,
      usable: drip.item.usableBarGeometry, usingBar: drip.item.usingBarGeometry,
      distance: drip.item.travelDistance, generation: drip.item.cycleGeneration,
      shadowOffsetX: drip.item.firstDropletShadowScreenOffsetX}}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as config_home:
            output = run_quickshell(qml, config_home=Path(config_home), timeout=10)
        require_no_qml_errors(output)
        row = parse_behave(output)[-1]
        self.assertEqual(row["top"]["direction"], "down")
        self.assertEqual(row["top"]["source"], 28)
        self.assertTrue(row["top"]["usable"])
        self.assertTrue(row["top"]["usingBar"])
        self.assertGreater(row["top"]["shadowOffsetX"], 0)
        self.assertEqual(row["bottom"]["direction"], "up")
        self.assertEqual(row["bottom"]["source"], 152)
        self.assertTrue(row["bottom"]["usingBar"])
        self.assertLess(row["bottom"]["shadowOffsetX"], 0)
        self.assertEqual(row["forcedDown"]["direction"], "down")
        self.assertEqual(row["forcedDown"]["source"], 0)
        self.assertFalse(row["forcedDown"]["usingBar"])
        self.assertEqual(row["forcedUp"]["direction"], "up")
        self.assertEqual(row["forcedUp"]["source"], 152)
        self.assertTrue(row["forcedUp"]["usingBar"])
        self.assertEqual(row["hidden"]["direction"], "up")
        self.assertEqual(row["hidden"]["source"], 180)
        self.assertFalse(row["hidden"]["usable"])
        self.assertFalse(row["hidden"]["usingBar"])
        self.assertFalse(row["reduced"]["animationsRunning"])
        self.assertEqual(row["reduced"]["count"], SETTINGS["dropletCount"])
        self.assertEqual(row["reduced"]["beadProgress"], 1)
        self.assertLess(row["reduced"]["firstY"], row["reduced"]["source"])
        self.assertGreater(row["reduced"]["firstY"], row["reduced"]["source"] - 100)

    def test_invalid_bar_size_falls_back_and_cycle_generation_updates_without_reloading(self):
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  property var identity: null
  Item {{
    width: 240; height: 120
    Loader {{
      id: drip; anchors.fill: parent
      source: "{qml_url('effects/DripEffect.qml')}"
      onLoaded: {{
        item.effectSettings = {json.dumps(SETTINGS)}
        item.barState = {{available: true, position: "top", size: 24, hidden: false}}
        identity = item
        first.restart()
      }}
    }}
  }}
  Timer {{
    id: first; interval: 40
    onTriggered: {{
      var generation = drip.item.cycleGeneration
      drip.item.barState = {{available: true, position: "bottom", size: 500, hidden: false}}
      finalProbe.generation = generation
      finalProbe.restart()
    }}
  }}
  Timer {{
    id: finalProbe; interval: 40; property int generation: -1
    onTriggered: {{
      console.log("BEHAVE " + JSON.stringify({{
        sameObject: identity === drip.item,
        usable: drip.item.usableBarGeometry,
        direction: drip.item.effectiveDirection,
        source: drip.item.sourceEdge,
        generationAdvanced: drip.item.cycleGeneration > generation
      }}))
      Qt.quit()
    }}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as config_home:
            output = run_quickshell(qml, config_home=Path(config_home), timeout=10)
        require_no_qml_errors(output)
        row = parse_behave(output)[-1]
        self.assertEqual(row, {
            "sameObject": True,
            "usable": False,
            "direction": "down",
            "source": 0,
            "generationAdvanced": True,
        }, output[-2000:])

    def test_missing_vertical_hidden_and_incompatible_direction_fallbacks(self):
        cases = [
            {"direction": "auto", "bar": None},
            {"direction": "auto", "bar": {"available": True, "position": "left", "size": 28, "hidden": False}},
            {"direction": "auto", "bar": {"available": False, "position": "bottom", "size": 28, "hidden": True}},
            {"direction": "up", "bar": {"available": True, "position": "top", "size": 28, "hidden": False}},
            {"direction": "auto", "bar": {"available": True, "position": "bottom", "size": "bad", "hidden": False}},
        ]
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  id: root
  property var cases: {json.dumps(cases)}
  property var rows: []
  property int caseIndex: -1
  Item {{
    width: 240; height: 120
    Loader {{
      id: drip; anchors.fill: parent
      source: "{qml_url('effects/DripEffect.qml')}"
      onLoaded: {{ item.effectSettings = {json.dumps(SETTINGS)}; probe.start() }}
    }}
  }}
  Timer {{
    id: probe; interval: 20; repeat: true
    onTriggered: {{
      if (root.caseIndex >= 0) root.rows.push({{
        usable: drip.item.usableBarGeometry,
        direction: drip.item.effectiveDirection,
        source: drip.item.sourceEdge,
        usingBar: drip.item.usingBarGeometry
      }})
      root.caseIndex += 1
      if (root.caseIndex >= root.cases.length) {{
        stop()
        console.log("BEHAVE " + JSON.stringify(root.rows))
        Qt.quit()
        return
      }}
      var next = root.cases[root.caseIndex]
      var settings = Object.assign({{}}, drip.item.effectSettings)
      settings.direction = next.direction
      drip.item.effectSettings = settings
      drip.item.barState = next.bar
    }}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as config_home:
            output = run_quickshell(qml, config_home=Path(config_home), timeout=10)
        require_no_qml_errors(output)
        rows = parse_behave(output)[-1]
        self.assertEqual(rows, [
            {"usable": False, "direction": "down", "source": 0, "usingBar": False},
            {"usable": False, "direction": "down", "source": 0, "usingBar": False},
            {"usable": False, "direction": "down", "source": 0, "usingBar": False},
            {"usable": True, "direction": "up", "source": 120, "usingBar": False},
            {"usable": False, "direction": "down", "source": 0, "usingBar": False},
        ], output[-2000:])

    def test_speed_change_retimes_a_droplet_already_in_flight(self):
        settings = dict(SETTINGS)
        settings.update({"dropletCount": 6, "formationTime": 600, "fallSpeed": 80, "speed": 1})
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  Item {{
    width: 240; height: 240
    Loader {{
      id: drip; anchors.fill: parent
      source: "{qml_url('effects/DripEffect.qml')}"
      onLoaded: {{
        item.effectSettings = {json.dumps(settings)}
        item.barState = {{available: true, position: "top", size: 24, hidden: false, color: "#334455"}}
        retime.start()
      }}
    }}
  }}
  Timer {{
    id: retime; interval: 1500
    onTriggered: {{
      probe.startY = drip.item.firstDropletY
      probe.generation = drip.item.timingGeneration
      var next = Object.assign({{}}, drip.item.effectSettings)
      next.speed = 4
      drip.item.effectSettings = next
      probe.start()
    }}
  }}
  Timer {{
    id: probe; interval: 300
    property real startY: 0
    property int generation: -1
    onTriggered: {{
      console.log("BEHAVE " + JSON.stringify({{
        startY: startY,
        endY: drip.item.firstDropletY,
        generationAdvanced: drip.item.timingGeneration > generation,
        phase: drip.item.firstDropletAnimationRunning
      }}))
      Qt.quit()
    }}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as config_home:
            output = run_quickshell(qml, config_home=Path(config_home), timeout=10)
        require_no_qml_errors(output)
        row = parse_behave(output)[-1]
        self.assertTrue(row["generationAdvanced"])
        self.assertTrue(row["phase"])
        self.assertGreater(row["endY"] - row["startY"], 40)

    def test_shadow_remains_visible_after_droplet_leaves_top_eighth(self):
        settings = dict(SETTINGS)
        settings.update({"dropletCount": 6, "formationTime": 600, "fallSpeed": 120})
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  Item {{
    width: 240; height: 240
    Loader {{
      id: drip; anchors.fill: parent
      source: "{qml_url('effects/DripEffect.qml')}"
      onLoaded: {{
        item.effectSettings = {json.dumps(settings)}
        item.barState = {{available: true, position: "top", size: 24, hidden: false, color: "#334455"}}
        first.start()
      }}
    }}
  }}
  Timer {{
    id: first; interval: 1500
    onTriggered: {{ second.firstY = drip.item.firstDropletY; second.firstOpacity = drip.item.firstDropletShadowOpacity; second.start() }}
  }}
  Timer {{
    id: second; interval: 600
    property real firstY: 0
    property real firstOpacity: 0
    onTriggered: {{
      console.log("BEHAVE " + JSON.stringify({{
        firstY: firstY, firstOpacity: firstOpacity,
        secondY: drip.item.firstDropletY,
        secondOpacity: drip.item.firstDropletShadowOpacity,
        shadowOverhang: drip.item.firstDropletShadowOverhang
      }}))
      Qt.quit()
    }}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as config_home:
            output = run_quickshell(qml, config_home=Path(config_home), timeout=10)
        require_no_qml_errors(output)
        row = parse_behave(output)[-1]
        self.assertGreater(row["firstY"], 30)
        self.assertGreater(row["secondY"], row["firstY"])
        self.assertGreater(row["firstOpacity"], 0)
        self.assertGreater(row["secondOpacity"], 0)
        self.assertGreater(row["shadowOverhang"], 0)

    def test_blood_mode_overrides_bar_color_and_strengthens_decorations(self):
        settings = dict(SETTINGS)
        settings["bloodMode"] = True
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  Item {{
    width: 240; height: 120
    Loader {{
      id: drip; anchors.fill: parent
      source: "{qml_url('effects/DripEffect.qml')}"
      onLoaded: {{
        item.effectSettings = {json.dumps(settings)}
        item.barState = {{available: true, position: "top", size: 24, hidden: false, color: "#334455"}}
        item.reducedMotion = true
        probe.start()
      }}
    }}
  }}
  Timer {{
    id: probe; interval: 40
    onTriggered: {{
      console.log("BEHAVE " + JSON.stringify({{
        bloodMode: drip.item.bloodMode,
        barColor: String(drip.item.barDropletColor),
        waterColor: String(drip.item.waterColor),
        shadowAlpha: drip.item.shadowColor.a,
        reflectionColor: String(drip.item.reflectionColor)
      }}))
      Qt.quit()
    }}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as config_home:
            output = run_quickshell(qml, config_home=Path(config_home), timeout=10)
        require_no_qml_errors(output)
        row = parse_behave(output)[-1]
        self.assertTrue(row["bloodMode"])
        self.assertEqual(row["barColor"], "#334455")
        self.assertEqual(row["waterColor"], "#4a1014")
        self.assertGreater(row["shadowAlpha"], 0.6)
        self.assertNotEqual(row["reflectionColor"], row["waterColor"])

    def test_runtime_opacity_reduced_motion_and_population_gate_delegate_animation(self):
        settings = dict(SETTINGS)
        settings["dropletCount"] = 6
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  id: root
  property var active: ({{}})
  property var disabled: ({{}})
  property var transparent: ({{}})
  Item {{
    width: 240; height: 120
    Loader {{
      id: drip; anchors.fill: parent
      source: "{qml_url('effects/DripEffect.qml')}"
      onLoaded: {{
        item.effectSettings = {json.dumps(settings)}
        item.barState = {{available: true, position: "top", size: 24, hidden: false, color: "#334455"}}
        activeProbe.start()
      }}
    }}
  }}
  Timer {{
    id: activeProbe; interval: 50
    onTriggered: {{
      root.active = root.capture()
      drip.item.runtimeEnabled = false
      disabledProbe.restart()
    }}
  }}
  Timer {{
    id: disabledProbe; interval: 20
    onTriggered: {{
      root.disabled = root.capture()
      drip.item.runtimeEnabled = true
      drip.item.globalOpacity = 0
      transparentProbe.restart()
    }}
  }}
  Timer {{
    id: transparentProbe; interval: 20
    onTriggered: {{
      root.transparent = root.capture()
      drip.item.globalOpacity = 1
      drip.item.reducedMotion = true
      var next = Object.assign({{}}, drip.item.effectSettings)
      next.dropletCount = 10
      drip.item.effectSettings = next
      finalProbe.restart()
    }}
  }}
  Timer {{
    id: finalProbe; interval: 30
    onTriggered: {{
      console.log("BEHAVE " + JSON.stringify({{
        active: root.active, disabled: root.disabled, transparent: root.transparent,
        reduced: root.capture(), mature: drip.item.firstDropletBeadProgress,
        count: drip.item.allocatedDropletCount,
        barColor: String(drip.item.baseDropletColor)
      }}))
      Qt.quit()
    }}
  }}
  function capture() {{
    return {{visible: drip.item.effectVisible, requested: drip.item.animationsRunning,
      delegate: drip.item.firstDropletAnimationRunning}}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as config_home:
            output = run_quickshell(qml, config_home=Path(config_home), timeout=10)
        require_no_qml_errors(output)
        row = parse_behave(output)[-1]
        self.assertEqual(row["active"], {"visible": True, "requested": True, "delegate": True})
        self.assertEqual(row["disabled"], {"visible": False, "requested": False, "delegate": False})
        self.assertEqual(row["transparent"], {"visible": False, "requested": False, "delegate": False})
        self.assertEqual(row["reduced"], {"visible": True, "requested": False, "delegate": False})
        self.assertEqual(row["mature"], 1)
        self.assertEqual(row["count"], 10)
        self.assertEqual(row["barColor"], "#334455")


if __name__ == "__main__":
    unittest.main()
