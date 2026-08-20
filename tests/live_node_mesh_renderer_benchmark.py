#!/usr/bin/env python3
"""Opt-in Canvas versus Shape benchmark for the Node Mesh line renderer.

The benchmark creates reversible headless Hyprland outputs and uses isolated
Quickshell processes. It never reads or writes live plugin settings. Raw values
are machine-local and are intended to compare the two otherwise identical
prototypes, not to define a cross-machine CPU guarantee.
"""

from __future__ import annotations

import argparse
import json
import os
import select
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

from qml_harness import parse_behave, require_no_qml_errors


if os.environ.get("JOBO_AMBIENCE_NODE_MESH_BENCHMARK") != "1":
    raise SystemExit("set JOBO_AMBIENCE_NODE_MESH_BENCHMARK=1 to run the renderer benchmark")
if not os.environ.get("WAYLAND_DISPLAY"):
    raise SystemExit("an active Wayland session is required")
for tool in ("quickshell", "hyprctl"):
    if not shutil.which(tool):
        raise SystemExit(f"missing required tool: {tool}")

ROOT = Path(__file__).resolve().parents[1]
PROTOTYPE_ROOT = ROOT / "tests/prototypes/node-mesh"
RENDERERS = {
    "canvas": PROTOTYPE_ROOT / "CanvasPrototype.qml",
    "shape": PROTOTYPE_ROOT / "ShapePrototype.qml",
}
SCENARIOS = {
    "default": {"nodeCount": 54, "connectionDistance": 132},
    "maximum": {"nodeCount": 120, "connectionDistance": 260},
}
MAX_NEIGHBORS = 4
TARGET_UPDATES_PER_SECOND = 30
PIXEL_EVIDENCE = ROOT / "docs/performance/evidence/node-mesh-pixels.json"


def run(command: list[str], *, timeout: int = 30, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    if check and proc.returncode != 0:
        raise AssertionError(
            f"{command} failed ({proc.returncode})\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return proc


def wait_for_outputs(names: list[str], present: bool, timeout: float = 10) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        monitors = json.loads(run(["hyprctl", "-j", "monitors", "all"]).stdout)
        current = {str(item.get("name")) for item in monitors}
        if all((name in current) is present for name in names):
            return
        time.sleep(0.1)
    raise AssertionError(f"outputs did not settle present={present}: {names}")


def configure_output(name: str, x: int) -> dict:
    expression = (
        "hl.monitor({"
        f'output = "{name}", mode = "1920x1080@60", position = "{x}x0", '
        "scale = 1, transform = 0"
        "})"
    )
    run(["hyprctl", "eval", expression])
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        monitors = json.loads(run(["hyprctl", "-j", "monitors", "all"]).stdout)
        monitor = next((item for item in monitors if str(item.get("name")) == name), None)
        if monitor and int(monitor.get("x", 0)) == x:
            return {
                "name": name,
                "x": int(monitor.get("x", 0)),
                "y": int(monitor.get("y", 0)),
                "width": int(monitor.get("width", 0)),
                "height": int(monitor.get("height", 0)),
                "scale": float(monitor.get("scale", 1)),
            }
        time.sleep(0.1)
    raise AssertionError(f"temporary output {name} did not settle at x={x}")


def proc_ticks(pid: int) -> int:
    fields = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").split()
    return int(fields[13]) + int(fields[14])


def proc_rss_kib(pid: int) -> int:
    for line in Path(f"/proc/{pid}/status").read_text(encoding="utf-8").splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1])
    return 0


