from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from qml_harness import HAVE_SESSION, parse_behave, qml_url, require_no_qml_errors, run_quickshell


DEFAULTS = {
    "enabled": True,
    "intensity": 0.48,
    "speed": 0.7,
    "nodeCount": 54,
    "nodeSize": 3,
    "connectionDistance": 132,
    "lineWidth": 1,
    "lineOpacity": 0.3,
    "driftAmount": 0.38,
    "pointerMode": "off",
    "mouseInfluence": 0.3,
    "nodeColorRole": "accent",
    "lineColorRole": "color12",
}


@unittest.skipUnless(HAVE_SESSION, "needs a quickshell binary and a Wayland session")
class NodeMeshBehaviorTests(unittest.TestCase):
    def test_normalization_adds_defaults_without_activation_and_bounds_all_fields(self):
        source = {
            "version": 99,
            "activeEffects": ["bokeh", "trackingLines"],
            "effects": {
                "nodeMesh": {
                    "intensity": 7,
                    "speed": -1,
                    "nodeCount": 119.6,
                    "nodeSize": 99,
                    "connectionDistance": -8,
                    "lineWidth": 12,
                    "lineOpacity": -3,
                    "driftAmount": 9,
                    "pointerMode": "sideways",
                    "mouseInfluence": 4,
                    "nodeColorRole": "invalid",
                    "lineColorRole": "color14",
                    "futureMesh": {"kept": True},
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
      console.log("BEHAVE " + JSON.stringify({{
        defaults: service.item.normalize({{}}),
        normalized: service.item.normalize({json.dumps(source)})
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
        self.assertEqual(row["defaults"]["effects"]["nodeMesh"], DEFAULTS)
        self.assertNotIn("nodeMesh", row["defaults"]["activeEffects"])
        normalized = row["normalized"]
        self.assertEqual(normalized["activeEffects"], ["bokeh", "trackingLines"])
        self.assertEqual(normalized["futureRoot"], [1, None, False])
        mesh = normalized["effects"]["nodeMesh"]
        self.assertEqual(mesh["intensity"], 1)
        self.assertEqual(mesh["speed"], 0.15)
        self.assertEqual(mesh["nodeCount"], 120)
        self.assertEqual(mesh["nodeSize"], 10)
        self.assertEqual(mesh["connectionDistance"], 40)
        self.assertEqual(mesh["lineWidth"], 3)
        self.assertEqual(mesh["lineOpacity"], 0)
        self.assertEqual(mesh["driftAmount"], 1)
        self.assertEqual(mesh["pointerMode"], "off")
        self.assertEqual(mesh["mouseInfluence"], 1)
        self.assertEqual(mesh["nodeColorRole"], "accent")
        self.assertEqual(mesh["lineColorRole"], "color14")
        self.assertEqual(mesh["futureMesh"], {"kept": True})

    def test_reduced_motion_is_deterministic_static_and_edges_are_strictly_bounded(self):
        settings = dict(DEFAULTS)
        settings.update({"nodeCount": 120, "connectionDistance": 260, "driftAmount": 1,
                         "pointerMode": "attract", "mouseInfluence": 1})
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  Item {{
    width: 640; height: 360
    Loader {{ id: first; anchors.fill: parent; source: "{qml_url('effects/NodeMeshEffect.qml')}" }}
    Loader {{ id: second; anchors.fill: parent; source: "{qml_url('effects/NodeMeshEffect.qml')}" }}
  }}
  Timer {{
    interval: 160; running: true
    onTriggered: {{
      first.item.effectSettings = {json.dumps(settings)}
      second.item.effectSettings = {json.dumps(settings)}
      first.item.reducedMotion = true
      second.item.reducedMotion = true
      settle.start()
    }}
  }}
  Timer {{
    id: settle; interval: 120
    onTriggered: {{
      var firstNodes = []
      var secondNodes = []
      var edges = []
      for (var i = 0; i < first.item.acceptedNodeCount; i++) {{
        firstNodes.push(first.item.nodeSnapshot(i))
        secondNodes.push(second.item.nodeSnapshot(i))
      }}
      for (var j = 0; j < first.item.edgeCount; j++) edges.push(first.item.edgeSnapshot(j))
      console.log("BEHAVE " + JSON.stringify({{
        nodeCount: first.item.acceptedNodeCount,
        delegates: first.item.boundedDelegateCount,
        edgeCount: first.item.edgeCount,
        edgeCeiling: first.item.edgeCeiling,
        pathCount: first.item.shapePathCount,
        running: first.item.simulationRunning,
        updates: first.item.simulationUpdateCount,
        same: JSON.stringify(firstNodes) === JSON.stringify(secondNodes),
        nodes: firstNodes,
        edges: edges
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
        self.assertEqual(row["nodeCount"], 120, output[-3000:])
        self.assertEqual(row["delegates"], 120)
        self.assertLessEqual(row["edgeCount"], 240)
        self.assertEqual(row["edgeCeiling"], 240)
        self.assertEqual(row["pathCount"], 8)
        self.assertFalse(row["running"])
        self.assertEqual(row["updates"], 0)
        self.assertTrue(row["same"])
        self.assertTrue(all(node["x"] == node["initialX"] and node["y"] == node["initialY"]
                            for node in row["nodes"]))
        seen: set[tuple[int, int]] = set()
        degrees = [0] * 120
        for edge in row["edges"]:
            pair = (edge["a"], edge["b"])
            self.assertLess(edge["a"], edge["b"])
            self.assertNotIn(pair, seen)
            seen.add(pair)
            degrees[edge["a"]] += 1
            degrees[edge["b"]] += 1
            self.assertLess(edge["distance"], 260)
            self.assertGreater(edge["opacity"], 0)
            self.assertLessEqual(edge["opacity"], 1)
        self.assertLessEqual(max(degrees), 4)

    def test_pointer_ownership_negative_origins_force_direction_and_clamps(self):
        attract = dict(DEFAULTS)
        attract.update({"driftAmount": 0, "pointerMode": "attract", "mouseInfluence": 1})
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  QtObject {{ id: screen; property real x: -1920; property real y: -200 }}
  QtObject {{
    id: tracker
    property bool hasCursorSample: true
    property real cursorX: -1600
    property real cursorY: -20
    property real displayCursorX: -1600
    property real displayCursorY: -20
  }}
  Item {{
    width: 640; height: 360
    Loader {{
      id: effect; anchors.fill: parent; source: "{qml_url('effects/NodeMeshEffect.qml')}"
      onLoaded: {{
        item.effectSettings = {json.dumps(attract)}
        item.targetScreen = screen
        item.cursorTracker = tracker
        probe.start()
      }}
    }}
  }}
  Timer {{
    id: probe; interval: 120
    onTriggered: {{
      var ownedLocalX = effect.item.rawCursorLocalX
      var ownedLocalY = effect.item.rawCursorLocalY
      var attractForce = effect.item.pointerForceForPosition(220, 180)
      var attractMagnitude = Math.sqrt(attractForce.x * attractForce.x + attractForce.y * attractForce.y)
      var next = Object.assign({{}}, effect.item.effectSettings)
      next.pointerMode = "repel"
      effect.item.effectSettings = next
      var repelForce = effect.item.pointerForceForPosition(220, 180)
      var clampedDisplacement = effect.item.clampVector(1000, 1000, effect.item.maximumFrameDisplacement)
      var displacementMagnitude = Math.sqrt(clampedDisplacement.x * clampedDisplacement.x
        + clampedDisplacement.y * clampedDisplacement.y)
      tracker.cursorX = -100
      tracker.displayCursorX = -100
      var outsideOwned = effect.item.cursorOwned
      var outsideForce = effect.item.pointerForceForPosition(220, 180).active
      tracker.cursorX = Number.NaN
      tracker.displayCursorX = Number.NaN
      var invalid = effect.item.hasValidCursorSample
      effect.item.reducedMotion = true
      console.log("BEHAVE " + JSON.stringify({{
        reportedLocalX: ownedLocalX,
        reportedLocalY: ownedLocalY,
        attractX: attractForce.x,
        attractY: attractForce.y,
        attractMagnitude: attractMagnitude,
        repelX: repelForce.x,
        repelY: repelForce.y,
        outsideOwned: outsideOwned,
        outsideForce: outsideForce,
        invalidSampleAccepted: invalid,
        reducedRunning: effect.item.simulationRunning,
        displacementMagnitude: displacementMagnitude,
        maxAcceleration: effect.item.maximumPointerAcceleration,
        maxDisplacement: effect.item.maximumFrameDisplacement
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
        self.assertEqual(row["reportedLocalX"], 320)
        self.assertEqual(row["reportedLocalY"], 180)
        self.assertGreater(row["attractX"], 0, output[-3000:])
        self.assertAlmostEqual(row["attractY"], 0, delta=1e-6)
        self.assertLess(row["repelX"], 0)
        self.assertAlmostEqual(row["repelY"], 0, delta=1e-6)
        self.assertLessEqual(row["attractMagnitude"], row["maxAcceleration"] + 1e-6)
        self.assertFalse(row["outsideOwned"])
        self.assertFalse(row["outsideForce"])
        self.assertFalse(row["invalidSampleAccepted"])
        self.assertFalse(row["reducedRunning"])
        self.assertLessEqual(row["displacementMagnitude"], row["maxDisplacement"] + 1e-6)

    def test_frame_clock_accepts_at_most_thirty_updates_per_second(self):
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  id: root
  property int baseline: 0
  Item {{
    width: 640; height: 360
    Loader {{
      id: effect; anchors.fill: parent; source: "{qml_url('effects/NodeMeshEffect.qml')}"
      onLoaded: {{ item.effectSettings = {json.dumps(DEFAULTS)}; warmup.start() }}
    }}
  }}
  Timer {{
    id: warmup; interval: 180
    onTriggered: {{ root.baseline = effect.item.simulationUpdateCount; sample.start() }}
  }}
  Timer {{
    id: sample; interval: 1000
    onTriggered: {{
      var delta = effect.item.simulationUpdateCount - root.baseline
      console.log("BEHAVE " + JSON.stringify({{delta: delta,
        running: effect.item.simulationRunning, revision: effect.item.simulationRevision}}))
      Qt.quit()
    }}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as config_home:
            output = run_quickshell(qml, config_home=Path(config_home), timeout=10)
        require_no_qml_errors(output)
        row = parse_behave(output)[-1]
        self.assertTrue(row["running"], output[-3000:])
        self.assertGreaterEqual(row["delta"], 20)
        self.assertLessEqual(row["delta"], 31)
        self.assertGreater(row["revision"], row["delta"])

    def test_stack_preserves_identity_live_updates_and_stops_with_paint_suppression(self):
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  QtObject {{
    id: state
    property real opacity: 1
    property bool reduceMotion: false
    property var effects: ({{nodeMesh: {json.dumps(DEFAULTS)}}})
  }}
  QtObject {{
    id: theme
    property bool alternate: false
    function colorFor(name, fallback) {{
      var colors = alternate ? {{accent: "#ff3300", color12: "#22dd88", foreground: "#ffeecc"}}
        : {{accent: "#33ccff", color12: "#5577aa", foreground: "#eeeeee"}}
      return colors[name] || fallback
    }}
  }}
  Item {{
    width: 640; height: 360
    property var identity: null
    property var delegateIdentity: null
    property int stoppedAt: 0
    Loader {{
      id: stack; anchors.fill: parent; source: "{qml_url('components/AmbienceStack.qml')}"
      onLoaded: {{
        item.settings = state
        item.theme = theme
        item.activeEffects = []
        inactiveProbe.start()
      }}
    }}
    Timer {{
      id: inactiveProbe; interval: 80
      onTriggered: {{
        var absent = stack.item.productionEffectObject("nodeMesh") === null
        parent.propertyA = absent
        stack.item.activeEffects = ["nodeMesh"]
        activeProbe.start()
      }}
    }}
    property bool propertyA: false
    Timer {{
      id: activeProbe; interval: 360
      onTriggered: {{
        parent.identity = stack.item.productionEffectObject("nodeMesh")
        parent.delegateIdentity = parent.identity.nodeObject(0)
        var nodeSnapshot = parent.identity.nodeSnapshot(0)
        parent.propertyD = Math.abs(nodeSnapshot.x - nodeSnapshot.initialX) > 0.001
          && Math.abs(parent.delegateIdentity.currentX - nodeSnapshot.x) < 0.000001
        var initialColor = String(parent.identity.effectiveNodeColor)
        var initialUpdates = parent.identity.simulationUpdateCount
        theme.alternate = true
        var next = Object.assign({{}}, state.effects.nodeMesh)
        next.nodeSize = 5
        next.connectionDistance = 40
        next.lineColorRole = "foreground"
        state.effects = {{nodeMesh: next}}
        stack.item.activeEffects = ["trackingLines", "nodeMesh"]
        stack.item.paintEnabled = false
        parent.stoppedAt = parent.identity.simulationUpdateCount
        stoppedProbe.start()
        parent.propertyB = initialColor
        parent.propertyC = initialUpdates
      }}
    }}
    property string propertyB: ""
    property int propertyC: 0
    property bool propertyD: false
    Timer {{
      id: stoppedProbe; interval: 180
      onTriggered: {{
        var current = stack.item.productionEffectObject("nodeMesh")
        console.log("BEHAVE " + JSON.stringify({{
          absent: parent.propertyA,
          loaded: parent.identity !== null,
          same: parent.identity === current,
          sameDelegate: parent.delegateIdentity === current.nodeObject(0),
          delegateTrackedRevision: parent.propertyD,
          initialUpdates: parent.propertyC,
          stoppedAt: parent.stoppedAt,
          finalUpdates: current.simulationUpdateCount,
          running: current.simulationRunning,
          runtimeEnabled: current.runtimeEnabled,
          initialColor: parent.propertyB,
          reboundColor: String(current.effectiveNodeColor),
          nodeSize: current.nodeSize,
          connectionDistance: current.connectionDistance,
          pathCount: current.shapePathCount,
          nodeZ: stack.item.zForEffect("nodeMesh"),
          vhsZ: stack.item.zForEffect("trackingLines")
        }}))
        Qt.quit()
      }}
    }}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as config_home:
            output = run_quickshell(qml, config_home=Path(config_home), timeout=12)
        require_no_qml_errors(output)
        row = parse_behave(output)[-1]
        self.assertTrue(row["absent"], output[-3000:])
        self.assertTrue(row["loaded"])
        self.assertTrue(row["same"])
        self.assertTrue(row["sameDelegate"])
        self.assertTrue(row["delegateTrackedRevision"])
        self.assertGreater(row["initialUpdates"], 0)
        self.assertLessEqual(row["finalUpdates"], row["stoppedAt"] + 1)
        self.assertFalse(row["running"])
        self.assertFalse(row["runtimeEnabled"])
        self.assertNotEqual(row["initialColor"], row["reboundColor"])
        self.assertEqual(row["nodeSize"], 5)
        self.assertEqual(row["connectionDistance"], 40)
        self.assertEqual(row["pathCount"], 8)
        self.assertGreater(row["vhsZ"], row["nodeZ"])

    def test_stalled_frame_accepts_one_fixed_step_and_clears_backlog(self):
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  Item {{
    width: 640; height: 360
    Loader {{
      id: effect; anchors.fill: parent; source: "{qml_url('effects/NodeMeshEffect.qml')}"
      onLoaded: {{
        item.runtimeEnabled = false
        item.effectSettings = {json.dumps(DEFAULTS)}
        probe.start()
      }}
    }}
  }}
  Timer {{
    id: probe; interval: 100
    onTriggered: {{
      effect.item.runtimeEnabled = true
      var baseline = effect.item.simulationUpdateCount
      effect.item.acceptFrame(1.0)
      var afterStall = effect.item.simulationUpdateCount
      var backlogAfterStall = effect.item.accumulatedFrameTime
      effect.item.acceptFrame(1 / 60)
      var afterFirstNormal = effect.item.simulationUpdateCount
      effect.item.acceptFrame(1 / 60)
      var afterSecondNormal = effect.item.simulationUpdateCount
      console.log("BEHAVE " + JSON.stringify({{
        stallUpdates: afterStall - baseline,
        backlogAfterStall: backlogAfterStall,
        firstNormalUpdates: afterFirstNormal - afterStall,
        secondNormalUpdates: afterSecondNormal - afterFirstNormal
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
        self.assertEqual(row["stallUpdates"], 1, output[-3000:])
        self.assertEqual(row["backlogAfterStall"], 0)
        self.assertEqual(row["firstNormalUpdates"], 0)
        self.assertEqual(row["secondNormalUpdates"], 1)

    def test_enabled_toggle_preserves_resident_identity_and_stops_all_work(self):
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  QtObject {{
    id: state
    property real opacity: 1
    property bool reduceMotion: false
    property var effects: ({{nodeMesh: {json.dumps(DEFAULTS)}}})
  }}
  Item {{
    id: host; width: 640; height: 360
    property var identity: null
    property int disabledAt: 0
    Loader {{
      id: stack; anchors.fill: parent; source: "{qml_url('components/AmbienceStack.qml')}"
      onLoaded: {{
        item.settings = state
        item.activeEffects = ["nodeMesh"]
        activeProbe.start()
      }}
    }}
    Timer {{
      id: activeProbe; interval: 320
      onTriggered: {{
        host.identity = stack.item.productionEffectObject("nodeMesh")
        var disabled = Object.assign({{}}, state.effects.nodeMesh)
        disabled.enabled = false
        state.effects = {{nodeMesh: disabled}}
        host.disabledAt = host.identity.simulationUpdateCount
        disabledProbe.start()
      }}
    }}
    Timer {{
      id: disabledProbe; interval: 220
      onTriggered: {{
        var resident = stack.item.productionEffectObject("nodeMesh")
        host.propertyA = resident === host.identity
          && resident.simulationUpdateCount === host.disabledAt
          && !resident.simulationRunning && !resident.effectVisible
          && stack.item.activeProductionEffectCount === 0
        var enabled = Object.assign({{}}, state.effects.nodeMesh)
        enabled.enabled = true
        state.effects = {{nodeMesh: enabled}}
        enabledProbe.start()
      }}
    }}
    property bool propertyA: false
    Timer {{
      id: enabledProbe; interval: 240
      onTriggered: {{
        var current = stack.item.productionEffectObject("nodeMesh")
        console.log("BEHAVE " + JSON.stringify({{
          sameWhileDisabled: host.propertyA,
          sameAfterEnable: current === host.identity,
          runningAfterEnable: current.simulationRunning,
          updatesAfterEnable: current.simulationUpdateCount - host.disabledAt,
          activeCount: stack.item.activeProductionEffectCount
        }}))
        Qt.quit()
      }}
    }}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as config_home:
            output = run_quickshell(qml, config_home=Path(config_home), timeout=12)
        require_no_qml_errors(output)
        row = parse_behave(output)[-1]
        self.assertTrue(row["sameWhileDisabled"], output[-3000:])
        self.assertTrue(row["sameAfterEnable"])
        self.assertTrue(row["runningAfterEnable"])
        self.assertGreater(row["updatesAfterEnable"], 0)
        self.assertEqual(row["activeCount"], 1)


if __name__ == "__main__":
    unittest.main()
