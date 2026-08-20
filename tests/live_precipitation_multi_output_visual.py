#!/usr/bin/env python3
"""Opt-in reversible rain/snow visual probe on two negative-origin outputs."""

from __future__ import annotations

import hashlib
import json
import os
import select
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

from PIL import Image, ImageStat

from qml_harness import parse_behave, qml_url, require_no_qml_errors


if os.environ.get("JOBO_AMBIENCE_LIVE_PHASE6") != "1":
    raise SystemExit("set JOBO_AMBIENCE_LIVE_PHASE6=1 to run the precipitation multi-output check")
if not os.environ.get("WAYLAND_DISPLAY"):
    raise SystemExit("an active Wayland session is required")
for tool in ("quickshell", "hyprctl", "grim"):
    if not shutil.which(tool):
        raise SystemExit(f"missing required tool: {tool}")

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = [f"JOBO-PRECIP-VIS-{uuid.uuid4().hex[:8]}-{index}" for index in range(2)]
ARTIFACT_DIR = Path(os.environ.get(
    "JOBO_AMBIENCE_PRECIPITATION_MULTI_ARTIFACTS",
    ROOT / ".pi/artifacts/precipitation-multi-output",
)).resolve()
EVIDENCE_PATH = ROOT / "docs/release/evidence/precipitation-multi-output.json"
MARKERS = [
    {"color": "#ff1744", "rgb": (255, 23, 68)},
    {"color": "#00e676", "rgb": (0, 230, 118)},
]