def make_qml(renderer: str, scenario: dict, output_names: list[str], duration_ms: int) -> str:
    source = RENDERERS[renderer].as_uri()
    windows = []
    for index, name in enumerate(output_names):
        windows.append(f'''
  Window {{
    screen: root.windowScreen("{name}")
    visibility: Window.FullScreen
    visible: true
    color: "#101315"
    title: "node-mesh-{renderer}-{index}"
    Loader {{
      anchors.fill: parent
      source: "{source}"
      onLoaded: root.configure(item)
    }}
  }}''')

    return f'''
import Quickshell
import QtQuick
import QtQuick.Window

ShellRoot {{
  id: root
  property int loadedCount: 0
  property var loadedItems: []
  property int baselineUpdates: 0
  property int baselinePaints: 0
  property bool measuring: false
  property int frameCount: 0
  property real frameTotalMs: 0
  property real frameMaxMs: 0
  property int framesOver20Ms: 0

  function windowScreen(name) {{
    for (var index = 0; index < Qt.application.screens.length; index++)
      if (String(Qt.application.screens[index].name) === name) return Qt.application.screens[index]
    return null
  }}

  function total(propertyName) {{
    var value = 0
    for (var index = 0; index < loadedItems.length; index++)
      value += Number(loadedItems[index][propertyName])
    return value
  }}

  function configure(item) {{
    item.running = true
    item.nodeCount = {scenario['nodeCount']}
    item.connectionDistance = {scenario['connectionDistance']}
    loadedItems = loadedItems.concat([item])
    loadedCount += 1
    if (loadedCount === {len(output_names)}) warmup.start()
  }}

  Timer {{
    id: warmup
    interval: 1200
    onTriggered: {{
      baselineUpdates = total("updateCount")
      baselinePaints = total("paintRequestCount")
      console.log("BENCH_READY " + JSON.stringify({{warmupMs: warmup.interval, sampleMs: sample.interval}}))
      measuring = true
      sample.start()
    }}
  }}

  FrameAnimation {{
    running: root.measuring
    onTriggered: {{
      var milliseconds = frameTime * 1000
      frameCount += 1
      frameTotalMs += milliseconds
      frameMaxMs = Math.max(frameMaxMs, milliseconds)
      if (milliseconds > 20) framesOver20Ms += 1
    }}
  }}

  Timer {{
    id: sample
    interval: {duration_ms}
    onTriggered: {{
      measuring = false
      for (var index = 0; index < loadedItems.length; index++) loadedItems[index].running = false
      console.log("BEHAVE " + JSON.stringify({{
        renderer: "{renderer}",
        scenario: "{'maximum' if scenario['nodeCount'] == 120 else 'default'}",
        outputs: {len(output_names)},
        durationMs: {duration_ms},
        updateDelta: total("updateCount") - baselineUpdates,
        paintDelta: total("paintRequestCount") - baselinePaints,
        edgeCount: total("edgeCount"),
        edgeCeiling: total("edgeCeiling"),
        pathObjectCount: total("pathObjectCount"),
        renderedSegmentCount: total("renderedSegmentCount"),
        frameCount: frameCount,
        meanFrameMs: frameCount > 0 ? frameTotalMs / frameCount : 0,
        maxFrameMs: frameMaxMs,
        framesOver20Ms: framesOver20Ms
      }}))
      quitDelay.start()
    }}
  }}

  Timer {{ id: quitDelay; interval: 250; onTriggered: Qt.quit() }}

  {''.join(windows)}
}}
'''


