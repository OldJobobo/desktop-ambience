from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def load(path: str) -> dict:
    return json.loads(read(path))


def test_visual_matrix_covers_complete_precipitation_review_at_negative_origin():
    visual = read("tests/live_phase6_visual.py")
    for case_id in (
        "rainExtractionParity", "rainMistSplashMinimum", "rainMistSplashMaximum",
        "rainReducedMotion", "snowMinimumPopulation", "snowDefault",
        "snowMaximumPopulation", "snowMinimumSize", "snowMaximumSize",
        "snowLowFlutterNegativeSlant", "snowHighFlutterPositiveSlant",
        "snowSoft", "snowCrystal", "snowMixed", "snowReducedMotion",
        "rainBackground", "rainForeground", "snowBackground", "snowForeground",
        "snowThemeSwitch",
    ):
        assert case_id in visual
    assert 'position = "-1920x-1080"' in visual
    assert '"negativeOriginCovered"' in visual
    assert '"precipitationThemeSwitchChangedPixels"' in visual
    assert '"rainExtractionParityEvidence"' in visual


def test_performance_matrix_enforces_precipitation_population_clock_and_shutdown_bounds():
    performance = read("tests/live_phase7_performance.py")
    for case_id in (
        "rainDefault", "snowDefault", "rainMaximumPopulation", "snowMaximumPopulation",
        "snowMaximumSizeCrystal", "rainMistSplashMinimum", "rainMistSplashMaximum",
        "rainReducedMotion", "snowReducedMotion", "precipitationStyleSwitchChurn",
        "rainHidden", "snowHidden", "rainFullscreenSuppressed", "snowFullscreenSuppressed",
    ):
        assert f'("{case_id}", "effects/RainfallEffect.qml")' in performance
    for metric in (
        "particleCount", "primitiveCount", "animationObjectCount", "runningAnimationCount",
        "clockObjectCount", "runningClockCount", "clockUpdateDelta", "styleSwitchCount",
        "rootIdentityStable", "precipitationAfterShutdown",
    ):
        assert metric in performance
    assert 'metrics["primitiveCount"] <= 1280 * outputs' in performance
    assert 'metrics["animationObjectCount"] > 520 * outputs' in performance
    assert 'stopped_metrics["loadedStyleCount"] != outputs' in performance


def test_fullscreen_and_multi_output_harnesses_are_reversible_isolated_and_integrated():
    fullscreen = read("tests/live_phase6_fullscreen.py")
    multi = read("tests/live_precipitation_multi_output_visual.py")
    orchestrator = read("scripts/check-phase6.sh")
    assert '"activeEffects": ["bokeh", "nodeMesh", "rainfall"]' in fullscreen
    assert '"precipitationStyle": "snow"' in fullscreen
    assert "precipitationStoppedWhileSuppressed" in fullscreen
    assert "precipitationIdentityPreservedAcrossPresentation" in fullscreen
    assert "JOBO_AMBIENCE_FULLSCREEN_EVIDENCE" in fullscreen
    assert 'os.environ.get("JOBO_AMBIENCE_LIVE_PHASE6") != "1"' in multi
    assert 'run(["hyprctl", "output", "remove", name], check=False)' in multi
    assert '"XDG_CONFIG_HOME": str(temp / "config")' in multi
    assert 'configure_output(OUTPUTS[0], -3840, -180)' in multi
    assert 'configure_output(OUTPUTS[1], -1920, 0)' in multi
    assert '"negativeOriginCovered"' in multi
    assert '"liveSettingsModified": False' in multi
    assert '"persistentHyprlandConfigModified": False' in multi
    assert "tests/live_precipitation_multi_output_visual.py" in orchestrator


def test_release_docs_keep_one_rainfall_renderer_and_explain_compatible_count_key():
    readme = read("README.md")
    changelog = read("CHANGELOG.md")
    todo = read("TODO.md")
    plan = read("docs/precipitation-styles-plan.md")
    assert "Eleven ordered renderers" in readme
    assert "production renderer count stays at eleven" in readme
    assert "`effects.rainfall.dropCount`" in readme
    assert "**Precipitation Count**" in readme
    assert "selectable rain and snow precipitation styles" in changelog
    assert "compatible persisted `dropCount`" in changelog
    assert "[x] **Precipitation styles**" in todo
    assert "Status: complete" in plan
    assert "### 6. Complete documentation and release integration — complete" in plan


def test_recorded_precipitation_evidence_covers_visual_multi_output_fullscreen_and_performance():
    visual = load("docs/release/evidence/precipitation-styles/visual-performance.json")
    assert visual["isolatedConfig"] is True
    assert visual["liveSettingsModified"] is False
    assert visual["negativeOriginCovered"] is True
    assert visual["precipitationThemeSwitchChangedPixels"] is True
    assert len(visual["precipitationVisualCases"]) >= 19

    multi = load("docs/release/evidence/precipitation-multi-output.json")
    assert multi["isolatedConfig"] is True
    assert multi["liveSettingsModified"] is False
    assert multi["negativeOriginCovered"] is True
    assert multi["styles"] == ["rain", "snow"]
    assert multi["screenshotsNonBlankAndDistinct"] is True

    fullscreen = load("docs/release/evidence/precipitation-fullscreen.json")
    assert fullscreen["activeEffects"] == ["bokeh", "nodeMesh", "rainfall"]
    assert fullscreen["precipitationStyle"] == "snow"
    assert fullscreen["precipitationStoppedWhileSuppressed"] is True

    performance = load("docs/performance/evidence/precipitation-styles.json")
    assert performance["isolatedConfig"] is True
    assert performance["liveSettingsModified"] is False
    assert performance["negativeOriginCovered"] is True
    assert {row["outputs"] for row in performance["results"]} == {1, 3}
    assert set(performance["cases"]) >= {
        "rainDefault", "snowDefault", "rainMaximumPopulation", "snowMaximumPopulation",
        "snowMaximumSizeCrystal", "rainMistSplashMinimum", "rainMistSplashMaximum",
        "rainReducedMotion", "snowReducedMotion", "precipitationStyleSwitchChurn",
        "rainHidden", "snowHidden", "rainFullscreenSuppressed", "snowFullscreenSuppressed",
    }
    assert all(row["precipitationAfterShutdown"]["autonomousOutputs"] == 0
               for row in performance["results"])
