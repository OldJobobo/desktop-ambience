#!/usr/bin/env python3
"""Opt-in reversible mixed-scale and mixed-refresh Phase 6 validation.

A temporary headless output covers fractional scale and rotation. One
non-focused physical output is briefly switched to another advertised refresh
rate, then restored from its exact pre-test monitor state in a finally block.
No persistent Hyprland configuration is edited.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
import uuid
from pathlib import Path


if os.environ.get("JOBO_AMBIENCE_LIVE_PHASE6") != "1":
    raise SystemExit("set JOBO_AMBIENCE_LIVE_PHASE6=1 to run the output-mode matrix")
for tool in ("hyprctl", "omarchy-shell"):
    if not shutil.which(tool):
        raise SystemExit(f"missing required tool: {tool}")

ROOT = Path(__file__).resolve().parents[1]
VERSION = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))["version"]
ARTIFACT_DIR = ROOT / "docs/release/evidence" / VERSION
headless_name = f"JOBO-PHASE6-MODE-{uuid.uuid4().hex[:8]}"
SAFE_OUTPUT = re.compile(r"^[A-Za-z0-9._-]+$")
SAFE_MODE = re.compile(r"^\d+x\d+@\d+(?:\.\d+)?$")


def run(command: list[str], *, timeout: int = 30, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    if check and proc.returncode != 0:
        raise AssertionError(
            f"{command} failed ({proc.returncode})\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return proc


def monitors() -> list[dict]:
    return json.loads(run(["hyprctl", "-j", "monitors", "all"]).stdout)


def monitor(name: str) -> dict | None:
    return next((item for item in monitors() if item.get("name") == name), None)


def wait_monitor(name: str, predicate, timeout: float = 10) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        current = monitor(name)
        if current and predicate(current):
            return current
        time.sleep(0.1)
    raise AssertionError(f"monitor state did not settle for {name}")


def configure(item: dict, mode: str, scale: float, transform: int) -> None:
    name = str(item["name"])
    if not SAFE_OUTPUT.fullmatch(name) or not SAFE_MODE.fullmatch(mode):
        raise AssertionError(f"unsafe monitor configuration value: {name} {mode}")
    x, y = int(item["x"]), int(item["y"])
    expression = (
        "hl.monitor({"
        f'output = "{name}", mode = "{mode}", position = "{x}x{y}", '
        f"scale = {float(scale)}, transform = {int(transform)}"
        "})"
    )
    run(["hyprctl", "eval", expression])


def status() -> dict:
    return json.loads(run(["omarchy-shell", "jobo-desktop-ambience", "status"]).stdout)


originals = [item for item in monitors() if not item.get("disabled")]
physical_target = None
alternate_mode = ""
for candidate in sorted(originals, key=lambda item: bool(item.get("focused"))):
    name = str(candidate.get("name", ""))
    if name.startswith("JOBO-") or not SAFE_OUTPUT.fullmatch(name):
        continue
    prefix = f'{int(candidate["width"])}x{int(candidate["height"])}@'
    alternatives = [mode for mode in candidate.get("availableModes", []) if mode.startswith(prefix)]
    alternatives = [mode.replace("Hz", "") for mode in alternatives]
    alternatives = [mode for mode in alternatives if SAFE_MODE.fullmatch(mode)]
    alternatives = [mode for mode in alternatives
                    if abs(float(mode.split("@", 1)[1]) - float(candidate["refreshRate"])) > 1]
    if alternatives:
        physical_target = candidate
        alternate_mode = alternatives[0]
        break
if not physical_target:
    raise SystemExit("no non-destructive alternate refresh mode is advertised")

original_mode = (
    f'{int(physical_target["width"])}x{int(physical_target["height"])}'
    f'@{float(physical_target["refreshRate"]):.2f}'
)
refresh_observed = None
headless_observed = None
try:
    run(["hyprctl", "output", "create", "headless", headless_name])
    headless = wait_monitor(headless_name, lambda value: True)
    configure(headless, "1920x1080@60", 1.25, 1)
    headless_observed = wait_monitor(
        headless_name,
        lambda value: abs(float(value.get("scale", 0)) - 1.25) < 0.01
        and int(value.get("transform", -1)) == 1,
    )
    headless_status = status()
    if headless_status["surfaceCount"] != headless_status["expectedSurfaceCount"]:
        raise AssertionError(headless_status)

    configure(
        physical_target,
        alternate_mode,
        float(physical_target["scale"]),
        int(physical_target["transform"]),
    )
    expected_refresh = float(alternate_mode.split("@", 1)[1])
    refresh_observed = wait_monitor(
        str(physical_target["name"]),
        lambda value: abs(float(value.get("refreshRate", 0)) - expected_refresh) < 1,
    )
    refresh_status = status()
    if refresh_status["surfaceCount"] != refresh_status["expectedSurfaceCount"]:
        raise AssertionError(refresh_status)
finally:
    try:
        configure(
            physical_target,
            original_mode,
            float(physical_target["scale"]),
            int(physical_target["transform"]),
        )
        wait_monitor(
            str(physical_target["name"]),
            lambda value: abs(float(value.get("refreshRate", 0))
                              - float(physical_target["refreshRate"])) < 0.5,
        )
    finally:
        run(["hyprctl", "output", "remove", headless_name], check=False)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and monitor(headless_name):
            time.sleep(0.1)

if not refresh_observed or not headless_observed:
    raise AssertionError("output-mode evidence was not captured")

evidence = {
    "schemaVersion": 1,
    "persistentHyprlandConfigModified": False,
    "fractionalScaleAndRotation": {
        "temporaryOutput": headless_name,
        "scale": headless_observed["scale"],
        "transform": headless_observed["transform"],
        "surfaceCreated": True,
    },
    "mixedRefreshRate": {
        "output": physical_target["name"],
        "originalHz": physical_target["refreshRate"],
        "testedHz": refresh_observed["refreshRate"],
        "restored": True,
        "surfaceCountStable": True,
    },
}
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
(ARTIFACT_DIR / "output-modes.json").write_text(
    json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps(evidence, indent=2))
