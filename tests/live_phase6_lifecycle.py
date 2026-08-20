#!/usr/bin/env python3
"""Opt-in Phase 6 lifecycle and installed-hardware evidence.

This check is read-only with respect to live plugin settings. It verifies the
installed checkout, plugin rescan, shell restart, layer/surface cardinality,
clean-clone validation, and reversible headless-output hotplug.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path


if os.environ.get("JOBO_AMBIENCE_LIVE_PHASE6") != "1":
    raise SystemExit("set JOBO_AMBIENCE_LIVE_PHASE6=1 to run the Phase 6 lifecycle check")

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ID = "jobo.desktop-ambience"
VERSION = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))["version"]
ARTIFACT_DIR = ROOT / "docs/release/evidence" / VERSION
for tool in ("git", "hyprctl", "omarchy", "omarchy-shell"):
    if not shutil.which(tool):
        raise SystemExit(f"missing required tool: {tool}")


def run(
    command: list[str], *, timeout: int = 60, env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout, env=env)
    if proc.returncode != 0:
        raise AssertionError(
            f"{command} failed ({proc.returncode})\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return proc


def run_when_shell_ready(command: list[str], timeout: float = 20) -> subprocess.CompletedProcess[str]:
    deadline = time.monotonic() + timeout
    last: subprocess.CompletedProcess[str] | None = None
    while time.monotonic() < deadline:
        last = subprocess.run(command, capture_output=True, text=True, timeout=10)
        if last.returncode == 0:
            return last
        if "not responding" not in (last.stdout + last.stderr).lower():
            break
        time.sleep(0.15)
    raise AssertionError(
        f"{command} did not become ready\nstdout:\n{last.stdout if last else ''}"
        f"\nstderr:\n{last.stderr if last else ''}"
    )


def status() -> dict:
    return json.loads(run_when_shell_ready(
        ["omarchy-shell", "jobo-desktop-ambience", "status"]
    ).stdout)


def wait_for_status(timeout: float = 20) -> dict:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            value = status()
            if value.get("surfaceCount") == value.get("expectedSurfaceCount"):
                return value
        except Exception as error:  # IPC is briefly absent during restart.
            last_error = error
        time.sleep(0.15)
    raise AssertionError(f"plugin status did not settle: {last_error}")


def sha256_if_present(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "missing"


def layer_names() -> dict[str, list[str]]:
    payload = json.loads(run(["hyprctl", "-j", "layers"]).stdout)
    result: dict[str, list[str]] = {}
    for output, data in payload.items():
        names = []
        for entries in data.get("levels", {}).values():
            for entry in entries:
                if entry.get("namespace") == "jobo-desktop-ambience":
                    names.append(str(entry.get("namespace")))
        result[output] = names
    return result


manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
settings_path = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) \
    / "omarchy/jobo/desktop-ambience/settings.json"
shell_config = Path.home() / ".config/omarchy/shell.json"
settings_before = sha256_if_present(settings_path)
shell_config_before = sha256_if_present(shell_config)

installed = Path.home() / ".config/omarchy/plugins" / PLUGIN_ID
if not installed.is_dir():
    raise AssertionError(f"installed checkout missing: {installed}")
if run(["git", "-C", str(installed), "rev-parse", "HEAD"]).stdout.strip() \
        != run(["git", "rev-parse", "HEAD"]).stdout.strip():
    raise AssertionError("installed checkout does not match the release candidate")
run(["omarchy", "plugin", "validate", str(installed)])

initial = wait_for_status()
if initial.get("version") != manifest["version"]:
    raise AssertionError(initial)
if len({surface["output"] for surface in initial["surfaces"]}) != initial["surfaceCount"]:
    raise AssertionError("duplicate output surfaces detected")

initial_layers = layer_names()
for output in (surface["output"] for surface in initial["surfaces"]):
    if len(initial_layers.get(output, [])) != 1:
        raise AssertionError(f"expected one ambience layer on {output}: {initial_layers}")

run_when_shell_ready(["omarchy-shell", "shell", "rescanPlugins"])
rescanned = wait_for_status()

run(["omarchy", "restart", "shell"], timeout=90)
restarted = wait_for_status()
restarted_layers = layer_names()
for output in (surface["output"] for surface in restarted["surfaces"]):
    if len(restarted_layers.get(output, [])) != 1:
        raise AssertionError(f"restart left incorrect layer count on {output}: {restarted_layers}")

with tempfile.TemporaryDirectory() as directory:
    clone = Path(directory) / PLUGIN_ID
    run(["git", "clone", "--quiet", "--no-hardlinks", str(ROOT), str(clone)])
    run(["omarchy", "plugin", "validate", str(clone)])
    clean_clone_head = run(["git", "-C", str(clone), "rev-parse", "HEAD"]).stdout.strip()

hotplug_env = os.environ.copy()
hotplug_env["JOBO_AMBIENCE_LIVE_HOTPLUG"] = "1"
hotplug_proc = run(
    ["python", "tests/live_phase3_hotplug.py"], timeout=45, env=hotplug_env,
)
hotplug = json.loads(hotplug_proc.stdout)

final = wait_for_status()
if sha256_if_present(settings_path) != settings_before:
    raise AssertionError("live plugin settings changed during lifecycle validation")
if sha256_if_present(shell_config) != shell_config_before:
    raise AssertionError("shell configuration changed during lifecycle validation")

monitor_payload = json.loads(run(["hyprctl", "-j", "monitors", "all"]).stdout)
monitors = [
    {
        "name": item.get("name"),
        "width": item.get("width"),
        "height": item.get("height"),
        "refreshRate": item.get("refreshRate"),
        "scale": item.get("scale"),
        "transform": item.get("transform"),
    }
    for item in monitor_payload
    if not item.get("disabled")
]

hardware_coverage = {
    "outputCount": len(monitors),
    "multipleOutputs": len(monitors) > 1,
    "mixedResolution": len({(item["width"], item["height"]) for item in monitors}) > 1,
    "mixedScale": len({item["scale"] for item in monitors}) > 1,
    "mixedOrientation": len({item["transform"] for item in monitors}) > 1,
    "mixedRefreshRate": len({round(float(item["refreshRate"]), 2) for item in monitors}) > 1,
}

evidence = {
    "schemaVersion": 1,
    "pluginVersion": manifest["version"],
    "repositoryHead": run(["git", "rev-parse", "HEAD"]).stdout.strip(),
    "cleanCloneHead": clean_clone_head,
    "liveSettingsModified": False,
    "shellConfigModified": False,
    "monitors": monitors,
    "hardwareCoverage": hardware_coverage,
    "initial": {
        "surfaceCount": initial["surfaceCount"],
        "mappedSurfaceCount": initial["mappedSurfaceCount"],
        "mode": initial["mode"],
    },
    "pluginRescan": {
        "surfaceCount": rescanned["surfaceCount"],
        "mappedSurfaceCount": rescanned["mappedSurfaceCount"],
    },
    "shellRestart": {
        "surfaceCount": restarted["surfaceCount"],
        "mappedSurfaceCount": restarted["mappedSurfaceCount"],
        "oneLayerPerOutput": True,
    },
    "headlessHotplug": hotplug,
    "final": {
        "surfaceCount": final["surfaceCount"],
        "mappedSurfaceCount": final["mappedSurfaceCount"],
    },
}
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
(ARTIFACT_DIR / "lifecycle-hardware.json").write_text(
    json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps(evidence, indent=2))
