#!/usr/bin/env python3
"""Opt-in isolated per-effect Phase 7 performance matrix.

The harness creates three temporary headless outputs and launches a fresh
Quickshell process for every effect/output-count pair. Live plugin settings are
never read or written. Use --target-root to profile an older Git worktree with
the current harness.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

from qml_harness import parse_behave, qml_url, require_no_qml_errors


if os.environ.get("JOBO_AMBIENCE_LIVE_PHASE7") != "1":
    raise SystemExit("set JOBO_AMBIENCE_LIVE_PHASE7=1 to run the Phase 7 performance matrix")
if not os.environ.get("WAYLAND_DISPLAY"):
    raise SystemExit("an active Wayland session is required")
for tool in ("quickshell", "hyprctl"):
    if not shutil.which(tool):
        raise SystemExit(f"missing required tool: {tool}")

REPO_ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ("auroraDrift", "effects/AuroraDriftEffect.qml"),
    ("cinematicLight", "effects/CinematicLightEffect.qml"),
    ("crt", "effects/CrtEffect.qml"),
    ("dustMotes", "effects/DustMotesEffect.qml"),
    ("filmGrain", "effects/FilmGrainEffect.qml"),
    ("godRays", "effects/GodRaysEffect.qml"),
    ("rainfall", "effects/RainfallEffect.qml"),
    ("tacticalGrid", "effects/TacticalGridEffect.qml"),
    ("trackingLines", "effects/VhsEffect.qml"),
    ("backgroundVignette", "effects/VignetteEffect.qml"),
    ("threeEffectStack", "components/AmbienceStack.qml"),
]


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
        payload = json.loads(run(["hyprctl", "-j", "monitors", "all"]).stdout)
        current = {str(item.get("name")) for item in payload}
        if all((name in current) is present for name in names):
            return
        time.sleep(0.1)
    raise AssertionError(f"outputs did not settle present={present}: {names}")


def proc_ticks(pid: int) -> int:
    fields = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").split()
    return int(fields[13]) + int(fields[14])


def proc_rss_kib(pid: int) -> int:
    for line in Path(f"/proc/{pid}/status").read_text(encoding="utf-8").splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1])
    return 0


def make_qml(
    target_root: Path,
    case_id: str,
    source: str,
    output_names: list[str],
    duration_ms: int,
    shared_tracker: bool,
) -> str:
    registry_url = (target_root / "services/EffectRegistry.js").as_uri()
    source_url = (target_root / source).as_uri()
    tracker_source = (target_root / "services/CursorTracker.qml").as_uri() if shared_tracker else ""

    windows = []
    for index, name in enumerate(output_names):
        windows.append(f'''
  Window {{
    id: renderWindow{index}
    screen: root.windowScreen("{name}")
    visibility: Window.FullScreen
    visible: true
    color: "#101315"
    title: "jobo-phase7-{case_id}-{index}"
    Loader {{
      anchors.fill: parent
      source: "{source_url}"
      onLoaded: root.configure(item, "{name}")
    }}
  }}''')

    tracker_loader = f'''
  Loader {{
    id: trackerLoader
    active: true
    source: "{tracker_source}"
  }}''' if shared_tracker else "  QtObject { id: trackerLoader; property var item: null }"

    tracker_assign = 'if ("cursorTracker" in item) item.cursorTracker = trackerLoader.item' if shared_tracker else ""
    stack_tracker_assign = "item.cursorTracker = trackerLoader.item" if shared_tracker else ""
    tracker_start = 'if (trackerLoader.item) trackerLoader.item.active = caseId === "dustMotes" || caseId === "tacticalGrid"' if shared_tracker else ""
    tracker_stop = "if (trackerLoader.item) trackerLoader.item.active = false" if shared_tracker else ""
    tracker_count = "trackerLoader.item ? trackerLoader.item.launchCount : -1" if shared_tracker else "-1"

    return f'''
import Quickshell
import QtQuick
import QtQuick.Window
import "{registry_url}" as EffectRegistry

ShellRoot {{
  id: root
  property string caseId: "{case_id}"
  property int loadedCount: 0
  property bool measuring: false
  property int frameCount: 0
  property real frameTotalMs: 0
  property real frameMaxMs: 0
  property int framesOver20Ms: 0

  QtObject {{
    id: state
    property real opacity: 1
    property bool reduceMotion: false
    property var effects: ({{}})
  }}

  QtObject {{
    id: theme
    function colorFor(name, fallback) {{
      var colors = {{
        background: "#101315", foreground: "#d8dee9", accent: "#88c0d0",
        color5: "#b48ead", color11: "#ebcb8b", color12: "#81a1c1",
        color13: "#b48ead", color14: "#8fbcbb", color15: "#eceff4"
      }}
      return colors[name] || fallback
    }}
  }}

  function renderScreen(name) {{
    for (var i = 0; i < Quickshell.screens.length; i++)
      if (String(Quickshell.screens[i].name) === name) return Quickshell.screens[i]
    return null
  }}

  function windowScreen(name) {{
    for (var i = 0; i < Qt.application.screens.length; i++)
      if (String(Qt.application.screens[i].name) === name) return Qt.application.screens[i]
    return null
  }}

  function configure(item, outputName) {{
    if (caseId === "backgroundVignette") {{
      item.settings = EffectRegistry.vignetteDefaults()
      item.settings.enabled = true
      item.paintEnabled = true
    }} else if (caseId === "threeEffectStack") {{
      var ids = EffectRegistry.orderedIds()
      var values = {{}}
      for (var i = 0; i < ids.length; i++) values[ids[i]] = EffectRegistry.defaultsFor(ids[i])
      values.dustMotes.mouseReactive = false
      state.effects = values
      item.settings = state
      item.theme = theme
      {stack_tracker_assign}
      item.activeEffects = ["auroraDrift", "rainfall", "filmGrain"]
      item.productionEffectsEnabled = true
      item.paintEnabled = true
    }} else {{
      item.effectSettings = EffectRegistry.defaultsFor(caseId)
      item.globalOpacity = 1
      item.reducedMotion = false
      if ("theme" in item) item.theme = theme
      {tracker_assign}
    }}
    if ("targetScreen" in item) item.targetScreen = renderScreen(outputName)
    loadedCount += 1
    if (loadedCount === {len(output_names)}) warmup.start()
  }}

  {tracker_loader}

  Timer {{
    id: warmup
    interval: 1200
    onTriggered: {{
      {tracker_start}
      root.measuring = true
      sample.stop()
      sample.start()
    }}
  }}

  FrameAnimation {{
    running: root.measuring
    onTriggered: {{
      var milliseconds = frameTime * 1000
      root.frameCount += 1
      root.frameTotalMs += milliseconds
      root.frameMaxMs = Math.max(root.frameMaxMs, milliseconds)
      if (milliseconds > 20) root.framesOver20Ms += 1
    }}
  }}

  Timer {{
    id: sample
    interval: {duration_ms}
    onTriggered: {{
      root.measuring = false
      {tracker_stop}
      console.log("BEHAVE " + JSON.stringify({{
        caseId: caseId,
        outputs: {len(output_names)},
        frameCount: frameCount,
        meanFrameMs: frameCount > 0 ? frameTotalMs / frameCount : 0,
        maxFrameMs: frameMaxMs,
        framesOver20Ms: framesOver20Ms,
        cursorLaunchCount: {tracker_count}
      }}))
      Qt.quit()
    }}
  }}

  {''.join(windows)}
}}
'''


def profile_case(
    target_root: Path,
    case_id: str,
    source: str,
    output_names: list[str],
    duration_ms: int,
    shared_tracker: bool,
) -> dict:
    qml = make_qml(target_root, case_id, source, output_names, duration_ms, shared_tracker)
    with tempfile.TemporaryDirectory() as directory:
        temp = Path(directory)
        shell = temp / "shell.qml"
        shell.write_text(qml, encoding="utf-8")
        omarchy_shell = Path(os.environ.get("OMARCHY_PATH", "/usr/share/omarchy")) / "shell"
        for module in ("Commons", "Ui"):
            source_dir = omarchy_shell / module
            if source_dir.is_dir():
                (temp / module).symlink_to(source_dir, target_is_directory=True)
        env = os.environ.copy()
        env["QT_QPA_PLATFORM"] = "wayland"
        env["XDG_CONFIG_HOME"] = str(temp / "config")
        env["XDG_STATE_HOME"] = str(temp / "state")
        proc = subprocess.Popen(
            ["quickshell", "-p", str(shell)], env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        try:
            time.sleep(1.7)
            started_at = time.monotonic()
            start_ticks = proc_ticks(proc.pid)
            end_ticks = start_ticks
            peak_rss = 0
            samples = 0
            while proc.poll() is None:
                end_ticks = proc_ticks(proc.pid)
                peak_rss = max(peak_rss, proc_rss_kib(proc.pid))
                samples += 1
                time.sleep(0.1)
            elapsed = max(0.001, time.monotonic() - started_at)
            stdout, stderr = proc.communicate(timeout=5)
        except Exception:
            proc.kill()
            stdout, stderr = proc.communicate()
            raise
    output = stdout + stderr
    require_no_qml_errors(output)
    rows = parse_behave(output)
    if proc.returncode != 0 or not rows:
        raise AssertionError(f"performance case failed: {case_id}/{len(output_names)}\n{output[-4000:]}")
    row = rows[-1]
    ticks_per_second = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
    row.update({
        "averageCpuPercent": (end_ticks - start_ticks) / ticks_per_second / elapsed * 100,
        "peakRssKiB": peak_rss,
        "processSamples": samples,
        "sharedCursorTracker": shared_tracker,
        "legacyExpectedCursorLaunchesPerSecond": (
            len(output_names) * 1000 / 120 if case_id == "dustMotes" and not shared_tracker else 0
        ),
    })
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--duration-ms", type=int, default=4000)
    parser.add_argument("--output-counts", default="1,3")
    parser.add_argument("--cases", default="")
    parser.add_argument("--repetitions", type=int, default=1)
    args = parser.parse_args()
    target_root = args.target_root.resolve()
    version = json.loads((target_root / "manifest.json").read_text(encoding="utf-8"))["version"]
    shared_tracker = (target_root / "services/CursorTracker.qml").is_file()
    output_counts = [int(value) for value in args.output_counts.split(",")]
    if not output_counts or min(output_counts) < 1 or max(output_counts) > 3:
        raise SystemExit("--output-counts must contain values from 1 through 3")
    requested_cases = {value for value in args.cases.split(",") if value}
    selected_cases = [case for case in CASES if not requested_cases or case[0] in requested_cases]
    if requested_cases and {case[0] for case in selected_cases} != requested_cases:
        raise SystemExit("--cases contains an unknown effect ID")
    if args.repetitions < 1:
        raise SystemExit("--repetitions must be positive")

    output_names = [f"JOBO-PHASE7-PERF-{uuid.uuid4().hex[:8]}-{index}" for index in range(3)]
    results: list[dict] = []
    try:
        for name in output_names:
            run(["hyprctl", "output", "create", "headless", name])
        wait_for_outputs(output_names, True)
        for repetition in range(1, args.repetitions + 1):
            for count in output_counts:
                for case_id, source in selected_cases:
                    result = profile_case(
                        target_root, case_id, source, output_names[:count],
                        args.duration_ms, shared_tracker,
                    )
                    result["repetition"] = repetition
                    results.append(result)
                    print(
                        f"{case_id:22} outputs={count} run={repetition} "
                        f"cpu={result['averageCpuPercent']:.2f}% "
                        f"rss={result['peakRssKiB'] / 1024:.1f}MiB frame={result['meanFrameMs']:.2f}ms"
                    )
    finally:
        for name in reversed(output_names):
            run(["hyprctl", "output", "remove", name], check=False)
        wait_for_outputs(output_names, False)

    evidence = {
        "schemaVersion": 1,
        "pluginVersion": version,
        "targetRoot": str(target_root),
        "isolatedConfig": True,
        "liveSettingsModified": False,
        "durationMs": args.duration_ms,
        "repetitions": args.repetitions,
        "cases": [case[0] for case in selected_cases],
        "results": results,
    }
    output_path = args.output or REPO_ROOT / "docs/performance/evidence" / version / "phase7-performance.json"
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