def run(command: list[str], *, timeout: int = 30, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    if check and proc.returncode != 0:
        raise AssertionError(f"{command} failed ({proc.returncode})\n{proc.stdout}\n{proc.stderr}")
    return proc


def monitors() -> list[dict]:
    return json.loads(run(["hyprctl", "-j", "monitors", "all"]).stdout)


def wait_for_outputs(present: bool, timeout: float = 10) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        current = {str(item.get("name")) for item in monitors()}
        if all((name in current) is present for name in OUTPUTS):
            return
        time.sleep(0.1)
    raise AssertionError(f"temporary outputs did not settle present={present}")


def configure_output(name: str, x: int, y: int) -> dict:
    expression = (
        "hl.monitor({"
        f'output = "{name}", mode = "1920x1080@60", position = "{x}x{y}", '
        "scale = 1, transform = 0"
        "})"
    )
    run(["hyprctl", "eval", expression])
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        monitor = next((item for item in monitors() if str(item.get("name")) == name), None)
        if monitor and int(monitor.get("x", 0)) == x and int(monitor.get("y", 0)) == y:
            return {
                "name": name, "x": int(monitor["x"]), "y": int(monitor["y"]),
                "width": int(monitor["width"]), "height": int(monitor["height"]),
                "scale": float(monitor.get("scale", 1)),
            }
        time.sleep(0.1)
    raise AssertionError(f"output {name} did not settle at {x}x{y}")


def qml_source(layout: list[dict]) -> str:
    windows = []
    for index, output in enumerate(layout):
        style = "rain" if index == 0 else "snow"
        windows.append(f'''
  PanelWindow {{
    screen: root.renderScreen("{output['name']}")
    color: "#101315"
    WlrLayershell.namespace: "jobo-precipitation-multi-{index}"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
    exclusionMode: ExclusionMode.Ignore
    mask: Region {{}}
    anchors {{ top: true; bottom: true; left: true; right: true }}
    Loader {{
      id: effect{index}
      anchors.fill: parent
      source: "{qml_url('effects/RainfallEffect.qml')}"
      onLoaded: root.configure(item, "{style}")
    }}
    Rectangle {{ x: 24; y: 24; width: 48; height: 48; color: "{MARKERS[index]['color']}" }}
  }}''')

    settings = {
        "enabled": True, "intensity": 0.72, "speed": 0.62,
        "precipitationStyle": "rain", "dropCount": 180, "slant": 0.08,
        "accentBlend": 0.42, "vignette": True, "mistAmount": 0.34,
        "splashAmount": 0.38, "flakeSize": 6, "flutterAmount": 0.58,
        "flakeDetail": "mixed",
    }
    return f'''
import Quickshell
import Quickshell.Wayland
import QtQuick

ShellRoot {{
  id: root
  property int loadedCount: 0
  function renderScreen(name) {{
    for (var index = 0; index < Quickshell.screens.length; index++)
      if (String(Quickshell.screens[index].name) === name) return Quickshell.screens[index]
    return null
  }}
  function configure(item, style) {{
    var configured = {json.dumps(settings)}
    configured.precipitationStyle = style
    item.effectSettings = configured
    item.reducedMotion = true
    item.theme = theme
    loadedCount += 1
    if (loadedCount === 2) settle.start()
  }}
  function report() {{
    var items = [effect0.item, effect1.item]
    var metrics = []
    for (var index = 0; index < items.length; index++) {{
      var item = items[index]
      metrics.push({{
        output: index === 0 ? "{layout[0]['name']}" : "{layout[1]['name']}",
        style: item.selectedStyle,
        loadedStyleCount: item.loadedStyleCount,
        particleCount: item.boundedParticleCount,
        primitiveCount: item.selectedStyle === "snow"
          ? item.snowPrimitiveCount : item.boundedParticleCount,
        autonomousMotionRunning: item.autonomousMotionRunning,
        runningAnimationCount: item.runningAnimationCount,
        runningClockCount: item.runningClockCount
      }})
    }}
    console.log("BEHAVE " + JSON.stringify({{metrics: metrics}}))
  }}
  QtObject {{
    id: theme
    function colorFor(name, fallback) {{
      var colors = {{background: "#101315", foreground: "#d8dee9", accent: "#88c0d0",
        color14: "#8fbcbb", color15: "#eceff4"}}
      return colors[name] || fallback
    }}
  }}
  Timer {{ id: settle; interval: 700; onTriggered: root.report() }}
  {''.join(windows)}
}}
'''


def image_metrics(path: Path, marker: dict) -> dict:
    image = Image.open(path).convert("RGB")
    observed = image.getpixel((48, 48))
    marker_ok = all(abs(observed[channel] - marker["rgb"][channel]) <= 12 for channel in range(3))
    deviation = sum(ImageStat.Stat(image).stddev) / 3
    return {
        "file": path.name,
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "width": image.width,
        "height": image.height,
        "standardDeviation": deviation,
        "markerObserved": list(observed),
        "markerMatched": marker_ok,
    }


ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
layout: list[dict] = []
try:
    for name in OUTPUTS:
        run(["hyprctl", "output", "create", "headless", name])
    wait_for_outputs(True)
    layout = [
        configure_output(OUTPUTS[0], -3840, -180),
        configure_output(OUTPUTS[1], -1920, 0),
    ]
    with tempfile.TemporaryDirectory() as directory:
        temp = Path(directory)
        shell = temp / "shell.qml"
        shell.write_text(qml_source(layout), encoding="utf-8")
        env = os.environ.copy()
        env.update({
            "QT_QPA_PLATFORM": "wayland",
            "XDG_CONFIG_HOME": str(temp / "config"),
            "XDG_STATE_HOME": str(temp / "state"),
        })
        proc = subprocess.Popen(
            ["quickshell", "-p", str(shell)], env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        lines: list[str] = []
        output = ""
        try:
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline and proc.poll() is None:
                ready, _, _ = select.select([proc.stdout], [], [], 0.2)
                if not ready:
                    continue
                line = proc.stdout.readline()
                if not line:
                    continue
                lines.append(line)
                if "BEHAVE " in line:
                    break
            output = "".join(lines)
            rows = parse_behave(output)
            if not rows:
                raise AssertionError(f"multi-output visual produced no metrics\n{output[-4000:]}")
            for index, name in enumerate(OUTPUTS):
                run(["grim", "-o", name, str(ARTIFACT_DIR / f"precipitation-output-{index}.png")])
        finally:
            if proc.poll() is None:
                proc.terminate()
            tail, _ = proc.communicate(timeout=5)
            output += tail
    require_no_qml_errors(output)
    metrics = rows[-1]["metrics"]
    if [item["style"] for item in metrics] != ["rain", "snow"]:
        raise AssertionError(metrics)
    if any(item["loadedStyleCount"] != 1 or item["autonomousMotionRunning"] is not False
           or item["runningAnimationCount"] != 0 or item["runningClockCount"] != 0
           for item in metrics):
        raise AssertionError(metrics)
    if metrics[0]["particleCount"] <= 0 or metrics[1]["particleCount"] != 180:
        raise AssertionError(metrics)
    if metrics[1]["primitiveCount"] < metrics[1]["particleCount"] \
            or metrics[1]["primitiveCount"] > metrics[1]["particleCount"] * 4:
        raise AssertionError(metrics)
    images = [
        image_metrics(ARTIFACT_DIR / f"precipitation-output-{index}.png", MARKERS[index])
        for index in range(2)
    ]
    if any(not image["markerMatched"] or image["standardDeviation"] <= 1
           or (image["width"], image["height"]) != (1920, 1080) for image in images):
        raise AssertionError(images)
    if images[0]["sha256"] == images[1]["sha256"]:
        raise AssertionError("rain and snow multi-output screenshots are byte-identical")
    evidence = {
        "schemaVersion": 1,
        "isolatedConfig": True,
        "liveSettingsModified": False,
        "persistentHyprlandConfigModified": False,
        "temporaryOutputLayout": layout,
        "negativeOriginCovered": all(item["x"] < 0 or item["y"] < 0 for item in layout),
        "styles": ["rain", "snow"],
        "reducedMotion": True,
        "metrics": metrics,
        "compositorPlacementVerified": True,
        "screenshotsNonBlankAndDistinct": True,
        "images": images,
    }
    EVIDENCE_PATH.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2))
finally:
    for name in reversed(OUTPUTS):
        run(["hyprctl", "output", "remove", name], check=False)
    try:
        wait_for_outputs(False, timeout=5)
    except Exception:
        pass
