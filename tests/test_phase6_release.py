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
    ):
        assert command in script
    assert "docs/release/evidence/$version" in script


def test_phase6_live_checks_are_opt_in_and_restore_temporary_resources():
    visual = read("tests/live_phase6_visual.py")
    fullscreen = read("tests/live_phase6_fullscreen.py")
    lifecycle = read("tests/live_phase6_lifecycle.py")
    output_modes = read("tests/live_phase6_output_modes.py")
    for source in (visual, fullscreen, lifecycle, output_modes):
        assert 'os.environ.get("JOBO_AMBIENCE_LIVE_PHASE6") != "1"' in source
        assert "docs/release/evidence" in source
    assert 'run(["hyprctl", "output", "remove", output_name], check=False)' in visual
    assert 'run(["hyprctl", "output", "remove", output_name], check=False)' in fullscreen
    assert "liveSettingsModified" in visual
    assert "liveSettingsModified" in fullscreen
    assert "liveSettingsModified" in lifecycle
    assert "configure(\n            physical_target,\n            original_mode" in output_modes
    assert 'run(["hyprctl", "output", "remove", headless_name], check=False)' in output_modes


def test_visual_matrix_covers_every_effect_vignette_stack_theme_and_performance():
    source = read("tests/live_phase6_visual.py")
    for case_id in (
        "auroraDrift", "cinematicLight", "crt", "dustMotes", "filmGrain",
        "godRays", "rainfall", "trackingLines", "backgroundVignette",
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


def test_output_matrix_covers_fractional_scale_rotation_and_refresh_restore():
    source = read("tests/live_phase6_output_modes.py")
    assert 'configure(headless, "1920x1080@60", 1.25, 1)' in source
    assert '"mixedRefreshRate"' in source
    assert '"restored": True' in source
    assert '"persistentHyprlandConfigModified": False' in source
