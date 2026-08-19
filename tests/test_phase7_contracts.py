from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_cursor_sampling_has_one_panel_owned_runtime_owner():
    panel = read("Panel.qml")
    stack = read("components/AmbienceStack.qml")
    dust = read("effects/DustMotesEffect.qml")
    tracker = read("services/CursorTracker.qml")

    assert panel.count("CursorTracker {") == 1
    assert "active: root.dustMotesRequested && root.paintAllowedSurfaceCount > 0" in panel
    assert panel.count("        cursorTracker: cursorTracker\n") == 1
    assert "property var cursorTracker: null" in stack
    assert "cursorTracker: root.cursorTracker" in stack
    assert "property var cursorTracker: null" in dust
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
    assert "paintAllowedSurfaceCount > 0" in panel
    assert "onPaintAllowedChanged: root.recountPaintAllowedSurfaces()" in panel


def test_status_exposes_shared_cursor_tracker_health():
    panel = read("Panel.qml")
    tracker = read("services/CursorTracker.qml")
    assert "cursorTracker: cursorTracker.status()" in panel
    for field in ("active", "running", "healthy", "launchCount", "failureCount", "error"):
        assert f"{field}:" in tracker


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
        "godRays", "rainfall", "trackingLines", "backgroundVignette",
        "threeEffectStack",
    ):
        assert case_id in source
