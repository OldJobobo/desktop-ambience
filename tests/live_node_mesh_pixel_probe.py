#!/usr/bin/env python3
"""Opt-in pixel proof for production Node Mesh and Canvas/Shape equivalence."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from PIL import Image, ImageChops

from qml_harness import parse_behave, qml_url, require_no_qml_errors


if os.environ.get("JOBO_AMBIENCE_NODE_MESH_PIXEL_PROBE") != "1":
    raise SystemExit("set JOBO_AMBIENCE_NODE_MESH_PIXEL_PROBE=1 to run the pixel probe")
if not os.environ.get("WAYLAND_DISPLAY"):
    raise SystemExit("an active Wayland session is required")
for tool in ("quickshell", "hyprctl"):
    if not shutil.which(tool):
        raise SystemExit(f"missing required tool: {tool}")

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / ".pi/artifacts/node-mesh-pixels"
EVIDENCE_PATH = ROOT / "docs/performance/evidence/node-mesh-pixels.json"
OUTPUT = f"JOBO-NODE-PIXEL-{uuid.uuid4().hex[:8]}"
WIDTH = 640
HEIGHT = 360
BACKGROUND = (16, 19, 21, 255)


def run(command: list[str], *, check: bool = True, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    if check and proc.returncode != 0:
        raise AssertionError(f"{command} failed\n{proc.stdout}\n{proc.stderr}")
    return proc


def wait_for_output(present: bool) -> None:
    for _ in range(80):
        rows = json.loads(run(["hyprctl", "-j", "monitors", "all"]).stdout)
        if ((OUTPUT in {str(row.get("name")) for row in rows}) is present):
            return
        import time
        time.sleep(0.1)
    raise AssertionError(f"temporary output did not settle present={present}")


def capture(case_id: str, source: str, *, production: bool, distance: int, opacity: float) -> dict:
    target = ARTIFACT_DIR / f"{case_id}.png"
    if production:
        configure = f'''
        item.effectSettings = {{
          enabled: true, intensity: 1, speed: 0.7, nodeCount: 54, nodeSize: 3,
          connectionDistance: {distance}, lineWidth: 1, lineOpacity: {opacity},
          driftAmount: 0, pointerMode: "off", mouseInfluence: 0,
          nodeColorRole: "accent", lineColorRole: "color12"
        }}
        item.reducedMotion = true
        item.theme = theme
'''
    else:
        configure = f'''
        item.running = false
        item.nodeCount = 54
        item.connectionDistance = {distance}
'''
    qml = f'''
import Quickshell
import QtQuick
import QtQuick.Window
ShellRoot {{
  function screenFor(name) {{
    for (var i = 0; i < Qt.application.screens.length; i++)
      if (String(Qt.application.screens[i].name) === name) return Qt.application.screens[i]
    return null
  }}
  QtObject {{
    id: theme
    function colorFor(name, fallback) {{
      return name === "accent" ? "#88c0d0" : (name === "color12" ? "#81a1c1" : fallback)
    }}
  }}
  Window {{
    id: window
    screen: screenFor("{OUTPUT}")
    width: {WIDTH}; height: {HEIGHT}; visible: true
    flags: Qt.Tool | Qt.WindowDoesNotAcceptFocus
    color: "#101315"
    Item {{
      id: host; anchors.fill: parent
      Rectangle {{ anchors.fill: parent; color: "#101315" }}
      Loader {{
        id: renderer; anchors.fill: parent; source: "{qml_url(source)}"
        onLoaded: {{ {configure}; settle.start() }}
      }}
    }}
    Timer {{
      id: settle; interval: 500
      onTriggered: host.grabToImage(function(result) {{
        var saved = result.saveToFile("{target.as_posix()}")
        console.log("BEHAVE " + JSON.stringify({{
          caseId: "{case_id}", saved: saved, edgeCount: renderer.item.edgeCount,
          pathCount: renderer.item.pathObjectCount !== undefined
            ? renderer.item.pathObjectCount : renderer.item.shapePathCount
        }}))
        Qt.quit()
      }})
    }}
  }}
}}
'''
    with tempfile.TemporaryDirectory() as directory:
        shell = Path(directory) / "shell.qml"
        shell.write_text(qml, encoding="utf-8")
        env = os.environ.copy()
        env["QT_QPA_PLATFORM"] = "wayland"
        env["XDG_CONFIG_HOME"] = str(Path(directory) / "config")
        env["XDG_STATE_HOME"] = str(Path(directory) / "state")
        proc = subprocess.run(
            ["quickshell", "-p", str(shell)], env=env,
            capture_output=True, text=True, timeout=15,
        )
    output = proc.stdout + proc.stderr
    require_no_qml_errors(output)
    rows = parse_behave(output)
    if proc.returncode != 0 or not rows or not rows[-1]["saved"] or not target.is_file():
        raise AssertionError(f"capture failed: {case_id}\n{output[-3000:]}")
    return rows[-1]


def changed_pixels(first: Path, second: Path) -> int:
    difference = ImageChops.difference(Image.open(first).convert("RGBA"), Image.open(second).convert("RGBA"))
    return sum(1 for pixel in difference.get_flattened_data() if pixel != (0, 0, 0, 0))


def visible_pixels(path: Path) -> int:
    return sum(1 for pixel in Image.open(path).convert("RGBA").get_flattened_data() if pixel != BACKGROUND)


def mask(path: Path) -> set[int]:
    return {
        index for index, pixel in enumerate(Image.open(path).convert("RGBA").get_flattened_data())
        if pixel != BACKGROUND
    }


ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
for old in ARTIFACT_DIR.glob("*.png"):
    old.unlink()

rows: list[dict] = []
try:
    run(["hyprctl", "output", "create", "headless", OUTPUT])
    wait_for_output(True)
    run(["hyprctl", "eval", (
        "hl.monitor({" + f'output = "{OUTPUT}", mode = "{WIDTH}x{HEIGHT}@60", '
        'position = "-640x0", scale = 1, transform = 0})'
    )])
    rows.extend([
        capture("production-lines-off", "effects/NodeMeshEffect.qml", production=True, distance=132, opacity=0),
        capture("production-lines-on", "effects/NodeMeshEffect.qml", production=True, distance=132, opacity=1),
        capture("production-long-distance", "effects/NodeMeshEffect.qml", production=True, distance=260, opacity=1),
        capture("prototype-canvas", "tests/prototypes/node-mesh/CanvasPrototype.qml", production=False, distance=132, opacity=0.3),
        capture("prototype-shape", "tests/prototypes/node-mesh/ShapePrototype.qml", production=False, distance=132, opacity=0.3),
    ])
finally:
    run(["hyprctl", "output", "remove", OUTPUT], check=False)
    wait_for_output(False)

paths = {path.stem: path for path in ARTIFACT_DIR.glob("*.png")}
line_delta = changed_pixels(paths["production-lines-off"], paths["production-lines-on"])
distance_delta = changed_pixels(paths["production-lines-on"], paths["production-long-distance"])
short_visible = visible_pixels(paths["production-lines-on"])
long_visible = visible_pixels(paths["production-long-distance"])
canvas_mask = mask(paths["prototype-canvas"])
shape_mask = mask(paths["prototype-shape"])
intersection = len(canvas_mask & shape_mask)
union = len(canvas_mask | shape_mask)
jaccard = intersection / union if union else 0
overlap_of_smaller = intersection / min(len(canvas_mask), len(shape_mask)) if intersection else 0
prototype_delta = changed_pixels(paths["prototype-canvas"], paths["prototype-shape"])

if line_delta < 100:
    raise AssertionError(f"line opacity did not produce visible connection pixels: {line_delta}")
if distance_delta < 100 or long_visible <= short_visible:
    raise AssertionError(f"distance did not visibly increase connections: {distance_delta}, {short_visible}, {long_visible}")
if len(canvas_mask) < 100 or len(shape_mask) < 100 or overlap_of_smaller < 0.98:
    raise AssertionError(
        "prototype line geometry not equivalent: "
        f"canvas={len(canvas_mask)} shape={len(shape_mask)} overlap={overlap_of_smaller}"
    )

result = {
    "schemaVersion": 1,
    "renderProven": True,
    "productionLineOpacityChangedPixels": line_delta,
    "productionConnectionDistanceChangedPixels": distance_delta,
    "productionShortVisiblePixels": short_visible,
    "productionLongVisiblePixels": long_visible,
    "canvasVisiblePixels": len(canvas_mask),
    "shapeVisiblePixels": len(shape_mask),
    "canvasShapeMaskJaccard": jaccard,
    "canvasShapeSmallerMaskOverlap": overlap_of_smaller,
    "canvasShapeChangedPixels": prototype_delta,
    "captures": rows,
    "artifactDirectory": ".pi/artifacts/node-mesh-pixels",
}
EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
EVIDENCE_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, indent=2))
