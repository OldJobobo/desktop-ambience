#!/usr/bin/env python3
"""Capture isolated pre-refactor Rainfall visual evidence on a temporary output."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

from qml_harness import parse_behave, qml_url, require_no_qml_errors


if os.environ.get("JOBO_AMBIENCE_RAIN_BASELINE") != "1":
    raise SystemExit("set JOBO_AMBIENCE_RAIN_BASELINE=1 to capture the Rainfall baseline")
if not os.environ.get("WAYLAND_DISPLAY"):
    raise SystemExit("an active Wayland session is required")
for tool in ("quickshell", "hyprctl", "magick"):
    if not shutil.which(tool):
        raise SystemExit(f"missing required tool: {tool}")

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "docs/release/evidence/rainfall-baseline"
EVIDENCE_PATH = ARTIFACT_DIR / "visual.json"
output_name = f"JOBO-RAIN-BASELINE-{uuid.uuid4().hex[:8]}"
window_title = f"jobo-rain-baseline-{uuid.uuid4().hex[:8]}"


def run(command: list[str], *, timeout: int = 30, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    if check and proc.returncode != 0:
        raise AssertionError(f"{command} failed ({proc.returncode})\n{proc.stdout}\n{proc.stderr}")
    return proc


def monitors() -> list[dict]:
    return json.loads(run(["hyprctl", "-j", "monitors", "all"]).stdout)


def wait_for_output(present: bool, timeout: float = 8) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        found = any(str(item.get("name")) == output_name for item in monitors())
        if found is present:
            return
        time.sleep(0.1)
    raise AssertionError(f"output {output_name} present={present} did not settle")


def place_render_window() -> None:
    output = next((item for item in monitors() if item.get("name") == output_name), None)
    if not output:
        raise AssertionError("temporary output disappeared")
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        matches = [
            client for client in json.loads(run(["hyprctl", "-j", "clients"]).stdout)
            if str(client.get("title")) == window_title
        ]
        if len(matches) > 1:
            raise AssertionError(f"expected one render window, found {len(matches)}")
        if matches:
            address = str(matches[0].get("address", ""))
            if not address.startswith("0x"):
                raise AssertionError(f"invalid window address: {address}")
            run(["hyprctl", "dispatch", (
                'hl.dsp.window.move({'
                f'monitor = "{output_name}", follow = false, window = "address:{address}"'
                '})'
            )])
            move_deadline = time.monotonic() + 5
            while time.monotonic() < move_deadline:
                current = next((client for client in json.loads(run(["hyprctl", "-j", "clients"]).stdout)
                                if str(client.get("title")) == window_title), None)
                if current and int(current.get("monitor", -1)) == int(output["id"]):
                    return
                time.sleep(0.1)
            raise AssertionError("render window did not move to temporary output")
        time.sleep(0.1)
    raise AssertionError("render window did not appear")


def configure_output() -> dict:
    expression = (
        "hl.monitor({"
        f'output = "{output_name}", mode = "1920x1080@60", position = "-1920x-1080", '
        "scale = 1, transform = 0"
        "})"
    )
    run(["hyprctl", "eval", expression])
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        monitor = next((item for item in monitors() if item.get("name") == output_name), None)
        if monitor and int(monitor.get("x", 0)) == -1920 and int(monitor.get("y", 0)) == -1080:
            return {key: monitor.get(key) for key in ("name", "x", "y", "width", "height", "scale", "transform")}
        time.sleep(0.1)
    raise AssertionError("temporary output geometry did not settle")


def qml_source(static_path: Path, animated_path: Path) -> str:
    settings = json.dumps({
        "enabled": True, "intensity": 0.72, "speed": 0.62, "dropCount": 180,
        "slant": 0.08, "mistAmount": 0.34, "splashAmount": 0.38,
        "accentBlend": 0.42, "vignette": True,
    })
    return f'''
import Quickshell
import QtQuick
import QtQuick.Window
ShellRoot {{
  id: root
  property var renderScreen: null
  property var windowScreen: null
  property bool capturePending: false
  property var staticSnapshots: []
  function findRenderScreen() {{
    for (var i = 0; i < Quickshell.screens.length; i++)
      if (String(Quickshell.screens[i].name) === "{output_name}") return Quickshell.screens[i]
    return null
  }}
  function findWindowScreen() {{
    for (var i = 0; i < Qt.application.screens.length; i++)
      if (String(Qt.application.screens[i].name) === "{output_name}") return Qt.application.screens[i]
    return null
  }}
  function snapshot() {{
    var rows = []
    for (var i = 0; i < effect.item.primaryDropCount; i++)
      rows.push(effect.item.primaryDropSnapshot(i))
    return rows
  }}
  function capture(path, done) {{
    if (capturePending) return
    capturePending = true
    effect.item.grabToImage(function(result) {{
      if (!result.saveToFile(path)) console.log("BEHAVE_ERR failed to save " + path)
      capturePending = false
      done()
    }})
  }}
  Component.onCompleted: screenProbe.start()
  Timer {{
    id: screenProbe; interval: 50; repeat: true; property int attempts: 0
    onTriggered: {{
      attempts += 1
      root.renderScreen = root.findRenderScreen()
      root.windowScreen = root.findWindowScreen()
      if (root.renderScreen && root.windowScreen) {{ stop(); window.visible = true; start.start() }}
      else if (attempts > 160) {{ console.log("BEHAVE_ERR screen missing"); Qt.quit() }}
    }}
  }}
  Timer {{ id: start; interval: 900; onTriggered: effect.source = "{qml_url('effects/RainfallEffect.qml')}" }}
  Window {{
    id: window; screen: root.windowScreen; visibility: Window.FullScreen; visible: false
    title: "{window_title}"; color: "#101315"
    Loader {{
      id: effect; anchors.fill: parent
      onLoaded: {{ item.effectSettings = {settings}; item.reducedMotion = true; staticSettle.start() }}
    }}
    Timer {{
      id: staticSettle; interval: 250
      onTriggered: {{
        root.staticSnapshots = root.snapshot()
        root.capture("{static_path}", function() {{
          effect.item.reducedMotion = false
          animatedSettle.start()
        }})
      }}
    }}
    Timer {{
      id: animatedSettle; interval: 650
      onTriggered: root.capture("{animated_path}", function() {{
        var moving = root.snapshot()
        console.log("BEHAVE " + JSON.stringify({{
          output: "{output_name}",
          width: effect.item.width,
          height: effect.item.height,
          primaryDrops: effect.item.primaryDropCount,
          sheetDrops: effect.item.sheetDropCount,
          foregroundDrops: effect.item.foregroundDropCount,
          splashes: effect.item.splashCount,
          mistBands: effect.item.mistBandCount,
          staticSnapshots: root.staticSnapshots,
          animatedSnapshots: moving,
          autonomousMotionRunning: effect.item.autonomousMotionRunning,
          visualLayerEnabled: effect.item.visualLayerEnabled
        }}))
        Qt.quit()
      }})
    }}
  }}
}}
'''


def image_metrics(path: Path) -> dict:
    output = run([
        "magick", str(path), "-format",
        "%w %h %[fx:mean] %[fx:standard_deviation] %[entropy]", "info:",
    ]).stdout.strip().split()
    return {
        "file": path.name,
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "width": int(output[0]),
        "height": int(output[1]),
        "mean": float(output[2]),
        "standardDeviation": float(output[3]),
        "entropy": float(output[4]),
    }


def bright_fraction(path: Path, geometry: str) -> float:
    return float(run([
        "magick", str(path), "-crop", geometry, "+repage", "-colorspace", "gray",
        "-threshold", "18%", "-format", "%[fx:mean]", "info:",
    ]).stdout.strip())


ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
static_path = ARTIFACT_DIR / "rainfall-static.png"
animated_path = ARTIFACT_DIR / "rainfall-animated.png"
try:
    run(["hyprctl", "output", "create", "headless", output_name])
    wait_for_output(True)
    geometry = configure_output()
    with tempfile.TemporaryDirectory() as shell_dir, tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as state_dir:
        shell_root = Path(shell_dir)
        shell = shell_root / "shell.qml"
        shell.write_text(qml_source(static_path, animated_path), encoding="utf-8")
        omarchy_shell = Path(os.environ.get("OMARCHY_PATH", "/usr/share/omarchy")) / "shell"
        for module in ("Commons", "Ui"):
            (shell_root / module).symlink_to(omarchy_shell / module, target_is_directory=True)
        env = os.environ.copy()
        env.update({"QT_QPA_PLATFORM": "wayland", "XDG_CONFIG_HOME": config_dir, "XDG_STATE_HOME": state_dir})
        proc = subprocess.Popen(
            [shutil.which("quickshell") or "quickshell", "-p", str(shell)],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        try:
            place_render_window()
            stdout, stderr = proc.communicate(timeout=20)
        except Exception:
            proc.kill()
            proc.communicate()
            raise
    output = stdout + stderr
    require_no_qml_errors(output)
    rows = parse_behave(output)
    if proc.returncode != 0 or not rows:
        raise AssertionError(output[-4000:])
    row = rows[-1]
    for path in (static_path, animated_path):
        if not path.is_file() or path.stat().st_size < 1024:
            raise AssertionError(f"missing or empty image: {path}")
    images = [image_metrics(static_path), image_metrics(animated_path)]
    if any(item["standardDeviation"] <= 0.001 for item in images):
        raise AssertionError(images)
    coverage = {
        "staticTop": bright_fraction(static_path, "1920x540+0+0"),
        "staticBottom": bright_fraction(static_path, "1920x540+0+540"),
        "animatedTop": bright_fraction(animated_path, "1920x540+0+0"),
        "animatedBottom": bright_fraction(animated_path, "1920x540+0+540"),
    }
    if coverage["staticTop"] <= 0.004 or coverage["animatedTop"] <= 0.004 \
            or coverage["staticBottom"] <= 0.1 or coverage["animatedBottom"] <= 0.1:
        raise AssertionError(coverage)
    moved = sum(
        abs(float(after["currentY"]) - float(before["currentY"])) > 1
        for before, after in zip(row["staticSnapshots"], row["animatedSnapshots"], strict=True)
    )
    if moved < 150:
        raise AssertionError(f"only {moved} primary drops moved")
    evidence = {
        "schemaVersion": 1,
        "sourceCommit": run(["git", "-C", str(ROOT), "rev-parse", "HEAD"]).stdout.strip(),
        "isolatedConfig": True,
        "liveSettingsModified": False,
        "temporaryOutput": geometry,
        "defaults": {
            "enabled": True, "intensity": 0.72, "speed": 0.62, "dropCount": 180,
            "slant": 0.08, "mistAmount": 0.34, "splashAmount": 0.38,
            "accentBlend": 0.42, "vignette": True,
        },
        "population": {key: row[key] for key in ("primaryDrops", "sheetDrops", "foregroundDrops", "splashes", "mistBands")},
        "visualLayerEnabledFalseStillRendered": row["visualLayerEnabled"] is False,
        "autonomousMotionRunning": row["autonomousMotionRunning"],
        "movedPrimaryDrops": moved,
        "startupCoverage": coverage,
        "images": images,
    }
    EVIDENCE_PATH.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2))
finally:
    run(["hyprctl", "output", "remove", output_name], check=False)
    try:
        wait_for_output(False, timeout=5)
    except Exception:
        pass