def profile(renderer: str, scenario_name: str, output_names: list[str], duration_ms: int) -> dict:
    scenario = SCENARIOS[scenario_name]
    qml = make_qml(renderer, scenario, output_names, duration_ms)
    with tempfile.TemporaryDirectory() as directory:
        shell = Path(directory) / "shell.qml"
        shell.write_text(qml, encoding="utf-8")
        env = os.environ.copy()
        env["QT_QPA_PLATFORM"] = "wayland"
        env["XDG_CONFIG_HOME"] = str(Path(directory) / "config")
        env["XDG_STATE_HOME"] = str(Path(directory) / "state")
        proc = subprocess.Popen(
            ["quickshell", "-p", str(shell)], env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0,
        )
        process_started_at = time.monotonic()
        measurement_started_at = 0.0
        measurement_ended_at = 0.0
        measurement_target_at = 0.0
        result_observed_at = 0.0
        resource_window_closed = False
        start_ticks = 0
        end_ticks = 0
        peak_rss = 0
        resource_samples = 0
        ready_payload: dict | None = None
        output_chunks: list[bytes] = []
        pending = b""
        behave_seen = False
        deadline = process_started_at + duration_ms / 1000 + 15
        try:
            while time.monotonic() < deadline and not (behave_seen and resource_window_closed):
                timeout = 0.05
                if measurement_target_at > 0 and not resource_window_closed:
                    timeout = max(0, min(timeout, measurement_target_at - time.monotonic()))
                ready, _, _ = select.select([proc.stdout], [], [], timeout)
                if ready:
                    chunk = os.read(proc.stdout.fileno(), 4096)
                    if chunk:
                        output_chunks.append(chunk)
                        pending += chunk
                        complete_lines = pending.split(b"\n")
                        pending = complete_lines.pop()
                        for raw_line in complete_lines:
                            line = raw_line.decode("utf-8", errors="replace")
                            marker = line.find("BENCH_READY ")
                            if marker >= 0:
                                ready_payload = json.loads(line[marker + len("BENCH_READY "):].strip())
                                measurement_started_at = time.monotonic()
                                measurement_target_at = measurement_started_at + duration_ms / 1000
                                start_ticks = proc_ticks(proc.pid)
                                end_ticks = start_ticks
                                peak_rss = proc_rss_kib(proc.pid)
                                resource_samples = 1
                            if "BEHAVE " in line:
                                if measurement_started_at <= 0:
                                    raise AssertionError("benchmark result arrived before warmup marker")
                                result_observed_at = time.monotonic()
                                behave_seen = True
                if (measurement_started_at > 0 and not resource_window_closed
                        and proc.poll() is None):
                    observed_at = time.monotonic()
                    end_ticks = proc_ticks(proc.pid)
                    peak_rss = max(peak_rss, proc_rss_kib(proc.pid))
                    resource_samples += 1
                    if observed_at >= measurement_target_at:
                        measurement_ended_at = observed_at
                        resource_window_closed = True
                if proc.poll() is not None and not ready:
                    break
            tail, _ = proc.communicate(timeout=5)
            output_chunks.append(tail)
        except Exception:
            proc.kill()
            tail, _ = proc.communicate()
            output_chunks.append(tail)
            raise
        process_ended_at = time.monotonic()
    output = b"".join(output_chunks).decode("utf-8", errors="replace")
    require_no_qml_errors(output)
    rows = parse_behave(output)
    if (proc.returncode != 0 or not rows or ready_payload is None or not behave_seen
            or not resource_window_closed):
        raise AssertionError(f"benchmark failed: {renderer}/{scenario_name}/{len(output_names)}\n{output[-4000:]}")
    row = rows[-1]
    declared_sample_seconds = duration_ms / 1000
    measured_sample_seconds = measurement_ended_at - measurement_started_at
    total_process_seconds = process_ended_at - process_started_at
    warmup_observed_seconds = measurement_started_at - process_started_at
    sample_duration_error_ms = (measured_sample_seconds - declared_sample_seconds) * 1000
    if ready_payload != {"warmupMs": 1200, "sampleMs": duration_ms}:
        raise AssertionError(f"unexpected benchmark timing declaration: {ready_payload}")
    if warmup_observed_seconds < 1.15:
        raise AssertionError(f"resource measurement started before warmup completed: {warmup_observed_seconds}")
    if abs(sample_duration_error_ms) > 20:
        raise AssertionError(f"sample window drifted from declaration: {sample_duration_error_ms} ms")
    ticks_per_second = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
    row.update({
        "averageCpuPercent": (end_ticks - start_ticks) / ticks_per_second / measured_sample_seconds * 100,
        "peakRssKiB": peak_rss,
        "declaredWarmupMs": ready_payload["warmupMs"],
        "warmupObservedSeconds": warmup_observed_seconds,
        "declaredSampleMs": ready_payload["sampleMs"],
        "measuredSampleSeconds": measured_sample_seconds,
        "sampleDurationErrorMs": sample_duration_error_ms,
        "totalProcessLifetimeSeconds": total_process_seconds,
        "resultObservedAfterResourceWindowSeconds": max(0, result_observed_at - measurement_ended_at),
        "resourceWindowClosedAfterResultSeconds": max(0, measurement_ended_at - result_observed_at),
        "resourceSampleCount": resource_samples,
        "measurementStartedAfterWarmup": True,
        "updatesPerSecondPerOutput": row["updateDelta"] / declared_sample_seconds / len(output_names),
        "paintsPerSecondPerOutput": row["paintDelta"] / declared_sample_seconds / len(output_names),
    })
    expected_ceiling = scenario["nodeCount"] * MAX_NEIGHBORS // 2 * len(output_names)
    if row["edgeCeiling"] != expected_ceiling or row["edgeCount"] > row["edgeCeiling"]:
        raise AssertionError(row)
    if row["renderedSegmentCount"] != row["edgeCount"] or row["edgeCount"] <= 0:
        raise AssertionError(f"renderer did not publish equivalent visible geometry: {row}")
    if not 20 <= row["updatesPerSecondPerOutput"] <= TARGET_UPDATES_PER_SECOND + 1:
        raise AssertionError(f"unexpected update cadence: {row}")
    return row


