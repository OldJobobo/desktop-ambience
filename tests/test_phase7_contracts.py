from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_cursor_sampling_has_one_panel_owned_runtime_owner():
    panel = read("Panel.qml")
    stack = read("components/AmbienceStack.qml")
    dust = read("effects/DustMotesEffect.qml")
    tracker = read("services/CursorTracker.qml")

    tactical = read("effects/TacticalGridEffect.qml")
    node_mesh = read("effects/NodeMeshEffect.qml")

    assert panel.count("CursorTracker {") == 1
    assert "active: root.cursorTrackingRequested && root.paintAllowedSurfaceCount > 0" in panel
    assert "tacticalGridRequested || nodeMeshRequested" in panel
    assert panel.count("        cursorTracker: sharedCursorTracker\n") == 1
    assert "property var cursorTracker: null" in stack
    assert stack.count("cursorTracker: root.cursorTracker") == 3
    assert "property var cursorTracker: null" in dust
    assert "property var cursorTracker: null" in tactical
    assert "property var cursorTracker: null" in node_mesh
    assert "Quickshell.Io" not in dust
    assert "Process {" not in dust
    assert "hyprctl" not in dust
    assert tracker.count("Process {") == 1
    assert '["hyprctl", "cursorpos", "-j"]' in tracker


def test_cursor_sampling_stops_for_hidden_reduced_or_fully_suppressed_effects():
    panel = read("Panel.qml")
    assert 'normalizedOrder().indexOf("dustMotes") >= 0' in panel
    assert "dustMotesSettings.enabled === true" in panel
    assert "dustMotesSettings.mouseReactive === true" in panel
    assert "!ambienceSettings.reduceMotion" in panel
    assert 'normalizedOrder().indexOf("tacticalGrid") >= 0' in panel
    assert "tacticalGridSettings.enabled === true" in panel
    assert "|| tacticalGridRequested || nodeMeshRequested" in panel
    assert 'normalizedOrder().indexOf("nodeMesh") >= 0' in panel
    assert 'String(nodeMeshSettings.pointerMode) !== "off"' in panel
    assert "paintAllowedSurfaceCount > 0" in panel
    assert "onPaintAllowedChanged: root.recountPaintAllowedSurfaces()" in panel


def test_status_exposes_shared_cursor_tracker_health():
    panel = read("Panel.qml")
    tracker = read("services/CursorTracker.qml")
    assert "cursorTracker: sharedCursorTracker.status()" in panel
    for field in (
        "active", "running", "healthy", "launchCount", "failureCount",
        "hasCursorSample", "cursorX", "cursorY", "displayCursorX", "displayCursorY",
        "velocityX", "velocityY", "kick", "error",
    ):
        assert f"{field}:" in tracker


def test_mouse_influence_keeps_positional_repulsion_after_movement_impulse_decays():
    dust = read("effects/DustMotesEffect.qml")
    assert "root.hasCursorSample" in dust
    assert "root.cursorX >= 0" not in dust
    assert "root.cursorY >= 0" not in dust
    assert "root.cursorKick > 0" not in dust
    assert "dustWindow.cursorLocalX < dustWindow.width" in dust
    assert "dustWindow.cursorLocalY < dustWindow.height" in dust


def test_tactical_grid_uses_bounded_primitives_and_injected_pointer_state():
    tactical = read("effects/TacticalGridEffect.qml")
    assert tactical.count("Repeater {") == 2
    assert "cursorLocalX: cursorX - screenOriginX" in tactical
    assert "cursorLocalY: cursorY - screenOriginY" in tactical
    assert "cursorInsideOutput" in tactical
    assert "parallaxOffsetX" in tactical
    assert "parallaxOffsetY" in tactical
    assert "width: parent.width" in tactical
    assert "height: parent.height" in tactical
    assert "readonly property real renderedGridX: gridLayer.x" in tactical
    assert "rawCursorLocalX < width" in tactical
    assert "rawCursorLocalY < height" in tactical
    assert "FrameAnimation" in tactical
    for style in ("crosshair", "brackets", "ring", "diamond"):
        assert f'root.reticleStyle === "{style}"' in tactical or f'id: {style[:-1] if style.endswith("s") else style}Reticle' in tactical
    assert "Process {" not in tactical
    assert "FileView" not in tactical
    assert "Canvas" not in tactical


