from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_phase6_orchestrator_runs_complete_release_matrix():
    script = read("scripts/check-phase6.sh")
    assert "JOBO_AMBIENCE_LIVE_PHASE6" in script
    for command in (
        "./scripts/check.sh",
        "tests/live_phase6_lifecycle.py",
        "tests/live_phase6_output_modes.py",
        "tests/live_phase6_fullscreen.py",
        "tests/live_phase6_visual.py",
        "tests/live_node_mesh_multi_output_visual.py",
        "tests/live_precipitation_multi_output_visual.py",
        "tests/live_node_mesh_pixel_probe.py",
    ):
        assert command in script
    assert "docs/release/evidence/$version" in script
    assert "write_versioned_json" in script
    for artifact in (
        "rainfall-extraction-parity.json",
        "node-mesh-pixels.json",
        "node-mesh-multi-output.json",
        "precipitation-multi-output.json",
    ):
        assert artifact in script


def test_versioned_release_evidence_is_durable_and_matches_manifest_version():
    import json

    version = json.loads(read("manifest.json"))["version"]
    paths = [
        f"docs/performance/evidence/{version}/phase7-performance.json",
        f"docs/release/evidence/{version}/lifecycle-hardware.json",
        f"docs/release/evidence/{version}/output-modes.json",
        f"docs/release/evidence/{version}/fullscreen.json",
        f"docs/release/evidence/{version}/visual-performance.json",
        f"docs/release/evidence/{version}/rainfall-extraction-parity.json",
        f"docs/release/evidence/{version}/node-mesh-pixels.json",
        f"docs/release/evidence/{version}/node-mesh-multi-output.json",
        f"docs/release/evidence/{version}/precipitation-multi-output.json",
    ]
    for path in paths:
        payload = json.loads(read(path))
        assert payload["pluginVersion"] == version, path
    visual = json.loads(read(f"docs/release/evidence/{version}/visual-performance.json"))
    assert visual["rainExtractionParityEvidence"] == "rainfall-extraction-parity.json"


def test_phase6_live_checks_are_opt_in_and_restore_temporary_resources():
    visual = read("tests/live_phase6_visual.py")
    fullscreen = read("tests/live_phase6_fullscreen.py")
    lifecycle = read("tests/live_phase6_lifecycle.py")
    output_modes = read("tests/live_phase6_output_modes.py")
    node_mesh_multi = read("tests/live_node_mesh_multi_output_visual.py")
    for source in (visual, fullscreen, lifecycle, output_modes, node_mesh_multi):
        assert 'os.environ.get("JOBO_AMBIENCE_LIVE_PHASE6") != "1"' in source
        assert "docs/release/evidence" in source
    assert 'run(["hyprctl", "output", "remove", output_name], check=False)' in visual
    assert 'run(["hyprctl", "output", "remove", output_name], check=False)' in fullscreen
    assert "liveSettingsModified" in visual
    assert "liveSettingsModified" in fullscreen
    assert "liveSettingsModified" in lifecycle
    assert "configure(\n            physical_target,\n            original_mode" in output_modes
    assert 'run(["hyprctl", "output", "remove", headless_name], check=False)' in output_modes
    assert 'run(["hyprctl", "output", "remove", name], check=False)' in node_mesh_multi
    assert '"singleOutputPointerOwnership"' in node_mesh_multi
    assert '"screenshotsNonBlankAndDistinct"' in node_mesh_multi
    assert '"compositorPlacementVerified"' in node_mesh_multi
    assert '"swappedCaptureAssignmentRejected"' in node_mesh_multi
    assert "OUTPUT_MARKERS" in node_mesh_multi
    assert "assignment_matrix != expected_assignment" in node_mesh_multi
    assert 'raise AssertionError("multi-output Node Mesh screenshots are byte-identical")' in node_mesh_multi


def test_visual_matrix_covers_every_effect_vignette_stack_theme_and_performance():
    source = read("tests/live_phase6_visual.py")
    for case_id in (
        "auroraDrift", "cinematicLight", "crt", "dustMotes", "filmGrain",
        "godRays", "rainfall", "tacticalGrid", "trackingLines", "bokeh", "nodeMesh", "backgroundVignette",
        "threeEffectStack", "threeEffectStackThemeSwitch",
    ):
        assert case_id in source
    assert "FrameAnimation" in source
    assert "averageCpuPercent" in source
    assert "themeSwitchChangedPixels" in source
    assert "contact-sheet.webp" in source


def test_fullscreen_matrix_distinguishes_fake_and_real_fullscreen():
    source = read("tests/live_phase6_fullscreen.py")
    assert "set_fullscreen_state(address, 0, 0)" in source
    assert "set_fullscreen_state(address, 0, 2)" in source
    assert "set_fullscreen_state(address, 2, 2)" in source
    assert '"surfaceRemainedMapped": True' in source
    assert '"activeEffects": ["bokeh", "nodeMesh", "rainfall"]' in source
    assert '"nodeMeshIdentityPreservedAcrossPresentation": True' in source
    assert 'next.presentation = "background"' in source
    assert '"bokehIdentityPreservedAcrossPresentation": True' in source
    assert 'JOBO_AMBIENCE_TEST_OUTPUT' in source
    assert 'JOBO_AMBIENCE_TEST_WORKSPACE' in source
    assert 'workspace = "{configured_workspace}", follow = false' in source
    assert "Qt.WindowDoesNotAcceptFocus" in source


def test_output_matrix_covers_fractional_scale_rotation_and_refresh_restore():
    source = read("tests/live_phase6_output_modes.py")
    assert 'configure(headless, "1920x1080@60", 1.25, 1)' in source
    assert '"mixedRefreshRate"' in source
    assert '"restored": True' in source
    assert '"persistentHyprlandConfigModified": False' in source
