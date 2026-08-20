from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from qml_harness import HAVE_SESSION, parse_behave, qml_url, require_no_qml_errors, run_quickshell


DEFAULTS = {
    "enabled": True,
    "intensity": 0.72,
    "speed": 0.62,
    "dropCount": 180,
    "slant": 0.08,
    "mistAmount": 0.34,
    "splashAmount": 0.38,
    "accentBlend": 0.42,
    "vignette": True,
}


@unittest.skipUnless(HAVE_SESSION, "needs a quickshell binary and a Wayland session")
class RainfallBaselineBehaviorTests(unittest.TestCase):
    def test_defaults_pin_population_slant_mist_splash_and_full_height_startup(self):
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  Item {{
    width: 640; height: 360
    Loader {{
      id: effect; anchors.fill: parent
      source: "{qml_url('effects/RainfallEffect.qml')}"
      onLoaded: {{ item.effectSettings = {json.dumps(DEFAULTS)}; probe.start() }}
    }}
  }}
  Timer {{
    id: probe; interval: 80
    onTriggered: {{
      var snapshots = []
      for (var i = 0; i < effect.item.primaryDropCount; i++)
        snapshots.push(effect.item.primaryDropSnapshot(i))
      console.log("BEHAVE " + JSON.stringify({{
        windDrift: effect.item.windDrift,
        dropRotation: effect.item.dropRotation,
        mistBands: effect.item.mistBandCount,
        primaryDrops: effect.item.primaryDropCount,
        sheetDrops: effect.item.sheetDropCount,
        foregroundDrops: effect.item.foregroundDropCount,
        splashes: effect.item.splashCount,
        boundedParticles: effect.item.boundedParticleCount,
        autonomous: effect.item.autonomousMotionRunning,
        visualLayerEnabled: effect.item.visualLayerEnabled,
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
        self.assertAlmostEqual(row["windDrift"], 0.08 * 0.18)
        self.assertAlmostEqual(row["dropRotation"], 2 + 0.08 * 16)
        self.assertEqual(row["mistBands"], 5)
        self.assertEqual(row["primaryDrops"], 180)
        self.assertEqual(row["sheetDrops"], 24)
        self.assertEqual(row["foregroundDrops"], 32)
        self.assertEqual(row["splashes"], 12)
        self.assertEqual(row["boundedParticles"], 248)
        self.assertTrue(row["autonomous"])
        self.assertFalse(row["visualLayerEnabled"])
        snapshots = row["snapshots"]
        progress = [float(item["initialProgress"]) for item in snapshots]
        initial_y = [float(item["initialY"]) for item in snapshots]
        self.assertLess(min(progress), 0.01)
        self.assertGreater(max(progress), 0.99)
        self.assertGreaterEqual(sum(value < 180 for value in initial_y), 75)
        self.assertGreaterEqual(sum(value >= 180 for value in initial_y), 75)
        self.assertGreaterEqual(len({round(value, 3) for value in progress}), 160)
        self.assertTrue(all(item["enabled"] is False and item["visible"] is True for item in snapshots))

    def test_enabled_false_only_disables_input_while_motion_runs_and_lifecycle_stops_it(self):
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  id: root
  property real firstY: 0
  property real movingY: 0
  property real reducedY: 0
  property real reducedLaterY: 0
  property real hiddenY: 0
  property real transparentY: 0
  property bool movingClock: false
  property bool reducedClock: true
  property bool hiddenClock: true
  property bool transparentClock: true
  Item {{
    width: 640; height: 360
    Loader {{
      id: effect; anchors.fill: parent
      source: "{qml_url('effects/RainfallEffect.qml')}"
      onLoaded: {{ item.effectSettings = {json.dumps(DEFAULTS)}; first.start() }}
    }}
  }}
  Timer {{
    id: first; interval: 60
    onTriggered: {{
      firstY = effect.item.primaryDropSnapshot(0).currentY
      movingClock = effect.item.autonomousMotionRunning
      moving.start()
    }}
  }}
  Timer {{
    id: moving; interval: 160
    onTriggered: {{
      movingY = effect.item.primaryDropSnapshot(0).currentY
      effect.item.reducedMotion = true
      reducedY = effect.item.primaryDropSnapshot(0).currentY
      reduced.start()
    }}
  }}
  Timer {{
    id: reduced; interval: 160
    onTriggered: {{
      reducedLaterY = effect.item.primaryDropSnapshot(0).currentY
      reducedClock = effect.item.autonomousMotionRunning
      effect.item.reducedMotion = false
      effect.item.runtimeEnabled = false
      hiddenY = effect.item.primaryDropSnapshot(0).currentY
      hidden.start()
    }}
  }}
  Timer {{
    id: hidden; interval: 160
    onTriggered: {{
      var hiddenLaterY = effect.item.primaryDropSnapshot(0).currentY
      hiddenClock = effect.item.autonomousMotionRunning
      effect.item.runtimeEnabled = true
      effect.item.globalOpacity = 0
      transparentY = effect.item.primaryDropSnapshot(0).currentY
      transparent.start()
      root.hiddenY = Math.abs(hiddenLaterY - hiddenY)
    }}
  }}
  Timer {{
    id: transparent; interval: 160
    onTriggered: {{
      var transparentLaterY = effect.item.primaryDropSnapshot(0).currentY
      transparentClock = effect.item.autonomousMotionRunning
      console.log("BEHAVE " + JSON.stringify({{
        moved: Math.abs(movingY - firstY),
        reducedDelta: Math.abs(reducedLaterY - reducedY),
        hiddenDelta: root.hiddenY,
        transparentDelta: Math.abs(transparentLaterY - transparentY),
        movingClock: movingClock,
        reducedClock: reducedClock,
        hiddenClock: hiddenClock,
        transparentClock: transparentClock,
        visualLayerEnabled: effect.item.visualLayerEnabled,
        descendantEnabled: effect.item.primaryDropSnapshot(0).enabled
      }}))
      Qt.quit()
    }}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as config_home:
            output = run_quickshell(qml, config_home=Path(config_home), timeout=12)
        require_no_qml_errors(output)
        row = parse_behave(output)[-1]
        self.assertGreater(row["moved"], 1)
        self.assertLess(row["reducedDelta"], 0.001)
        self.assertLess(row["hiddenDelta"], 0.001)
        self.assertLess(row["transparentDelta"], 0.001)
        self.assertTrue(row["movingClock"])
        self.assertFalse(row["reducedClock"])
        self.assertFalse(row["hiddenClock"])
        self.assertFalse(row["transparentClock"])
        self.assertFalse(row["visualLayerEnabled"])
        self.assertFalse(row["descendantEnabled"])

    def test_stack_preserves_rainfall_root_identity_across_style_payload_and_reorder(self):
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  id: root
  property var identity: null
  property var rainfallSettings: {json.dumps(DEFAULTS)}
  QtObject {{
    id: state
    property real opacity: 1
    property bool reduceMotion: false
    property var effects: ({{
      rainfall: root.rainfallSettings,
      filmGrain: {{enabled: true, intensity: 0.2, speed: 1, grainCount: 20, grainSize: 1, accentBlend: 0}}
    }})
  }}
  Item {{
    width: 640; height: 360
    Loader {{
      id: stack; anchors.fill: parent
      source: "{qml_url('components/AmbienceStack.qml')}"
      onLoaded: {{
        item.settings = state
        item.activeEffects = ["rainfall", "filmGrain"]
        item.productionEffectsEnabled = true
        first.start()
      }}
    }}
  }}
  Timer {{
    id: first; interval: 140
    onTriggered: {{
      identity = stack.item.productionEffectObject("rainfall")
      var nextRain = Object.assign({{}}, root.rainfallSettings)
      nextRain.precipitationStyle = "snow"
      nextRain.slant = -0.2
      root.rainfallSettings = nextRain
      state.effects = Object.assign({{}}, state.effects, {{rainfall: nextRain}})
      stack.item.activeEffects = ["filmGrain", "rainfall"]
      second.start()
    }}
  }}
  Timer {{
    id: second; interval: 160
    onTriggered: {{
      var current = stack.item.productionEffectObject("rainfall")
      console.log("BEHAVE " + JSON.stringify({{
        sameObject: identity === current,
        slant: current.slant,
        activeCount: stack.item.activeProductionEffectCount,
        z: stack.item.zForEffect("rainfall")
      }}))
      Qt.quit()
    }}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as config_home:
            output = run_quickshell(qml, config_home=Path(config_home), timeout=12)
        require_no_qml_errors(output)
        row = parse_behave(output)[-1]
        self.assertTrue(row["sameObject"])
        self.assertEqual(row["slant"], -0.2)
        self.assertEqual(row["activeCount"], 2)
        self.assertEqual(row["z"], 1)