def version(command: list[str]) -> str:
    result = run(command, check=False)
    return (result.stdout or result.stderr).strip().splitlines()[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration-ms", type=int, default=3000)
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/performance/evidence/node-mesh-renderer.json")
    args = parser.parse_args()
    if args.duration_ms < 1000 or args.repetitions < 1:
        raise SystemExit("duration must be >= 1000 ms and repetitions must be positive")

    if not PIXEL_EVIDENCE.is_file():
        raise SystemExit("run tests/live_node_mesh_pixel_probe.py before benchmarking")
    pixel_evidence = json.loads(PIXEL_EVIDENCE.read_text(encoding="utf-8"))
    if not pixel_evidence.get("renderProven") or pixel_evidence.get("canvasShapeSmallerMaskOverlap", 0) < 0.98:
        raise SystemExit("pixel evidence does not prove visible equivalent line geometry")

    output_names = [f"JOBO-NODE-MESH-{uuid.uuid4().hex[:8]}-{index}" for index in range(3)]
    layout: list[dict] = []
    results: list[dict] = []
    try:
        for name in output_names:
            run(["hyprctl", "output", "create", "headless", name])
        wait_for_outputs(output_names, True)
        for index, name in enumerate(output_names):
            layout.append(configure_output(name, -5760 + index * 1920))
        for repetition in range(1, args.repetitions + 1):
            for output_count in (1, 3):
                for scenario_name in SCENARIOS:
                    for renderer in RENDERERS:
                        row = profile(renderer, scenario_name, output_names[:output_count], args.duration_ms)
                        row["repetition"] = repetition
                        results.append(row)
                        print(
                            f"{renderer:6} {scenario_name:7} outputs={output_count} "
                            f"cpu={row['averageCpuPercent']:.2f}% rss={row['peakRssKiB']/1024:.1f}MiB "
                            f"updates={row['updatesPerSecondPerOutput']:.1f}/s "
                            f"edges={row['edgeCount']}/{row['edgeCeiling']}"
                        )
    finally:
        for name in reversed(output_names):
            run(["hyprctl", "output", "remove", name], check=False)
        wait_for_outputs(output_names, False)

    evidence = {
        "schemaVersion": 1,
        "purpose": "Node Mesh Canvas versus render-proven retained ShapePath/PathMultiline selection",
        "machineLocalDirectionalEvidence": True,
        "quickshellVersion": version(["quickshell", "--version"]),
        "qtVersion": version(["qmake6", "-query", "QT_VERSION"]),
        "isolatedConfig": True,
        "liveSettingsModified": False,
        "targetUpdatesPerSecond": TARGET_UPDATES_PER_SECOND,
        "declaredWarmupMs": 1200,
        "declaredSampleMs": args.duration_ms,
        "resourceMeasurementPolicy": "CPU ticks and RSS samples begin at BENCH_READY after warmup and end at an independent declared-duration deadline; BEHAVE result timing and total process lifetime are recorded separately",
        "sampleDurationAttested": all(
            row["measurementStartedAfterWarmup"]
            and abs(row["sampleDurationErrorMs"]) <= 20
            and row["totalProcessLifetimeSeconds"] > row["measuredSampleSeconds"]
            for row in results
        ),
        "visibleOutputEvidence": str(PIXEL_EVIDENCE.relative_to(ROOT)),
        "canvasShapeSmallerMaskOverlap": pixel_evidence["canvasShapeSmallerMaskOverlap"],
        "maximumNeighbors": MAX_NEIGHBORS,
        "scenarios": SCENARIOS,
        "temporaryOutputLayout": layout,
        "durationMs": args.duration_ms,
        "repetitions": args.repetitions,
        "results": results,
    }
    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
