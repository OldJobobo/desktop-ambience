from __future__ import annotations

import json
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOTYPES = ROOT / "tests/prototypes/node-mesh"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load(path: Path) -> dict:
    return json.loads(read(path))


def test_renderer_contract_selects_render_proven_bounded_shape_buckets():
    contract = load(PROTOTYPES / "renderer-contract.json")
    assert contract["selectedRenderer"] == "shape"
    assert contract["rejectedRenderer"] == "canvas"
    assert contract["targetUpdatesPerSecond"] == 30
    assert contract["maximumNodeCount"] == 120
    assert contract["maximumNeighborsPerNode"] == 4
    assert contract["maximumEdgesPerOutput"] == 120 * 4 // 2 == 240
    assert contract["lineSurfaceCountPerOutput"] == 1
    assert contract["fixedShapePathsPerOutput"] == 8
    assert contract["pathAllocationPolicy"] == (
        "eight declarative ShapePaths with retained PathMultiline opacity buckets"
    )


def test_prototypes_share_bounded_simulation_and_equivalent_opacity_buckets():
    core = read(PROTOTYPES / "NodeMeshPrototypeCore.js")
    canvas = read(PROTOTYPES / "CanvasPrototype.qml")
    shape = read(PROTOTYPES / "ShapePrototype.qml")

    for source in (canvas, shape):
        assert 'import "NodeMeshPrototypeCore.js" as MeshCore' in source
        assert source.count("FrameAnimation {") == 1
        assert "property int targetUpdatesPerSecond: 30" in source
        assert "Math.floor(nodeCount * maximumNeighbors / 2)" in source
        assert "MeshCore.createNodes" in source
        assert "MeshCore.advance" in source
        assert "MeshCore.buildEdges" in source
        assert "simulationRevision += 1" in source
        assert "function opacityBucket(opacity)" in source
        assert "function bucketOpacity(index)" in source
        assert "readonly property int renderedSegmentCount: edges.length" in source
        assert "if (rawFrameTime > 0.05)" in source
        assert "accumulatedFrameTime = 0" in source

    assert canvas.count("Canvas {") == 1
    assert "ShapePath" not in canvas
    assert "renderStrategy: Canvas.Immediate" in canvas
    assert shape.count("Shape {") == 1
    assert shape.count("ShapePath {") == 8
    assert shape.count("PathMultiline {") == 8
    assert "Canvas" not in shape
    assert "createObject" not in shape
    assert "pathGroups = groups" in shape

    assert "var grid = {}" in core
    assert "otherIndex <= index" in core
    assert "degrees[candidate.a] >= maxNeighbors" in core
    assert "degrees[candidate.b] >= maxNeighbors" in core
    assert "Math.floor(nodes.length * maxNeighbors / 2)" in core
    assert "1 - Math.sqrt(candidate.distanceSquared) / cutoff" in core


def test_benchmark_measurement_is_bounded_by_post_warmup_resource_markers():
    benchmark = read(ROOT / "tests/live_node_mesh_renderer_benchmark.py")
    assert 'console.log("BENCH_READY "' in benchmark
    assert 'ready_payload = json.loads' in benchmark
    assert 'start_ticks = proc_ticks(proc.pid)' in benchmark
    assert 'measurement_target_at = measurement_started_at + duration_ms / 1000' in benchmark
    assert 'if observed_at >= measurement_target_at:' in benchmark
    assert 'resource_window_closed = True' in benchmark
    assert '"totalProcessLifetimeSeconds": total_process_seconds' in benchmark
    assert '"sampleDurationAttested": all(' in benchmark


def test_pixel_evidence_proves_lines_settings_changes_and_renderer_equivalence():
    contract = load(PROTOTYPES / "renderer-contract.json")
    evidence = load(ROOT / contract["pixelEvidence"])

    assert evidence["renderProven"] is True
    assert evidence["productionLineOpacityChangedPixels"] >= 100
    assert evidence["productionConnectionDistanceChangedPixels"] >= 100
    assert evidence["productionLongVisiblePixels"] > evidence["productionShortVisiblePixels"]
    assert evidence["canvasVisiblePixels"] >= 100
    assert evidence["shapeVisiblePixels"] >= 100
    assert evidence["canvasShapeSmallerMaskOverlap"] >= 0.98
    captures = {row["caseId"]: row for row in evidence["captures"]}
    assert captures["prototype-canvas"]["edgeCount"] == captures["prototype-shape"]["edgeCount"] > 0
    assert captures["prototype-shape"]["pathCount"] == contract["fixedShapePathsPerOutput"]


