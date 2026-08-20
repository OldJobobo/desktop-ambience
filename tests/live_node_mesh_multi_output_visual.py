#!/usr/bin/env python3
"""Opt-in reversible two-output Node Mesh visual and pointer-ownership probe."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
import os
import select
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

from PIL import Image

from qml_harness import parse_behave, qml_url, require_no_qml_errors


if os.environ.get("JOBO_AMBIENCE_LIVE_PHASE6") != "1":
    raise SystemExit("set JOBO_AMBIENCE_LIVE_PHASE6=1 to run the Node Mesh multi-output visual check")
if not os.environ.get("WAYLAND_DISPLAY"):
    raise SystemExit("an active Wayland session is required")
for tool in ("quickshell", "hyprctl", "grim"):
    if not shutil.which(tool):
        raise SystemExit(f"missing required tool: {tool}")

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = [f"JOBO-NODE-VIS-{uuid.uuid4().hex[:8]}-{index}" for index in range(2)]
ARTIFACT_DIR = Path(os.environ.get(
    "JOBO_AMBIENCE_NODE_MESH_MULTI_ARTIFACTS",
    ROOT / ".pi/artifacts/node-mesh-multi-output",
)).resolve()
EVIDENCE_PATH = ROOT / "docs/release/evidence/node-mesh-multi-output.json"
OUTPUT_MARKERS = [
    {"color": "#ff1744", "rgb": (255, 23, 68), "x": 24, "y": 24, "size": 48},
    {"color": "#00e676", "rgb": (0, 230, 118), "x": 104, "y": 24, "size": 48},
]
MARKER_CHANNEL_TOLERANCE = 12


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


def marker_observation(path: Path, marker: dict) -> tuple[int, int, int]:
    image = Image.open(path).convert("RGB")
    center_x = marker["x"] + marker["size"] // 2
    center_y = marker["y"] + marker["size"] // 2
    return image.getpixel((center_x, center_y))


def marker_matches(path: Path, marker: dict) -> bool:
    observed = marker_observation(path, marker)
    return all(abs(observed[index] - marker["rgb"][index]) <= MARKER_CHANNEL_TOLERANCE
               for index in range(3))


def qml_source(layout: list[dict]) -> str:
    settings = {
        "enabled": True, "intensity": 0.48, "speed": 0.7, "nodeCount": 54,
        "nodeSize": 3, "connectionDistance": 132, "lineWidth": 1,
        "lineOpacity": 0.3, "driftAmount": 0.38, "pointerMode": "attract",
        "mouseInfluence": 1, "nodeColorRole": "accent", "lineColorRole": "color12",
    }
    windows = []
    for index, output in enumerate(layout):
        windows.append(f'''
  PanelWindow {{
    screen: root.renderScreen("{output['name']}")
    color: "#101315"
    WlrLayershell.namespace: "jobo-node-mesh-multi-{index}"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
    exclusionMode: ExclusionMode.Ignore
    mask: Region {{}}
    anchors {{ top: true; bottom: true; left: true; right: true }}
    Loader {{
      id: effect{index}
      anchors.fill: parent
      source: "{qml_url('effects/NodeMeshEffect.qml')}"
      onLoaded: root.configure(item, "{output['name']}")
    }}
    Rectangle {{
      x: {OUTPUT_MARKERS[index]['x']}; y: {OUTPUT_MARKERS[index]['y']}
      width: {OUTPUT_MARKERS[index]['size']}; height: {OUTPUT_MARKERS[index]['size']}
      color: "{OUTPUT_MARKERS[index]['color']}"
    }}
  }}''')

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
  function windowScreen(name) {{
    for (var index = 0; index < Qt.application.screens.length; index++)
      if (String(Qt.application.screens[index].name) === name) return Qt.application.screens[index]
    return null
  }}
  function configure(item, outputName) {{
    var configured = {json.dumps(settings)}
    if (outputName === "{layout[1]['name']}") configured.connectionDistance = 260
    item.effectSettings = configured
    item.targetScreen = renderScreen(outputName)
    item.cursorTracker = tracker
    item.theme = theme
    loadedCount += 1
    if (loadedCount === 2) settle.start()
  }}
  function reportEvidence() {{
    var items = [effect0.item, effect1.item]
    var metrics = []
    for (var index = 0; index < items.length; index++) {{
      var item = items[index]
      metrics.push({{
        output: "{layout[0]['name']}" === String(item.targetScreen.name)
          ? "{layout[0]['name']}" : "{layout[1]['name']}",
        originX: item.screenOriginX, originY: item.screenOriginY,
        rawCursorLocalX: item.rawCursorLocalX, rawCursorLocalY: item.rawCursorLocalY,
        cursorOwned: item.cursorOwned, pointerForceActive: item.pointerForceActive,
        simulationRunning: item.simulationRunning, updates: item.simulationUpdateCount,
        nodeCount: item.acceptedNodeCount, connectionDistance: item.connectionDistance,
        edgeCount: item.edgeCount,
        pathCount: item.shapePathCount
      }})
    }}
    console.log("BEHAVE " + JSON.stringify({{metrics: metrics}}))
  }}

  QtObject {{
    id: tracker
    property bool hasCursorSample: true
    property real cursorX: {layout[0]['x'] + 960}
    property real cursorY: {layout[0]['y'] + 540}
    property real displayCursorX: cursorX
    property real displayCursorY: cursorY
  }}
  QtObject {{
    id: theme
    function colorFor(name, fallback) {{
      return name === "accent" ? "#88c0d0" : (name === "color12" ? "#81a1c1" : fallback)
    }}
  }}
  Timer {{ id: settle; interval: 1200; onTriggered: root.reportEvidence() }}
  {''.join(windows)}
}}
'''


ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
for path in ARTIFACT_DIR.glob("nodeMesh-output-*.png"):
    path.unlink()

layout: list[dict] = []
try:
    for name in OUTPUTS:
        run(["hyprctl", "output", "create", "headless", name])
    wait_for_outputs(True)
    layout = [configure_output(OUTPUTS[0], -3840, 0), configure_output(OUTPUTS[1], -1920, 180)]

    with tempfile.TemporaryDirectory() as directory:
        shell = Path(directory) / "shell.qml"
        shell.write_text(qml_source(layout), encoding="utf-8")
        env = os.environ.copy()
        env["QT_QPA_PLATFORM"] = "wayland"
        env["XDG_CONFIG_HOME"] = str(Path(directory) / "config")
        env["XDG_STATE_HOME"] = str(Path(directory) / "state")
        proc = subprocess.Popen(
            ["quickshell", "-p", str(shell)], env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        lines: list[str] = []
        output = ""
        deadline = time.monotonic() + 15
        try:
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
                run(["grim", "-o", name, str(ARTIFACT_DIR / f"nodeMesh-output-{index}.png")])
        finally:
            if proc.poll() is None:
                proc.terminate()
            tail, _ = proc.communicate(timeout=5)
            output += tail
    require_no_qml_errors(output)
    metrics = rows[-1]["metrics"]
    if [item["cursorOwned"] for item in metrics] != [True, False]:
        raise AssertionError(metrics)
    if [item["pointerForceActive"] for item in metrics] != [True, False]:
        raise AssertionError(metrics)
    if any(item["updates"] <= 0 or item["nodeCount"] != 54 or item["pathCount"] != 8
           or item["edgeCount"] > 108 for item in metrics):
        raise AssertionError(metrics)
    if [item["connectionDistance"] for item in metrics] != [132, 260]:
        raise AssertionError(metrics)

    expected_origins = [(item["x"], item["y"]) for item in layout]
    reported_origins = [(item["originX"], item["originY"]) for item in metrics]
    if reported_origins != expected_origins:
        raise AssertionError(f"renderer origins do not match compositor layout: {reported_origins} != {expected_origins}")

    images = []
    image_hashes = []
    image_paths = []
    for index in range(2):
        path = ARTIFACT_DIR / f"nodeMesh-output-{index}.png"
        if not path.is_file() or path.stat().st_size < 1024:
            raise AssertionError(f"missing visual artifact: {path}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        pixels = list(Image.open(path).convert("RGBA").get_flattened_data())
        dominant_count = Counter(pixels).most_common(1)[0][1]
        visible_pixels = len(pixels) - dominant_count
        if visible_pixels < 100:
            raise AssertionError(f"blank Node Mesh output {index}: {visible_pixels} visible pixels")
        image_hashes.append(digest)
        image_paths.append(path)
        observed_marker = marker_observation(path, OUTPUT_MARKERS[index])
        images.append({
            "file": path.name,
            "intendedOutput": layout[index]["name"],
            "intendedOrigin": {"x": layout[index]["x"], "y": layout[index]["y"]},
            "marker": {
                "position": {"x": OUTPUT_MARKERS[index]["x"], "y": OUTPUT_MARKERS[index]["y"]},
                "expectedRgb": list(OUTPUT_MARKERS[index]["rgb"]),
                "observedRgb": list(observed_marker),
            },
            "bytes": path.stat().st_size,
            "sha256": digest,
            "visiblePixels": visible_pixels,
        })
    if len(set(image_hashes)) != len(image_hashes):
        raise AssertionError("multi-output Node Mesh screenshots are byte-identical")
    assignment_matrix = [
        [marker_matches(path, marker) for marker in OUTPUT_MARKERS]
        for path in image_paths
    ]
    expected_assignment = [[True, False], [False, True]]
    if assignment_matrix != expected_assignment:
        raise AssertionError(
            f"screenshots are not associated with their intended compositor outputs: {assignment_matrix}"
        )
    swapped_paths = list(reversed(image_paths))
    swapped_assignment_rejected = any(
        not marker_matches(swapped_paths[index], OUTPUT_MARKERS[index]) for index in range(2)
    )
    if not swapped_assignment_rejected:
        raise AssertionError("swapped compositor captures were not rejected")
    try:
        artifact_reference = str(ARTIFACT_DIR.relative_to(ROOT))
    except ValueError:
        artifact_reference = str(ARTIFACT_DIR)
    evidence = {
        "schemaVersion": 2,
        "isolatedConfig": True,
        "liveSettingsModified": False,
        "temporaryOutputLayout": layout,
        "negativeOriginsCovered": all(item["x"] < 0 for item in layout),
        "differingOriginsCovered": len({(item["x"], item["y"]) for item in layout}) == 2,
        "compositorPlacementVerified": (
            reported_origins == expected_origins and assignment_matrix == expected_assignment
        ),
        "screenshotOutputAssignmentMatrix": assignment_matrix,
        "swappedCaptureAssignmentRejected": swapped_assignment_rejected,
        "screenshotsNonBlankAndDistinct": len(set(image_hashes)) == len(image_hashes),
        "singleOutputPointerOwnership": [item["cursorOwned"] for item in metrics] == [True, False],
        "metrics": metrics,
        "images": images,
        "artifactDirectory": artifact_reference,
    }
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2))
finally:
    for name in reversed(OUTPUTS):
        run(["hyprctl", "output", "remove", name], check=False)
    try:
        wait_for_outputs(False, timeout=5)
    except Exception:
        pass
