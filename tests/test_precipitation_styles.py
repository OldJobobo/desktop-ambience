from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from qml_harness import HAVE_SESSION, parse_behave, qml_url, require_no_qml_errors, run_quickshell


ROOT = Path(__file__).resolve().parents[1]

RAIN = {
    "enabled": True, "intensity": 0.72, "speed": 0.62,
    "precipitationStyle": "rain", "dropCount": 180, "slant": 0.08,
    "accentBlend": 0.42, "vignette": True, "mistAmount": 0.34,
    "splashAmount": 0.38, "flakeSize": 6, "flutterAmount": 0.58,
    "flakeDetail": "mixed",
}
SNOW = {**RAIN, "precipitationStyle": "snow", "dropCount": 120,
        "slant": -0.12, "flakeSize": 8, "flutterAmount": 0.68,
        "flakeDetail": "mixed"}


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_adapter_selects_only_known_components_and_keeps_visuals_in_style_files():
    adapter = read("effects/RainfallEffect.qml")
    rain = read("effects/RainPrecipitationStyle.qml")
    snow = read("effects/SnowPrecipitationStyle.qml")
    assert adapter.count("Loader {") == 1
    assert adapter.count("RainPrecipitationStyle {") == 1
    assert adapter.count("SnowPrecipitationStyle {") == 1
    assert "configuredStyle: String(overlaySettings.precipitationStyle)" in adapter
    assert 'selectedStyle: configuredStyle === "snow" ? "snow" : "rain"' in adapter
    assert 'sourceComponent: root.selectedStyle === "snow" ? snowStyleComponent : rainStyleComponent' in adapter
    assert "Repeater {" not in adapter
    assert "NumberAnimation" not in adapter
    assert "rainWindow" not in adapter
    assert "rainDropRepeater" in rain
    assert "flakeRepeater" in snow


def test_rain_extraction_preserves_visual_math_and_snow_uses_one_bounded_clock():
    rain = read("effects/RainPrecipitationStyle.qml")
    snow = read("effects/SnowPrecipitationStyle.qml")
    for token in (
        "model: root.dropCount",
        "model: Math.max(24, Math.round(rainWindow.width / 34))",
        "model: Math.max(12, Math.round(root.dropCount * 0.18))",
        "model: Math.round(root.dropCount * root.splashAmount * 0.18)",
        "initialProgress: root.seededNoise(seed + 11)",
        "initialY: -dropLength + initialProgress * (rainWindow.height + dropLength * 2)",
        "duration: drop.startupComplete ? drop.fallDuration : drop.startupDuration",
        "running: root.effectVisible && !root.reducedMotion",
    ):
        assert token in rain
    assert snow.count("FrameAnimation {") == 1
    assert snow.count("NumberAnimation") == 0
    assert "targetUpdatesPerSecond: 30" in snow
    assert "model: Math.max(0, root.dropCount)" in snow
    assert "simulationRevision += 1" in snow
    assert "accumulatedFrameTime = Math.min(maximumFrameDelta" in snow
    assert "root.visualTime" in snow
    assert "seededNoise" in snow
    assert 'flakeDetail === "crystal"' in snow
    assert 'flakeDetail !== "mixed"' in snow
    assert "detailPrimitiveCount: flakeCount + crystalFlakeCount * 3" in snow


def test_internal_styles_have_no_forbidden_resource_or_unbounded_model_owners():
    for path in ("effects/RainfallEffect.qml", "effects/RainPrecipitationStyle.qml",
                 "effects/SnowPrecipitationStyle.qml"):
        source = read(path)
        for forbidden in ("Process {", "FileView {", "CursorTracker", "ParticleSystem",
                          "ListModel", "Canvas {", "Timer {"):
            assert forbidden not in source, (path, forbidden)
        assert "AmbienceSettings" not in source
        assert "EffectRegistry" not in source
    snow = read("effects/SnowPrecipitationStyle.qml")
    assert "push(" not in snow
    assert "createObject" not in snow
    assert "destroy()" not in snow
    panel = read("Panel.qml")
    assert "selectedStyle: rainfall.selectedStyle" in panel
    assert "autonomousMotionRunning: rainfall.autonomousMotionRunning" in panel