def test_live_evidence_covers_visible_default_and_maximum_on_one_and_three_outputs():
    contract = load(PROTOTYPES / "renderer-contract.json")
    evidence = load(ROOT / contract["evidence"])

    assert evidence["machineLocalDirectionalEvidence"] is True
    assert evidence["isolatedConfig"] is True
    assert evidence["liveSettingsModified"] is False
    assert evidence["visibleOutputEvidence"] == contract["pixelEvidence"]
    assert evidence["canvasShapeSmallerMaskOverlap"] >= 0.98
    assert evidence["targetUpdatesPerSecond"] == contract["targetUpdatesPerSecond"]
    assert evidence["declaredWarmupMs"] == 1200
    assert evidence["declaredSampleMs"] == evidence["durationMs"] == 3000
    assert evidence["sampleDurationAttested"] is True
    assert "begin at BENCH_READY after warmup" in evidence["resourceMeasurementPolicy"]
    assert "independent declared-duration deadline" in evidence["resourceMeasurementPolicy"]
    assert evidence["maximumNeighbors"] == contract["maximumNeighborsPerNode"]
    assert evidence["scenarios"] == {
        "default": {"nodeCount": 54, "connectionDistance": 132},
        "maximum": {"nodeCount": 120, "connectionDistance": 260},
    }
    assert evidence["repetitions"] >= 3
    assert {row["renderer"] for row in evidence["results"]} == {"canvas", "shape"}
    assert {row["scenario"] for row in evidence["results"]} == {"default", "maximum"}
    assert {row["outputs"] for row in evidence["results"]} == {1, 3}

    for row in evidence["results"]:
        assert 29 <= row["updatesPerSecondPerOutput"] <= 31
        assert row["measurementStartedAfterWarmup"] is True
        assert row["declaredWarmupMs"] == 1200
        assert row["declaredSampleMs"] == 3000
        assert row["warmupObservedSeconds"] >= 1.15
        assert abs(row["measuredSampleSeconds"] - 3) <= 0.02
        assert abs(row["sampleDurationErrorMs"]) <= 20
        assert row["totalProcessLifetimeSeconds"] > row["measuredSampleSeconds"]
        assert row["resourceSampleCount"] >= 10
        assert 0 < row["edgeCount"] <= row["edgeCeiling"]
        assert row["renderedSegmentCount"] == row["edgeCount"]
        expected_paths = contract["fixedShapePathsPerOutput"] * row["outputs"] \
            if row["renderer"] == "shape" else 0
        assert row["pathObjectCount"] == expected_paths


def test_shape_is_clearly_cheaper_and_callback_stability_is_comparable_in_every_cell():
    evidence = load(ROOT / "docs/performance/evidence/node-mesh-renderer.json")
    for outputs in (1, 3):
        for scenario in ("default", "maximum"):
            grouped = {
                renderer: [
                    row for row in evidence["results"]
                    if row["renderer"] == renderer
                    and row["scenario"] == scenario
                    and row["outputs"] == outputs
                ]
                for renderer in ("canvas", "shape")
            }
            assert len(grouped["canvas"]) == len(grouped["shape"]) >= 3
            canvas_cpu = statistics.median(row["averageCpuPercent"] for row in grouped["canvas"])
            shape_cpu = statistics.median(row["averageCpuPercent"] for row in grouped["shape"])
            canvas_rss = statistics.median(row["peakRssKiB"] for row in grouped["canvas"])
            shape_rss = statistics.median(row["peakRssKiB"] for row in grouped["shape"])
            canvas_max_frame = statistics.median(row["maxFrameMs"] for row in grouped["canvas"])
            shape_max_frame = statistics.median(row["maxFrameMs"] for row in grouped["shape"])

            assert shape_cpu < canvas_cpu
            assert shape_rss < canvas_rss
            assert shape_max_frame <= canvas_max_frame * 1.1


def test_plan_and_selection_note_pin_render_proven_shape_for_production():
    plan = read(ROOT / "docs/node-mesh-plan.md")
    selection = read(ROOT / "docs/performance/node-mesh-renderer-selection.md")
    assert "Phase 1 renderer decision: render-proven declarative ShapePath buckets" in plan
    assert "eight declarative `ShapePath` objects" in selection
    assert "99.93% of the smaller renderer mask" in selection
    assert "No reduction to the 120-node maximum" in selection
