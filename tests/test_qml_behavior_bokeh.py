from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from qml_harness import HAVE_SESSION, parse_behave, qml_url, require_no_qml_errors, run_quickshell


DEFAULTS = {
    "enabled": True,
    "intensity": 0.52,
    "speed": 0.65,
    "lightCount": 28,
    "lightSize": 88,
    "blurSoftness": 0.82,
    "driftAmount": 0.42,
    "twinkleAmount": 0.18,
    "primaryColorRole": "accent",
    "secondaryColorRole": "color13",
}


@unittest.skipUnless(HAVE_SESSION, "needs a quickshell binary and a Wayland session")
class BokehBehaviorTests(unittest.TestCase):
    def test_normalization_adds_payload_without_activating_and_bounds_roles_and_population(self):
        source = {
            "version": 99,
            "activeEffects": ["filmGrain", "trackingLines"],
            "effects": {
                "bokeh": {
                    "lightCount": 27.6,
                    "lightSize": 999,
                    "blurSoftness": -4,
                    "driftAmount": 4,
                    "twinkleAmount": -2,
                    "primaryColorRole": "invalid",
                    "secondaryColorRole": "color10",
                    "futureBokeh": {"kept": True},
                }
            },
            "futureRoot": [1, None, False],
        }
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  Loader {{ id: service; source: "{qml_url('services/AmbienceSettings.qml')}" }}
  Timer {{
    interval: 80; running: service.item !== null
    onTriggered: {{
      console.log("BEHAVE " + JSON.stringify(service.item.normalize({json.dumps(source)})))
      Qt.quit()
    }}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as config_home:
            output = run_quickshell(qml, config_home=Path(config_home), timeout=10)
        require_no_qml_errors(output)
        row = parse_behave(output)[-1]
        self.assertEqual(row["version"], 1)
        self.assertEqual(row["activeEffects"], ["filmGrain", "trackingLines"])
        self.assertEqual(row["futureRoot"], [1, None, False])
        self.assertEqual(row["effects"]["bokeh"]["lightCount"], 28)
        self.assertEqual(row["effects"]["bokeh"]["lightSize"], 240)
        self.assertEqual(row["effects"]["bokeh"]["blurSoftness"], 0)
        self.assertEqual(row["effects"]["bokeh"]["driftAmount"], 1)
        self.assertEqual(row["effects"]["bokeh"]["twinkleAmount"], 0)
        self.assertEqual(row["effects"]["bokeh"]["primaryColorRole"], "accent")
        self.assertEqual(row["effects"]["bokeh"]["secondaryColorRole"], "color10")
        self.assertEqual(row["effects"]["bokeh"]["futureBokeh"], {"kept": True})

    def test_startup_phases_are_seeded_distributed_and_begin_away_from_shared_endpoints(self):
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  Item {{
    width: 640; height: 360
    Loader {{
      id: effect; anchors.fill: parent
      source: "{qml_url('effects/BokehEffect.qml')}"
      onLoaded: {{ item.effectSettings = {json.dumps(DEFAULTS)}; startupProbe.start() }}
    }}
  }}
  Timer {{
    id: startupProbe; interval: 20
    onTriggered: {{
      var snapshots = []
      for (var i = 0; i < effect.item.boundedDelegateCount; i++)
        snapshots.push(effect.item.lightSnapshot(i))
      console.log("BEHAVE " + JSON.stringify({{
        animationRunning: effect.item.animationRunning,
        snapshots: snapshots
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
        snapshots = row["snapshots"]
        self.assertTrue(row["animationRunning"], output[-3000:])
        self.assertEqual(len(snapshots), 28)

        for key in ("initialXProgress", "initialYProgress", "initialTwinkleProgress"):
            values = [float(snapshot[key]) for snapshot in snapshots]
            self.assertGreaterEqual(len({round(value, 3) for value in values}), 24)
            self.assertLess(min(values), 0.05)
            self.assertGreater(max(values), 0.95)
            self.assertGreaterEqual(sum(0.05 < value < 0.95 for value in values), 18)

        self.assertTrue(all(
            abs(snapshot["startupX"] - snapshot["xA"]) > 1e-6
            and abs(snapshot["startupX"] - snapshot["xB"]) > 1e-6
            and abs(snapshot["startupY"] - snapshot["yA"]) > 1e-6
            and abs(snapshot["startupY"] - snapshot["yB"]) > 1e-6
            for snapshot in snapshots
        ))
        self.assertTrue(all(
            snapshot["twinkleFloor"] < snapshot["startupOpacity"] < snapshot["twinklePeak"]
            for snapshot in snapshots
        ))
        self.assertTrue(all(
            abs(snapshot["currentX"] - snapshot["startupX"])
                <= max(0.5, abs(snapshot["xB"] - snapshot["xA"]) * 0.01)
            and abs(snapshot["currentY"] - snapshot["startupY"])
                <= max(0.5, abs(snapshot["yB"] - snapshot["yA"]) * 0.01)
            and abs(snapshot["currentOpacity"] - snapshot["startupOpacity"]) <= 0.01
            for snapshot in snapshots
        ))
        self.assertTrue(all(
            abs(snapshot["currentX"] - snapshot["xA"]) > 1e-6
            and abs(snapshot["currentX"] - snapshot["xB"]) > 1e-6
            and snapshot["twinkleFloor"] < snapshot["currentOpacity"] < snapshot["twinklePeak"]
            for snapshot in snapshots
        ))
        self.assertGreaterEqual(len({round(snapshot["startupX"], 2) for snapshot in snapshots}), 24)
        self.assertGreaterEqual(len({round(snapshot["startupOpacity"], 4) for snapshot in snapshots}), 24)
        self.assertTrue(all(
            abs(snapshot["startupX"] - snapshot["cycleEndX"]) < 1e-8
            and abs(snapshot["startupY"] - snapshot["cycleEndY"]) < 1e-8
            and abs(snapshot["startupOpacity"] - snapshot["cycleEndOpacity"]) < 1e-8
            for snapshot in snapshots
        ))

    def test_grouped_blur_updates_live_preserves_identity_and_stops_cleanly(self):
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  property var firstIdentity: null
  property var secondIdentity: null
  property var initial: ({{}})
  property var rebound: ({{}})
  QtObject {{
    id: theme
    property bool alternate: false
    function colorFor(name, fallback) {{
      var base = alternate ? {{
        accent: "#ff3300", foreground: "#ffeecc", color10: "#22dd88", color13: "#6633ff"
      }} : {{
        accent: "#33ccff", foreground: "#eeeeee", color10: "#55aa77", color13: "#cc66ff"
      }}
      return base[name] || fallback
    }}
  }}
  Item {{
    width: 640; height: 360
    Loader {{
      id: effect; anchors.fill: parent
      source: "{qml_url('effects/BokehEffect.qml')}"
      onLoaded: {{
        item.effectSettings = {json.dumps(DEFAULTS)}
        item.theme = theme
        firstProbe.start()
      }}
    }}
  }}
  Timer {{
    id: firstProbe; interval: 140
    onTriggered: {{
      firstIdentity = effect.item.delegateObject(0)
      secondIdentity = effect.item.delegateObject(17)
      initial = {{
        count: effect.item.boundedDelegateCount,
        blurLayers: effect.item.activeBlurLayerCount,
        animated: effect.item.animationRunning,
        drift: effect.item.driftAnimationsRunning,
        twinkle: effect.item.twinkleAnimationsRunning,
        color: String(effect.item.effectivePrimaryColor),
        first: effect.item.lightSnapshot(0),
        second: effect.item.lightSnapshot(17)
      }}
      theme.alternate = true
      var next = Object.assign({{}}, effect.item.effectSettings)
      next.lightSize = 240
      next.blurSoftness = 1
      next.driftAmount = 0
      next.twinkleAmount = 0
      next.primaryColorRole = "foreground"
      next.secondaryColorRole = "color10"
      effect.item.effectSettings = next
      reboundProbe.start()
    }}
  }}
  Timer {{
    id: reboundProbe; interval: 140
    onTriggered: {{
      rebound = {{
        sameFirst: firstIdentity === effect.item.delegateObject(0),
        sameSecond: secondIdentity === effect.item.delegateObject(17),
        count: effect.item.boundedDelegateCount,
        animated: effect.item.animationRunning,
        color: String(effect.item.effectivePrimaryColor),
        role: effect.item.effectivePrimaryColorRole,
        secondaryRole: effect.item.effectiveSecondaryColorRole,
        overscan: effect.item.overscan,
        requiredOverscan: effect.item.maximumDrift + effect.item.maximumDiscRadius
          + effect.item.maximumBlurPadding + 8
      }}
      var maximum = Object.assign({{}}, effect.item.effectSettings)
      maximum.lightCount = 72
      maximum.driftAmount = 1
      maximum.twinkleAmount = 1
      effect.item.effectSettings = maximum
      maximumProbe.start()
    }}
  }}
  Timer {{
    id: maximumProbe; interval: 120
    onTriggered: {{
      var maximumCount = effect.item.boundedDelegateCount
      var maximumBlurLayers = effect.item.activeBlurLayerCount
      effect.item.reducedMotion = true
      var reducedAnimations = effect.item.animationRunning
      effect.item.runtimeEnabled = false
      Qt.callLater(function() {{
        console.log("BEHAVE " + JSON.stringify({{
          initial: initial,
          rebound: rebound,
          maximumCount: maximumCount,
          maximumBlurLayers: maximumBlurLayers,
          reducedAnimations: reducedAnimations,
          hidden: {{visible: effect.item.effectVisible,
            animations: effect.item.animationRunning,
            blurLayers: effect.item.activeBlurLayerCount}}
        }}))
        Qt.quit()
      }})
    }}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as config_home:
            output = run_quickshell(qml, config_home=Path(config_home), timeout=12)
        require_no_qml_errors(output)
        row = parse_behave(output)[-1]
        self.assertEqual(row["initial"]["count"], 28, output[-3000:])
        self.assertEqual(row["initial"]["blurLayers"], 3)
        self.assertTrue(row["initial"]["animated"])
        self.assertTrue(row["initial"]["drift"])
        self.assertTrue(row["initial"]["twinkle"])
        self.assertNotEqual(row["initial"]["first"]["depthBand"], row["initial"]["second"]["depthBand"])
        self.assertNotEqual(row["initial"]["first"]["diameter"], row["initial"]["second"]["diameter"])
        self.assertTrue(row["rebound"]["sameFirst"])
        self.assertTrue(row["rebound"]["sameSecond"])
        self.assertEqual(row["rebound"]["count"], 28)
        self.assertFalse(row["rebound"]["animated"])
        self.assertEqual(row["rebound"]["role"], "foreground")
        self.assertEqual(row["rebound"]["secondaryRole"], "color10")
        self.assertNotEqual(row["initial"]["color"], row["rebound"]["color"])
        self.assertGreaterEqual(row["rebound"]["overscan"], row["rebound"]["requiredOverscan"] - 1)
        self.assertEqual(row["maximumCount"], 72)
        self.assertEqual(row["maximumBlurLayers"], 3)
        self.assertFalse(row["reducedAnimations"])
        self.assertEqual(row["hidden"], {"visible": False, "animations": False, "blurLayers": 0})

    def test_minimum_field_is_deterministic_and_static_in_reduced_motion(self):
        settings = dict(DEFAULTS)
        settings.update({"lightCount": 6, "driftAmount": 1, "twinkleAmount": 1})
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  Item {{
    width: 480; height: 270
    Loader {{ id: first; anchors.fill: parent; source: "{qml_url('effects/BokehEffect.qml')}" }}
    Loader {{ id: second; anchors.fill: parent; source: "{qml_url('effects/BokehEffect.qml')}" }}
  }}
  Timer {{
    interval: 100; repeat: true; running: true; property int attempts: 0
    onTriggered: {{
      attempts += 1
      if (!first.item || !second.item) return
      first.item.effectSettings = {json.dumps(settings)}
      second.item.effectSettings = {json.dumps(settings)}
      first.item.reducedMotion = true
      second.item.reducedMotion = true
      var one = []
      var two = []
      for (var i = 0; i < 6; i++) {{
        one.push(first.item.lightSnapshot(i))
        two.push(second.item.lightSnapshot(i))
      }}
      console.log("BEHAVE " + JSON.stringify({{
        firstCount: first.item.boundedDelegateCount,
        secondCount: second.item.boundedDelegateCount,
        same: JSON.stringify(one) === JSON.stringify(two),
        bands: one.map(function(value) {{ return value.depthBand }}),
        firstAnimated: first.item.animationRunning,
        secondAnimated: second.item.animationRunning
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
        self.assertEqual(row["firstCount"], 6, output[-3000:])
        self.assertEqual(row["secondCount"], 6)
        self.assertTrue(row["same"])
        self.assertEqual(row["bands"], [0, 1, 2, 0, 1, 2])
        self.assertFalse(row["firstAnimated"])
        self.assertFalse(row["secondAnimated"])

    def test_stack_lazy_loads_bokeh_and_preserves_it_during_paint_suppression_and_reorder(self):
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  QtObject {{
    id: state
    property real opacity: 1
    property bool reduceMotion: false
    property var effects: ({{bokeh: {json.dumps(DEFAULTS)}}})
  }}
  Item {{
    width: 320; height: 180
    property var identity: null
    Loader {{
      id: stack; anchors.fill: parent; source: "{qml_url('components/AmbienceStack.qml')}"
      onLoaded: {{
        item.settings = state
        item.activeEffects = []
        inactiveProbe.start()
      }}
    }}
    Timer {{
      id: inactiveProbe; interval: 100
      onTriggered: {{
        var absent = stack.item.productionEffectObject("bokeh") === null
        stack.item.activeEffects = ["bokeh"]
        activeProbe.start()
        parent.absent = absent
      }}
    }}
    property bool absent: false
    Timer {{
      id: activeProbe; interval: 180
      onTriggered: {{
        parent.identity = stack.item.productionEffectObject("bokeh")
        var loaded = parent.identity !== null
        stack.item.paintEnabled = false
        stack.item.activeEffects = ["trackingLines", "bokeh"]
        Qt.callLater(function() {{
          console.log("BEHAVE " + JSON.stringify({{
            absent: parent.absent,
            loaded: loaded,
            same: parent.identity === stack.item.productionEffectObject("bokeh"),
            runtimeEnabled: parent.identity.runtimeEnabled,
            animations: parent.identity.animationRunning,
            bokehZ: stack.item.zForEffect("bokeh"),
            vhsZ: stack.item.zForEffect("trackingLines")
          }}))
          Qt.quit()
        }})
      }}
    }}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as config_home:
            output = run_quickshell(qml, config_home=Path(config_home), timeout=10)
        require_no_qml_errors(output)
        row = parse_behave(output)[-1]
        self.assertTrue(row["absent"], output[-3000:])
        self.assertTrue(row["loaded"])
        self.assertTrue(row["same"])
        self.assertFalse(row["runtimeEnabled"])
        self.assertFalse(row["animations"])
        self.assertGreater(row["vhsZ"], row["bokehZ"])


if __name__ == "__main__":
    unittest.main()
