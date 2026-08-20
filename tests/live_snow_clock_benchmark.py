#!/usr/bin/env python3
"""Opt-in installed-runtime comparison for Snow's animation-clock strategy.

Compares the production-style 30 Hz shared clock against three independent
NumberAnimations per flake at the maximum 320-flake population. The temporary
headless output and XDG homes are removed after the run; live settings are never
read or changed. Values are machine-local directional evidence.
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


if os.environ.get("JOBO_AMBIENCE_SNOW_CLOCK_BENCHMARK") != "1":
    raise SystemExit("set JOBO_AMBIENCE_SNOW_CLOCK_BENCHMARK=1 to run the Snow clock benchmark")
if not os.environ.get("WAYLAND_DISPLAY"):
    raise SystemExit("an active Wayland session is required")
for tool in ("quickshell", "hyprctl"):
    if not shutil.which(tool):
        raise SystemExit(f"missing required tool: {tool}")

ROOT = Path(__file__).resolve().parents[1]
PROTOTYPE = ROOT / "tests/prototypes/precipitation/SnowAnimationPrototype.qml"
MODES = ("sharedClock", "perFlake")


def run(command: list[str], *, timeout: int = 30, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    if check and proc.returncode != 0:
        raise AssertionError(f"{command} failed ({proc.returncode})\n{proc.stdout}\n{proc.stderr}")
    return proc


def monitors() -> list[dict]:
    return json.loads(run(["hyprctl", "-j", "monitors", "all"]).stdout)


def wait_for_output(name: str, present: bool, timeout: float = 10) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        found = any(str(item.get("name")) == name for item in monitors())
        if found is present:
            return
        time.sleep(0.1)
    raise AssertionError(f"temporary output {name} present={present} did not settle")


def configure_output(name: str) -> dict:
    expression = (
        "hl.monitor({"
        f'output = "{name}", mode = "1920x1080@60", position = "-1920x-1080", '
        "scale = 1, transform = 0"
        "})"
    )
    run(["hyprctl", "eval", expression])
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        monitor = next((item for item in monitors() if str(item.get("name")) == name), None)
        if monitor and int(monitor.get("x", 0)) == -1920 and int(monitor.get("y", 0)) == -1080:
            return {key: monitor.get(key) for key in ("name", "x", "y", "width", "height", "scale")}
        time.sleep(0.1)
    raise AssertionError("temporary Snow benchmark output did not settle")


def proc_ticks(pid: int) -> int:
    fields = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").split()
    return int(fields[13]) + int(fields[14])


def proc_rss_kib(pid: int) -> int:
    for line in Path(f"/proc/{pid}/status").read_text(encoding="utf-8").splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1])
    return 0


def make_qml(mode: str, output_name: str, duration_ms: int) -> str:
    return f'''
import Quickshell
import QtQuick
import QtQuick.Window

ShellRoot {{
  id: root
  property bool measuring: false
  property int frameCount: 0
  property real frameTotalMs: 0
  property real maximumFrameMs: 0
  property int baselineSharedUpdates: 0

  function outputScreen() {{
    for (var index = 0; index < Qt.application.screens.length; index++)
      if (String(Qt.application.screens[index].name) === "{output_name}") return Qt.application.screens[index]
    return null
  }}

  Window {{
    screen: root.outputScreen()
    visibility: Window.FullScreen
    visible: true
    color: "#101315"
    title: "snow-clock-{mode}"
    Loader {{
      id: prototype
      anchors.fill: parent
      source: "{PROTOTYPE.as_uri()}"
      onLoaded: {{
        item.animationMode = "{mode}"
        item.flakeCount = 320
        item.running = true
        warmup.start()
      }}
    }}
  }}

  Timer {{
    id: warmup; interval: 1200
    onTriggered: {{
      root.baselineSharedUpdates = prototype.item.sharedUpdateCount
      console.log("BENCH_READY " + JSON.stringify({{warmupMs: interval, sampleMs: sample.interval}}))
      root.measuring = true
      sample.start()
    }}
  }}

  FrameAnimation {{
    running: root.measuring
    onTriggered: {{
      var milliseconds = frameTime * 1000
      root.frameCount += 1
      root.frameTotalMs += milliseconds
      root.maximumFrameMs = Math.max(root.maximumFrameMs, milliseconds)
    }}
  }}

  Timer {{
    id: sample; interval: {duration_ms}
    onTriggered: {{
      root.measuring = false
      prototype.item.running = false
      console.log("BEHAVE " + JSON.stringify({{
        mode: "{mode}",
        flakeCount: prototype.item.primitiveCount,
        sharedUpdates: prototype.item.sharedUpdateCount - root.baselineSharedUpdates,
        frameCount: root.frameCount,
        meanFrameMs: root.frameCount > 0 ? root.frameTotalMs / root.frameCount : 0,
        maxFrameMs: root.maximumFrameMs
      }}))
      quitDelay.start()
    }}
  }}
  Timer {{ id: quitDelay; interval: 200; onTriggered: Qt.quit() }}
}}
'''


def profile(mode: str, output_name: str, duration_ms: int) -> dict:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        shell = root / "shell.qml"
        shell.write_text(make_qml(mode, output_name, duration_ms), encoding="utf-8")
        env = os.environ.copy()
        env.update({"QT_QPA_PLATFORM": "wayland", "XDG_CONFIG_HOME": str(root / "config"),
                    "XDG_STATE_HOME": str(root / "state")})
        proc = subprocess.Popen(["quickshell", "-p", str(shell)], env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0)
        chunks: list[bytes] = []
        pending = b""
        ready_payload = None
        started_at = ended_at = target_at = 0.0
        start_ticks = end_ticks = peak_rss = samples = 0
        behave_seen = False
        deadline = time.monotonic() + duration_ms / 1000 + 15
        try:
            while time.monotonic() < deadline and not (behave_seen and ended_at > 0):
                readable, _, _ = select.select([proc.stdout], [], [], 0.04)
                if readable:
                    chunk = os.read(proc.stdout.fileno(), 4096)
                    if chunk:
                        chunks.append(chunk)
                        pending += chunk
                        lines = pending.split(b"\n")
                        pending = lines.pop()
                        for raw in lines:
                            line = raw.decode(errors="replace")
                            marker = line.find("BENCH_READY ")
                            if marker >= 0:
                                ready_payload = json.loads(line[marker + len("BENCH_READY "):])
                                started_at = time.monotonic()
                                target_at = started_at + duration_ms / 1000
                                start_ticks = end_ticks = proc_ticks(proc.pid)
                                peak_rss = proc_rss_kib(proc.pid)
                                samples = 1
                            if "BEHAVE " in line:
                                behave_seen = True
                if started_at > 0 and ended_at == 0 and proc.poll() is None:
                    now = time.monotonic()
                    end_ticks = proc_ticks(proc.pid)
                    peak_rss = max(peak_rss, proc_rss_kib(proc.pid))
                    samples += 1
                    if now >= target_at:
                        ended_at = now
                if proc.poll() is not None and not readable:
                    break
            tail, _ = proc.communicate(timeout=5)
            chunks.append(tail)
        except Exception:
            proc.kill()
            chunks.append(proc.communicate()[0])
            raise
    output = b"".join(chunks).decode(errors="replace")
    require_no_qml_errors(output)
    rows = parse_behave(output)
    if proc.returncode != 0 or not rows or ready_payload is None or ended_at <= 0:
        raise AssertionError(output[-4000:])
    measured = ended_at - started_at
    if ready_payload != {"warmupMs": 1200, "sampleMs": duration_ms} or abs(measured - duration_ms / 1000) > 0.06:
        raise AssertionError({"ready": ready_payload, "measured": measured})
    row = rows[-1]
    ticks_per_second = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
    row.update({
        "averageCpuPercent": (end_ticks - start_ticks) / ticks_per_second / measured * 100,
        "peakRssKiB": peak_rss,
        "measuredSampleSeconds": measured,
        "resourceSampleCount": samples,
        "framesPerSecond": row["frameCount"] / (duration_ms / 1000),
    })
    return row


def version(command: list[str]) -> str:
    result = run(command, check=False)
    text = (result.stdout or result.stderr).strip().splitlines()
    return text[0] if text else "unknown"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration-ms", type=int, default=2500)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "docs/performance/evidence/snow-clock-selection.json")
    args = parser.parse_args()
    if args.duration_ms < 1000 or args.repetitions < 1:
        raise SystemExit("duration must be >= 1000 ms and repetitions positive")

    output_name = f"JOBO-SNOW-CLOCK-{uuid.uuid4().hex[:8]}"
    results: list[dict] = []
    layout = None
    try:
        run(["hyprctl", "output", "create", "headless", output_name])
        wait_for_output(output_name, True)
        layout = configure_output(output_name)
        for repetition in range(1, args.repetitions + 1):
            for mode in MODES:
                row = profile(mode, output_name, args.duration_ms)
                row["repetition"] = repetition
                results.append(row)
                print(f"{mode:11} cpu={row['averageCpuPercent']:.2f}% "
                      f"rss={row['peakRssKiB']/1024:.1f}MiB frames={row['framesPerSecond']:.1f}/s")
    finally:
        run(["hyprctl", "output", "remove", output_name], check=False)
        wait_for_output(output_name, False)

    shared = [row["averageCpuPercent"] for row in results if row["mode"] == "sharedClock"]
    per_flake = [row["averageCpuPercent"] for row in results if row["mode"] == "perFlake"]
    import statistics
    selected = "sharedClock" if statistics.median(shared) < statistics.median(per_flake) else "perFlake"
    evidence = {
        "schemaVersion": 1,
        "purpose": "Snow maximum-population shared clock versus three NumberAnimations per flake",
        "machineLocalDirectionalEvidence": True,
        "isolatedConfig": True,
        "liveSettingsModified": False,
        "quickshellVersion": version(["quickshell", "--version"]),
        "qtVersion": version(["qmake6", "-query", "QT_VERSION"]),
        "flakeCount": 320,
        "perFlakeAnimationCount": 960,
        "sharedClockCount": 1,
        "sharedClockTargetUpdatesPerSecond": 30,
        "durationMs": args.duration_ms,
        "repetitions": args.repetitions,
        "temporaryOutput": layout,
        "selectedStrategy": selected,
        "medianCpuPercent": {
            "sharedClock": statistics.median(shared),
            "perFlake": statistics.median(per_flake),
        },
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"selectedStrategy": selected, "medianCpuPercent": evidence["medianCpuPercent"]}, indent=2))


if __name__ == "__main__":
    main()
