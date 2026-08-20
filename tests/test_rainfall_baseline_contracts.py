from __future__ import annotations

import hashlib
import json
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / "tests/baselines/rainfall-pre-extraction.json").read_text(encoding="utf-8"))


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def load(path: str) -> dict:
    return json.loads(read(path))


def test_extracted_rain_source_preserves_pinned_layering_startup_and_lifecycle_contract():
    adapter = read("effects/RainfallEffect.qml")
    rain = read("effects/RainPrecipitationStyle.qml")
    registry = read("services/EffectRegistry.js")
    for token in (
        "initialProgress: root.seededNoise(seed + 11)",
        "initialY: -dropLength + initialProgress * (rainWindow.height + dropLength * 2)",
        "root.windDrift",
        "root.mistAmount > 0 ? 5 : 0",
        "root.dropCount * root.splashAmount * 0.18",
        "running: root.effectVisible && !root.reducedMotion",
        "readonly property bool autonomousMotionRunning: effectVisible && !reducedMotion",
        "readonly property bool visualLayerEnabled: effect.enabled",
    ):
        assert token in rain
    assert rain.count("enabled: false") == 1
    assert "RainPrecipitationStyle {" in adapter
    assert "SnowPrecipitationStyle {" in adapter
    assert 'sourceComponent: root.selectedStyle === "snow" ? snowStyleComponent : rainStyleComponent' in adapter
    rainfall = registry.split('id: "rainfall", label: "Rainfall"', 1)[1].split("\n  },", 1)[0]
    for key, value in CONTRACT["defaults"].items():
        if isinstance(value, bool):
            assert f"{key}: boolField({str(value).lower()})" in rainfall
        else:
            assert f"{key}:" in rainfall and str(value) in rainfall


def test_visual_baseline_is_isolated_full_height_and_hash_pinned():
    evidence = load(CONTRACT["visualEvidence"])
    assert evidence["sourceCommit"] == CONTRACT["sourceCommit"]
    assert evidence["isolatedConfig"] is True
    assert evidence["liveSettingsModified"] is False
    assert evidence["defaults"] == CONTRACT["defaults"]
    assert evidence["population"] == CONTRACT["defaultPopulationAt1920x1080"]
    assert evidence["visualLayerEnabledFalseStillRendered"] is True
    assert evidence["autonomousMotionRunning"] is True
    assert evidence["movedPrimaryDrops"] == CONTRACT["defaults"]["dropCount"]
    assert min(evidence["startupCoverage"].values()) > 0.004
    images = {item["file"]: item for item in evidence["images"]}
    assert images["rainfall-static.png"]["sha256"] == CONTRACT["staticImageSha256"]
    assert images["rainfall-animated.png"]["sha256"] == CONTRACT["animatedImageSha256"]
    for name, image in images.items():
        path = ROOT / "docs/release/evidence/rainfall-baseline" / name
        assert path.is_file() and path.stat().st_size == image["bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == image["sha256"]
        assert (image["width"], image["height"]) == (1920, 1080)
        assert image["standardDeviation"] > 0.001


def test_performance_baseline_covers_one_and_three_outputs_with_three_samples():
    evidence = load(CONTRACT["performanceEvidence"])
    assert evidence["isolatedConfig"] is True
    assert evidence["liveSettingsModified"] is False
    assert evidence["cases"] == ["rainfall"]
    assert evidence["durationMs"] == 3000
    assert evidence["repetitions"] == 3
    assert evidence["negativeOriginCovered"] is True
    assert len(evidence["results"]) == 6
    assert {row["outputs"] for row in evidence["results"]} == {1, 3}
    for count in (1, 3):
        rows = [row for row in evidence["results"] if row["outputs"] == count]
        assert len(rows) == 3
        assert all(row["caseId"] == "rainfall" for row in rows)
        assert all(row["frameCount"] >= 170 for row in rows)
        assert 16 <= statistics.median(row["meanFrameMs"] for row in rows) <= 18
        assert statistics.median(row["averageCpuPercent"] for row in rows) > 0
        assert statistics.median(row["peakRssKiB"] for row in rows) > 0


def test_baseline_harnesses_are_opt_in_reversible_and_never_touch_live_settings():
    visual = read("tests/live_rainfall_baseline.py")
    performance = read("tests/live_phase7_performance.py")
    assert 'os.environ.get("JOBO_AMBIENCE_RAIN_BASELINE") != "1"' in visual
    assert 'run(["hyprctl", "output", "create", "headless", output_name])' in visual
    assert 'run(["hyprctl", "output", "remove", output_name], check=False)' in visual
    assert '"XDG_CONFIG_HOME": config_dir' in visual
    assert '"liveSettingsModified": False' in visual
    assert 'parser.add_argument("--cases", default="")' in performance
    assert 'env["XDG_CONFIG_HOME"] = str(temp / "config")' in performance