def test_renderers_wait_for_stable_geometry_before_first_animation_cycle():
    stack = read("components/AmbienceStack.qml")
    assert "property bool animationGeometryReady: false" in stack
    assert "readonly property bool rendererPaintEnabled: paintEnabled && animationGeometryReady" in stack
    assert "onWidthChanged: scheduleGeometryReady()" in stack
    assert "onHeightChanged: scheduleGeometryReady()" in stack
    assert "interval: 80" in stack
    assert stack.count("runtimeEnabled: root.rendererPaintEnabled && root.productionEffectsEnabled") == 11


def test_aurora_secondary_glows_start_at_their_animated_floor():
    aurora = read("effects/AuroraDriftEffect.qml")
    assert "readonly property real glowFloor:" in aurora
    assert "readonly property real glowPeak:" in aurora
    assert "opacity: glowFloor" in aurora
    assert "from: glow.glowFloor" in aurora
    assert "to: glow.glowPeak" in aurora
    assert "from: glow.glowPeak" in aurora
    assert "to: glow.glowFloor" in aurora
    assert "function restartStartupReveal()" in aurora
    assert "startupOpacity = reducedMotion ? 1 : 0.06" in aurora
    assert "opacity: root.effectiveIntensity * root.startupOpacity" in aurora
    assert 'property: "startupOpacity"' in aurora
    assert "to: 0.12" in aurora
    assert "to: 1" in aurora
    assert "initialDelay" not in aurora
    assert "PauseAnimation" not in aurora


def test_god_rays_start_together_from_their_animated_low_state():
    rays = read("effects/GodRaysEffect.qml")
    assert "initialDelay" not in rays
    assert "PauseAnimation" not in rays
    assert "readonly property real ambientPulse: root.shimmer" in rays
    assert "function restartStartupReveal()" in rays
    assert "opacity: root.effectiveIntensity * root.startupOpacity" in rays
    assert "property real motionClock: 0" in rays
    assert "FrameAnimation" in rays
    assert "frameTime * root.speed" in rays
    assert "property int allocatedRayCount: 0" in rays
    assert "model: root.allocatedRayCount" in rays
    assert "model: Math.max(3, Math.round(root.allocatedRayCount * 0.7))" in rays
    assert rays.count("property bool populationReady: false") == 2
    assert rays.count("Behavior on populationOpacity") == 2
    assert "Behavior on fanLane" in rays


def test_rainfall_seeds_full_length_loops_at_distributed_startup_phases():
    rain = read("effects/RainPrecipitationStyle.qml")
    assert "phaseOffset" not in rain
    assert rain.count("readonly property real initialProgress:") == 3
    assert rain.count("readonly property real initialY:") == 3
    assert rain.count("property bool startupComplete: false") == 3
    assert "drop.startupComplete ? -drop.dropLength : drop.initialY" in rain
    assert "rainSheet.startupComplete ? -rainSheet.sheetLength : rainSheet.initialY" in rain
    assert "foregroundDrop.startupComplete ? -foregroundDrop.dropLength : foregroundDrop.initialY" in rain
    visual = read("tests/live_phase6_visual.py")
    assert 'item.reducedMotion = caseId !== "rainfall" && caseId !== "tacticalGrid"' in visual
    assert '"rainfallStartupCoverage"' in visual
    assert "rainfall_top <= 0.01 or rainfall_bottom <= 0.01" in visual


def test_phase7_orchestrator_requires_performance_and_full_parity_matrices():
    script = read("scripts/check-phase7.sh")
    assert "JOBO_AMBIENCE_LIVE_PHASE7" in script
    assert "./scripts/check.sh" in script
    assert "tests/live_phase7_performance.py" in script
    assert "JOBO_AMBIENCE_LIVE_PHASE6=1 ./scripts/check-phase6.sh" in script


def test_phase7_performance_matrix_is_isolated_repeatable_and_revision_aware():
    source = read("tests/live_phase7_performance.py")
    assert 'os.environ.get("JOBO_AMBIENCE_LIVE_PHASE7") != "1"' in source
    assert 'env["XDG_CONFIG_HOME"]' in source
    assert 'env["XDG_STATE_HOME"]' in source
    assert 'run(["hyprctl", "output", "remove", name], check=False)' in source
    assert 'parser.add_argument("--target-root"' in source
    assert 'parser.add_argument("--repetitions"' in source
    for case_id in (
        "auroraDrift", "cinematicLight", "crt", "dustMotes", "filmGrain",
        "godRays", "rainfall", "tacticalGrid", "trackingLines", "bokeh", "nodeMesh", "backgroundVignette",
        "threeEffectStack",
    ):
        assert case_id in source
