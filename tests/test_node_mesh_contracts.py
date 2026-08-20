from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_node_mesh_registry_schema_is_complete_opt_in_and_metadata_driven():
    registry = read("services/EffectRegistry.js")
    settings = read("services/AmbienceSettings.qml")
    node_block = registry.split('id: "nodeMesh", label: "Node Mesh"', 1)[1].split("\n  }\n]", 1)[0]

    for setting in (
        'enabled: boolField(true)', 'intensity: realField(0.48, 0, 1)',
        'speed: realField(0.7, 0.15, 4)', 'nodeCount: intField(54, 12, 120)',
        'nodeSize: realField(3, 1, 10)', 'connectionDistance: intField(132, 40, 260)',
        'lineWidth: realField(1, 0.5, 3)', 'lineOpacity: realField(0.3, 0, 1)',
        'driftAmount: realField(0.38, 0, 1)',
        'pointerMode: enumField("off", ["off", "attract", "repel"])',
        'mouseInfluence: realField(0.3, 0, 1)',
        'nodeColorRole: enumField("accent"', 'lineColorRole: enumField("color12"',
    ):
        assert setting in node_block
    for role in ("accent", "foreground", "color09", "color10", "color11", "color12", "color13", "color14"):
        assert f'"{role}"' in node_block
    for key in (
        "enabled", "intensity", "speed", "nodeCount", "nodeSize", "connectionDistance",
        "lineWidth", "lineOpacity", "driftAmount", "pointerMode", "mouseInfluence",
        "nodeColorRole", "lineColorRole",
    ):
        assert f'{key}:' in registry.split("var effectFieldLabels", 1)[1]
        assert f'{key}:' in registry.split("var effectFieldHints", 1)[1]
    assert 'activeEffects: ["trackingLines"]' in settings
    assert 'activeEffects: ["trackingLines", "nodeMesh"]' not in settings


def test_node_mesh_uses_selected_bounded_shape_simulation_contract():
    effect = read("effects/NodeMeshEffect.qml")
    selected = json.loads(read("tests/prototypes/node-mesh/renderer-contract.json"))

    assert selected["selectedRenderer"] == "shape"
    assert effect.count("FrameAnimation {") == 1
    assert effect.count("Repeater {") == 1
    assert effect.count("Shape {") == 1
    assert effect.count("ShapePath {") == 8
    assert effect.count("PathMultiline {") == 8
    assert "Canvas" not in effect
    assert "Timer {" not in effect
    assert "Process {" not in effect
    assert "FileView" not in effect
    assert "Particle" not in effect
    assert "property var nodes: []" in effect
    assert "property var edges: []" in effect
    assert "property int simulationRevision: 0" in effect
    assert "simulationRevision += 1" in effect
    assert "readonly property int targetUpdatesPerSecond: 30" in effect
    assert "readonly property int maximumNeighborsPerNode: 4" in effect
    assert "Math.floor(acceptedNodeCount * maximumNeighborsPerNode / 2)" in effect
    assert "readonly property int opacityBucketCount: 8" in effect
    assert "pathGroups = groups" in effect
    assert "createObject" not in effect
    assert "var grid = {}" in effect
    assert "otherIndex <= index" in effect
    assert "degrees[candidate.a] >= maximumNeighborsPerNode" in effect
    assert "degrees[candidate.b] >= maximumNeighborsPerNode" in effect
    assert "model: root.acceptedNodeCount" in effect
    assert effect.count("var revision = root.simulationRevision") == 2


def test_node_mesh_lifecycle_pointer_and_clamp_contracts_are_explicit():
    effect = read("effects/NodeMeshEffect.qml")
    for property_name in (
        "effectSettings", "globalOpacity", "reducedMotion", "theme", "targetScreen",
        "cursorTracker", "runtimeEnabled", "runtimeIntensity",
    ):
        assert f"property var {property_name}" in effect or f"property bool {property_name}" in effect \
            or f"property real {property_name}" in effect
    assert "readonly property bool effectVisible" in effect
    assert "readonly property bool cursorOwned" in effect
    assert "readonly property bool pointerForceActive" in effect
    assert "readonly property bool simulationRunning" in effect
    assert 'pointerMode !== "off"' in effect
    assert "rawCursorLocalX >= 0" in effect
    assert "rawCursorLocalX < width" in effect
    assert 'screenOrigin(targetScreen, "x")' in effect
    assert 'screenOrigin(targetScreen, "y")' in effect
    assert "readonly property real maximumFrameDelta: 0.05" in effect
    assert "readonly property real maximumPointerAcceleration: 90" in effect
    assert "readonly property real maximumNodeVelocity: 96" in effect
    assert "readonly property real maximumFrameDisplacement: 6" in effect
    assert 'pointerMode === "repel" ? -1 : 1' in effect
    assert "onReducedMotionChanged" in effect
    assert "onSimulationRunningChanged" in effect
    assert "running: root.simulationRunning" in effect
    assert "if (!pointerForceActive)" in effect
    assert "if (rawFrameTime > maximumFrameDelta)" in effect
    assert "accumulatedFrameTime = 0" in effect
    assert "integrate(interval)" in effect