def test_extracted_rain_is_pixel_exact_and_has_current_runtime_samples():
    parity = json.loads(read("docs/release/evidence/rainfall-extraction-parity.json"))
    assert parity["isolatedConfig"] is True
    assert parity["liveSettingsModified"] is False
    assert parity["staticPixelExact"] is True
    assert set(parity["images"]) == {"rainfall-static.png", "rainfall-animated.png"}
    for image in parity["images"].values():
        assert image["changedPixels"] == 0
        assert image["baselineSha256"] == image["extractedSha256"]
        assert image["maximumChannelDelta"] == 0

    performance = json.loads(read("docs/performance/evidence/rainfall-post-extraction.json"))
    assert performance["isolatedConfig"] is True
    assert performance["liveSettingsModified"] is False
    assert performance["cases"] == ["rainfall"]
    assert performance["durationMs"] == 3000
    assert performance["repetitions"] == 3
    assert {row["outputs"] for row in performance["results"]} == {1, 3}
    assert len(performance["results"]) == 6
    assert all(170 <= row["frameCount"] <= 190 for row in performance["results"])
    assert all(15 <= row["meanFrameMs"] <= 18 for row in performance["results"])


def test_installed_runtime_evidence_selects_shared_clock_at_maximum_population():
    evidence = json.loads(read("docs/performance/evidence/snow-clock-selection.json"))
    assert evidence["machineLocalDirectionalEvidence"] is True
    assert evidence["isolatedConfig"] is True
    assert evidence["liveSettingsModified"] is False
    assert evidence["flakeCount"] == 320
    assert evidence["perFlakeAnimationCount"] == 960
    assert evidence["sharedClockCount"] == 1
    assert evidence["sharedClockTargetUpdatesPerSecond"] == 30
    assert evidence["repetitions"] == 3
    assert evidence["selectedStrategy"] == "sharedClock"
    assert evidence["medianCpuPercent"]["sharedClock"] < evidence["medianCpuPercent"]["perFlake"]
    assert len(evidence["results"]) == 6
    for row in evidence["results"]:
        assert row["flakeCount"] == 320
        assert 55 <= row["framesPerSecond"] <= 65
        if row["mode"] == "sharedClock":
            assert 20 <= row["sharedUpdates"] / (evidence["durationMs"] / 1000) <= 31
        else:
            assert row["sharedUpdates"] == 0
    harness = read("tests/live_snow_clock_benchmark.py")
    assert 'os.environ.get("JOBO_AMBIENCE_SNOW_CLOCK_BENCHMARK") != "1"' in harness
    assert 'run(["hyprctl", "output", "create", "headless", output_name])' in harness
    assert 'run(["hyprctl", "output", "remove", output_name], check=False)' in harness