def test_node_mesh_visual_performance_and_settings_matrices_are_complete():
    visual = read("tests/live_phase6_visual.py")
    performance = read("tests/live_phase7_performance.py")
    settings_behavior = read("tests/test_qml_behavior_phase4_settings.py")
    fullscreen = read("tests/live_phase6_fullscreen.py")
    multi_output = read("tests/live_node_mesh_multi_output_visual.py")
    for case_id in (
        "nodeMesh", "nodeMeshMinimum", "nodeMeshMaximum", "nodeMeshShortDistance",
        "nodeMeshLongDistance", "nodeMeshLowOpacity", "nodeMeshHighOpacity",
        "nodeMeshPointerOff", "nodeMeshAttractCenter", "nodeMeshAttractEdge",
        "nodeMeshRepelCenter", "nodeMeshRepelEdge", "nodeMeshReducedMotion",
        "nodeMeshBackground", "nodeMeshForeground", "nodeMeshThemeSwitch",
    ):
        assert case_id in visual
    for case_id in (
        "nodeMeshStatic", "nodeMeshDefault", "nodeMeshMaximum", "nodeMeshPointerOff",
        "nodeMeshPointerAttract", "nodeMeshPointerRepel", "nodeMeshHidden",
        "nodeMeshFullscreenSuppressed",
    ):
        assert case_id in performance
    for metric in (
        "updateDelta", "paintDelta", "nodeCount", "edgeCount", "pathCount",
        "pointerOwnedOutputs", "pointerActiveOutputs", "cursorLaunchCount",
    ):
        assert metric in performance
    assert 'windowLoader.item.addEffect("nodeMesh")' in settings_behavior
    assert 'window.fieldsFor("nodeMesh")' in settings_behavior
    assert 'self.assertNotIn("nodeMesh"' in settings_behavior
    assert '"activeEffects": ["bokeh", "nodeMesh"]' in fullscreen
    assert '"nodeMeshIdentityPreservedAcrossPresentation": True' in fullscreen
    assert '"nodeMeshStoppedWhileSuppressed": True' in fullscreen
    assert '"singleOutputPointerOwnership"' in multi_output
    assert '"screenshotOutputAssignmentMatrix"' in multi_output
    assert '"swappedCaptureAssignmentRejected"' in multi_output
    assert "assignment_matrix != expected_assignment" in multi_output
    assert "swapped compositor captures were not rejected" in multi_output
    assert 'configure_output(OUTPUTS[0], -3840, 0)' in multi_output
    assert 'configure_output(OUTPUTS[1], -1920, 180)' in multi_output


def test_stack_lazy_loads_and_injects_node_mesh_without_replacing_shared_services():
    stack = read("components/AmbienceStack.qml")
    panel = read("Panel.qml")
    assert '"nodeMesh"' in stack
    assert "id: nodeMeshComponent" in stack
    assert "NodeMeshEffect {" in stack
    assert "id: nodeMeshLoader" in stack
    assert 'active: root.nodeMeshResident()' in stack
    assert 'return productionEffectsEnabled && stackIndex("nodeMesh") >= 0' in stack
    assert 'loader !== nodeMeshLoader || root.settingsFor("nodeMesh").enabled === true' in stack
    assert 'effectSettings: root.settingsFor("nodeMesh")' in stack
    assert "nodeMesh: nodeMeshLoader" in stack
    assert "targetScreen: root.targetScreen" in stack
    assert "cursorTracker: root.cursorTracker" in stack
    assert panel.count("CursorTracker {") == 1
    assert "readonly property bool nodeMeshRequested" in panel
    assert 'normalizedOrder().indexOf("nodeMesh") >= 0' in panel
    assert 'String(nodeMeshSettings.pointerMode) !== "off"' in panel
    assert "tacticalGridRequested || nodeMeshRequested" in panel
    assert "pollIntervalMs: root.tacticalGridRequested || root.nodeMeshRequested ? 60 : 120" in panel
    assert "cursorOwned: nodeMesh.cursorOwned" in panel
    assert "nodeMesh: root.nodeMeshRequested" in panel