@unittest.skipUnless(HAVE_SESSION, "needs a quickshell binary and a Wayland session")
class PrecipitationStyleBehaviorTests(unittest.TestCase):
    def test_reduced_motion_snow_is_deterministic_distributed_and_bounded(self):
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  Item {{
    width: 800; height: 480
    Loader {{ id: first; anchors.fill: parent; source: "{qml_url('effects/RainfallEffect.qml')}" }}
    Loader {{ id: second; anchors.fill: parent; source: "{qml_url('effects/RainfallEffect.qml')}" }}
  }}
  Timer {{
    interval: 120; running: first.item !== null && second.item !== null
    onTriggered: {{
      first.item.effectSettings = {json.dumps(SNOW)}
      second.item.effectSettings = {json.dumps(SNOW)}
      first.item.reducedMotion = true
      second.item.reducedMotion = true
      Qt.callLater(function() {{ probe.start() }})
    }}
  }}
  Timer {{
    id: probe; interval: 80
    onTriggered: {{
      var a = []
      var b = []
      for (var i = 0; i < first.item.snowFlakeCount; i++) {{
        a.push(first.item.snowFlakeSnapshot(i))
        b.push(second.item.snowFlakeSnapshot(i))
      }}
      console.log("BEHAVE " + JSON.stringify({{
        selected: first.item.selectedStyle,
        loadedName: first.item.loadedStyleName,
        loadedCount: first.item.loadedStyleCount,
        generation: first.item.styleGeneration,
        autonomous: first.item.autonomousMotionRunning,
        updates: first.item.snowClockUpdateCount,
        count: first.item.snowFlakeCount,
        crystals: first.item.snowCrystalCount,
        primitives: first.item.snowPrimitiveCount,
        first: a,
        second: b
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
        self.assertEqual(row["selected"], "snow")
        self.assertEqual(row["loadedName"], "snow")
        self.assertEqual(row["loadedCount"], 1)
        self.assertGreaterEqual(row["generation"], 2)
        self.assertFalse(row["autonomous"])
        self.assertEqual(row["updates"], 0)
        self.assertEqual(row["count"], 120)
        self.assertGreater(row["crystals"], 15)
        self.assertLess(row["crystals"], 50)
        self.assertEqual(row["primitives"], 120 + row["crystals"] * 3)
        self.assertEqual(row["first"], row["second"])
        snapshots = row["first"]
        progress = [float(item["initialProgress"]) for item in snapshots]
        self.assertLess(min(progress), 0.02)
        self.assertGreater(max(progress), 0.98)
        self.assertEqual({item["depthBand"] for item in snapshots}, {0, 1, 2})
        self.assertGreater(len({round(item["diameter"], 3) for item in snapshots}), 90)
        self.assertGreater(len({round(item["fallSpeed"], 3) for item in snapshots}), 90)
        self.assertGreater(len({round(item["flutterPhase"], 3) for item in snapshots}), 100)
        self.assertGreater(len({round(item["rotationSpeed"], 3) for item in snapshots}), 100)
        self.assertTrue(all(abs(item["currentY"] - item["initialY"]) < 1e-8 for item in snapshots))
        self.assertTrue(all(item["enabled"] is False and item["visible"] is True for item in snapshots))
        self.assertGreaterEqual(sum(item["initialY"] < 240 for item in snapshots), 45)
        self.assertGreaterEqual(sum(item["initialY"] >= 240 for item in snapshots), 45)

    def test_shared_snow_clock_moves_and_stops_for_every_runtime_gate(self):
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  id: root
  property real firstY: 0
  property real movedY: 0
  property real staticY: 0
  property real hiddenY: 0
  property real transparentY: 0
  property real transparentDelta: 0
  property real disabledY: 0
  property int activeUpdates: 0
  Item {{
    width: 800; height: 480
    Loader {{
      id: effect; anchors.fill: parent; source: "{qml_url('effects/RainfallEffect.qml')}"
      onLoaded: {{ item.effectSettings = {json.dumps(SNOW)}; first.start() }}
    }}
  }}
  Timer {{
    id: first; interval: 100
    onTriggered: {{ firstY = effect.item.snowFlakeSnapshot(0).currentY; moving.start() }}
  }}
  Timer {{
    id: moving; interval: 180
    onTriggered: {{
      movedY = effect.item.snowFlakeSnapshot(0).currentY
      activeUpdates = effect.item.snowClockUpdateCount
      effect.item.reducedMotion = true
      staticY = effect.item.snowFlakeSnapshot(0).currentY
      reduced.start()
    }}
  }}
  Timer {{
    id: reduced; interval: 150
    onTriggered: {{
      var reducedLater = effect.item.snowFlakeSnapshot(0).currentY
      effect.item.reducedMotion = false
      effect.item.runtimeEnabled = false
      hiddenY = effect.item.snowFlakeSnapshot(0).currentY
      hidden.start()
      root.staticY = Math.abs(reducedLater - staticY)
    }}
  }}
  Timer {{
    id: hidden; interval: 150
    onTriggered: {{
      var hiddenLater = effect.item.snowFlakeSnapshot(0).currentY
      effect.item.runtimeEnabled = true
      effect.item.globalOpacity = 0
      transparentY = effect.item.snowFlakeSnapshot(0).currentY
      transparent.start()
      root.hiddenY = Math.abs(hiddenLater - hiddenY)
    }}
  }}
  Timer {{
    id: transparent; interval: 150
    onTriggered: {{
      var transparentLater = effect.item.snowFlakeSnapshot(0).currentY
      root.transparentDelta = Math.abs(transparentLater - transparentY)
      effect.item.globalOpacity = 1
      var disabledSettings = Object.assign({{}}, effect.item.effectSettings)
      disabledSettings.enabled = false
      effect.item.effectSettings = disabledSettings
      disabledY = effect.item.snowFlakeSnapshot(0).currentY
      disabled.start()
    }}
  }}
  Timer {{
    id: disabled; interval: 150
    onTriggered: {{
      var disabledLater = effect.item.snowFlakeSnapshot(0).currentY
      console.log("BEHAVE " + JSON.stringify({{
        moved: Math.abs(movedY - firstY),
        reducedDelta: root.staticY,
        hiddenDelta: root.hiddenY,
        transparentDelta: root.transparentDelta,
        disabledDelta: Math.abs(disabledLater - disabledY),
        activeUpdates: activeUpdates,
        finalUpdates: effect.item.snowClockUpdateCount,
        autonomous: effect.item.autonomousMotionRunning
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
        self.assertGreater(row["moved"], 0.2)
        self.assertGreater(row["activeUpdates"], 2)
        self.assertLess(row["reducedDelta"], 1e-8)
        self.assertLess(row["hiddenDelta"], 1e-8)
        self.assertLess(row["transparentDelta"], 1e-8)
        self.assertLess(row["disabledDelta"], 1e-8)
        self.assertEqual(row["finalUpdates"], row["activeUpdates"])
        self.assertFalse(row["autonomous"])

    def test_repeated_style_switches_preserve_root_and_live_theme_settings(self):
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  id: root
  property var rootIdentity: null
  property var snowIdentity: null
  property color firstSnowColor: "transparent"
  property real firstDiameter: 0
  property var currentSettings: {json.dumps(RAIN)}
  QtObject {{
    id: theme
    property bool alternate: false
    function colorFor(name, fallback) {{
      var normal = {{background: "#101820", foreground: "#e8edf2", accent: "#55bbdd", color14: "#55bbdd", color15: "#ffffff"}}
      var changed = {{background: "#201018", foreground: "#fff0e8", accent: "#ff7744", color14: "#ff7744", color15: "#fff8ee"}}
      var colors = alternate ? changed : normal
      return colors[name] || fallback
    }}
  }}
  QtObject {{
    id: state
    property real opacity: 1
    property bool reduceMotion: true
    property var effects: ({{rainfall: root.currentSettings}})
  }}
  Item {{
    width: 800; height: 480
    Loader {{
      id: stack; anchors.fill: parent; source: "{qml_url('components/AmbienceStack.qml')}"
      onLoaded: {{
        item.settings = state
        item.theme = theme
        item.activeEffects = ["rainfall"]
        item.productionEffectsEnabled = true
        first.start()
      }}
    }}
  }}
  Timer {{
    id: first; interval: 150
    onTriggered: {{
      rootIdentity = stack.item.productionEffectObject("rainfall")
      var snow = Object.assign({{}}, root.currentSettings)
      snow.precipitationStyle = "snow"
      root.currentSettings = snow
      state.effects = ({{rainfall: snow}})
      second.start()
    }}
  }}
  Timer {{
    id: second; interval: 130
    onTriggered: {{
      var effect = stack.item.productionEffectObject("rainfall")
      snowIdentity = effect.loadedStyleObject
      firstSnowColor = effect.snowColor
      firstDiameter = effect.snowFlakeSnapshot(0).diameter
      theme.alternate = true
      var resized = Object.assign({{}}, root.currentSettings)
      resized.flakeSize = 15
      resized.flutterAmount = 0.9
      root.currentSettings = resized
      state.effects = ({{rainfall: resized}})
      third.start()
    }}
  }}
  Timer {{
    id: third; interval: 130
    onTriggered: {{
      var effect = stack.item.productionEffectObject("rainfall")
      var sameSnow = effect.loadedStyleObject === snowIdentity
      var colorChanged = String(effect.snowColor) !== String(firstSnowColor)
      var diameterChanged = effect.snowFlakeSnapshot(0).diameter > firstDiameter
      var rain = Object.assign({{}}, root.currentSettings)
      rain.precipitationStyle = "rain"
      root.currentSettings = rain
      state.effects = ({{rainfall: rain}})
      fourth.sameSnow = sameSnow
      fourth.colorChanged = colorChanged
      fourth.diameterChanged = diameterChanged
      fourth.start()
    }}
  }}
  Timer {{
    id: fourth; interval: 130
    property bool sameSnow: false
    property bool colorChanged: false
    property bool diameterChanged: false
    onTriggered: {{
      var snow = Object.assign({{}}, root.currentSettings)
      snow.precipitationStyle = "snow"
      root.currentSettings = snow
      state.effects = ({{rainfall: snow}})
      finalProbe.start()
    }}
  }}
  Timer {{
    id: finalProbe; interval: 130
    onTriggered: {{
      var effect = stack.item.productionEffectObject("rainfall")
      console.log("BEHAVE " + JSON.stringify({{
        sameRoot: effect === rootIdentity,
        sameSnowOnSettingsTheme: fourth.sameSnow,
        colorChanged: fourth.colorChanged,
        diameterChanged: fourth.diameterChanged,
        selected: effect.selectedStyle,
        loadedName: effect.loadedStyleName,
        loadedCount: effect.loadedStyleCount,
        generation: effect.styleGeneration,
        destroyed: effect.destroyedStyleCount,
        lastDestroyed: effect.lastDestroyedStyle,
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
        self.assertTrue(row["sameRoot"])
        self.assertTrue(row["sameSnowOnSettingsTheme"])
        self.assertTrue(row["colorChanged"])
        self.assertTrue(row["diameterChanged"])
        self.assertEqual(row["selected"], "snow")
        self.assertEqual(row["loadedName"], "snow")
        self.assertEqual(row["loadedCount"], 1)
        self.assertEqual(row["generation"], 4)
        self.assertEqual(row["destroyed"], 3)
        self.assertEqual(row["lastDestroyed"], "rain")
        self.assertEqual(row["activeCount"], 1)
        self.assertEqual(row["z"], 1)

    def test_removing_from_stack_destroys_adapter_and_readding_is_clean(self):
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  id: root
  property var firstIdentity: null
  QtObject {{
    id: state
    property real opacity: 1
    property bool reduceMotion: false
    property var effects: ({{rainfall: {json.dumps(SNOW)}}})
  }}
  Item {{
    width: 640; height: 360
    Loader {{
      id: stack; anchors.fill: parent; source: "{qml_url('components/AmbienceStack.qml')}"
      onLoaded: {{
        item.settings = state
        item.activeEffects = ["rainfall"]
        item.productionEffectsEnabled = true
        first.start()
      }}
    }}
  }}
  Timer {{
    id: first; interval: 150
    onTriggered: {{
      firstIdentity = stack.item.productionEffectObject("rainfall")
      stack.item.activeEffects = []
      removed.start()
    }}
  }}
  Timer {{
    id: removed; interval: 130
    onTriggered: {{
      var absent = stack.item.productionEffectObject("rainfall") === null
      var zero = stack.item.activeProductionEffectCount === 0
      stack.item.activeEffects = ["rainfall"]
      readded.absent = absent
      readded.zero = zero
      readded.start()
    }}
  }}
  Timer {{
    id: readded; interval: 150
    property bool absent: false
    property bool zero: false
    onTriggered: {{
      var current = stack.item.productionEffectObject("rainfall")
      console.log("BEHAVE " + JSON.stringify({{
        absent: absent,
        zero: zero,
        recreated: current !== null && current !== firstIdentity,
        style: current ? current.loadedStyleName : "",
        loadedCount: current ? current.loadedStyleCount : -1,
        activeCount: stack.item.activeProductionEffectCount
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
        self.assertTrue(row["absent"])
        self.assertTrue(row["zero"])
        self.assertTrue(row["recreated"])
        self.assertEqual(row["style"], "snow")
        self.assertEqual(row["loadedCount"], 1)
        self.assertEqual(row["activeCount"], 1)
