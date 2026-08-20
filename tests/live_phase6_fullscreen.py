#!/usr/bin/env python3
"""Opt-in real Hyprland fullscreen matrix on a temporary headless output.

The test runs an isolated foreground-mode Panel with temporary XDG homes beside
the installed plugin, creates one disposable test window, and verifies normal,
client-only (fake), and real fullscreen suppression. Live settings are untouched.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

from qml_harness import qml_url, require_no_qml_errors


if os.environ.get("JOBO_AMBIENCE_LIVE_PHASE6") != "1":
    raise SystemExit("set JOBO_AMBIENCE_LIVE_PHASE6=1 to run the Phase 6 fullscreen check")
if not os.environ.get("WAYLAND_DISPLAY"):
    raise SystemExit("an active Wayland session is required")
for tool in ("quickshell", "hyprctl"):
    if not shutil.which(tool):
        raise SystemExit(f"missing required tool: {tool}")

ROOT = Path(__file__).resolve().parents[1]
VERSION = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))["version"]
output_name = f"JOBO-PHASE6-FS-{uuid.uuid4().hex[:8]}"
window_title = f"jobo-phase6-fullscreen-{uuid.uuid4().hex[:8]}"


def run(command: list[str], *, timeout: int = 30, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    if check and proc.returncode != 0:
        raise AssertionError(
            f"{command} failed ({proc.returncode})\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
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


def matching_client() -> dict | None:
    matches = [
        client for client in json.loads(run(["hyprctl", "-j", "clients"]).stdout)
        if str(client.get("title")) == window_title
    ]
    if len(matches) > 1:
        raise AssertionError(f"expected at most one test client, found {len(matches)}")
    return matches[0] if matches else None


def wait_for_client(timeout: float = 10) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        client = matching_client()
        if client:
            return client
        time.sleep(0.1)
    raise AssertionError("test client did not appear")


def validated_selector(address: str) -> str:
    if not address.startswith("0x") or any(char not in "0123456789abcdefABCDEF" for char in address[2:]):
        raise AssertionError(f"invalid compositor address: {address}")
    return f"address:{address}"


def move_to_output(address: str) -> dict:
    selector = validated_selector(address)
    output = next((item for item in monitors() if item.get("name") == output_name), None)
    if not output:
        raise AssertionError(f"headless output disappeared: {output_name}")
    expression = (
        'hl.dsp.window.move({'
        f'monitor = "{output_name}", follow = false, window = "{selector}"'
        '})'
    )
    run(["hyprctl", "dispatch", expression])
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        current = matching_client()
        if current and int(current.get("monitor", -1)) == int(output["id"]):
            return current
        time.sleep(0.1)
    raise AssertionError(f"test client did not move to {output_name}")


def set_fullscreen_state(address: str, internal: int, client: int) -> dict:
    selector = validated_selector(address)
    expression = (
        'hl.dsp.window.fullscreen_state({'
        f'internal = {internal}, client = {client}, action = "set", '
        f'window = "{selector}"'
        '})'
    )
    run(["hyprctl", "dispatch", expression])
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        current = matching_client()
        if current and int(current.get("fullscreen", -1)) == internal \
                and int(current.get("fullscreenClient", -1)) == client:
            return current
        time.sleep(0.1)
    raise AssertionError(f"fullscreen state did not settle: internal={internal} client={client}")


def qml_source() -> str:
    return f'''
import Quickshell
import QtQuick
import QtQuick.Window

ShellRoot {{
  id: root
  property var renderScreen: null
  property var windowScreen: null
  property bool lastSuppressed: false
  property bool reportedInitial: false
  property bool sawSuppressed: false
  property bool requestedBackground: false
  property bool backgroundReported: false
  property var bokehIdentity: null
  property var nodeMeshIdentity: null
  property var precipitationIdentity: null

  function findScreen() {{
    for (var i = 0; i < Quickshell.screens.length; i++)
      if (String(Quickshell.screens[i].name) === "{output_name}") return Quickshell.screens[i]
    return null
  }}

  function findWindowScreen() {{
    for (var i = 0; i < Qt.application.screens.length; i++)
      if (String(Qt.application.screens[i].name) === "{output_name}") return Qt.application.screens[i]
    return null
  }}

  function testSurface() {{
    var panel = panelLoader.item
    if (!panel) return null
    for (var i = 0; i < panel.productionSurfaces.length; i++) {{
      var surface = panel.surfaceAt(i)
      if (surface && surface.outputName === "{output_name}") return surface
    }}
    return null
  }}

  Component.onCompleted: screenProbe.start()

  Loader {{
    id: panelLoader
    source: "{qml_url('Panel.qml')}"
  }}

  Timer {{
    id: screenProbe
    interval: 50
    repeat: true
    property int attempts: 0
    onTriggered: {{
      attempts += 1
      root.renderScreen = root.findScreen()
      root.windowScreen = root.findWindowScreen()
      if (root.renderScreen && root.windowScreen
          && panelLoader.item && panelLoader.item.settingsService.hasLoaded) {{
        testWindow.visible = true
        stateProbe.start()
        stop()
      }} else if (attempts > 200) {{ console.log("BEHAVE_ERR fullscreen harness did not initialize"); Qt.quit() }}
    }}
  }}

  Window {{
    id: testWindow
    screen: root.windowScreen
    width: 800
    height: 450
    visible: false
    title: "{window_title}"
    color: "#20242a"
  }}

  Timer {{
    id: stateProbe
    interval: 80
    repeat: true
    onTriggered: {{
      var surface = root.testSurface()
      if (!surface) return
      var bokeh = surface.stackObject
        ? surface.stackObject.productionEffectObject("bokeh") : null
      var nodeMesh = surface.stackObject
        ? surface.stackObject.productionEffectObject("nodeMesh") : null
      var precipitation = surface.stackObject
        ? surface.stackObject.productionEffectObject("rainfall") : null
      if (!bokeh || !nodeMesh || !precipitation) return
      panelLoader.item.fullscreenService.refresh()
      var suppressed = surface.fullscreenSuppressed === true
      if (!root.reportedInitial && !suppressed && !bokeh.effectVisible) return
      if (!root.bokehIdentity) root.bokehIdentity = bokeh
      if (!root.nodeMeshIdentity) root.nodeMeshIdentity = nodeMesh
      if (!root.precipitationIdentity) root.precipitationIdentity = precipitation
      var backgroundReady = root.requestedBackground && !root.backgroundReported
        && panelLoader.item.presentation === "background" && surface.layerName === "bottom"
      if (!root.reportedInitial || suppressed !== root.lastSuppressed || backgroundReady) {{
        root.reportedInitial = true
        root.lastSuppressed = suppressed
        if (suppressed) root.sawSuppressed = true
        if (backgroundReady) root.backgroundReported = true
        console.log("BEHAVE " + JSON.stringify({{
          output: surface.outputName,
          suppressed: suppressed,
          mapped: surface.visible,
          paintAllowed: surface.paintAllowed,
          presentation: panelLoader.item.presentation,
          layerName: surface.layerName,
          bokehLoaded: bokeh !== null,
          sameBokehObject: root.bokehIdentity === bokeh,
          bokehVisible: bokeh.effectVisible,
          bokehAnimationsRunning: bokeh.animationRunning,
          nodeMeshLoaded: nodeMesh !== null,
          sameNodeMeshObject: root.nodeMeshIdentity === nodeMesh,
          nodeMeshVisible: nodeMesh.effectVisible,
          nodeMeshSimulationRunning: nodeMesh.simulationRunning,
          nodeMeshUpdateCount: nodeMesh.simulationUpdateCount,
          precipitationLoaded: precipitation !== null,
          samePrecipitationObject: root.precipitationIdentity === precipitation,
          precipitationStyle: precipitation.selectedStyle,
          precipitationVisible: precipitation.effectVisible,
          precipitationMotionRunning: precipitation.autonomousMotionRunning,
          precipitationRunningClockCount: precipitation.runningClockCount,
          precipitationClockUpdateCount: precipitation.snowClockUpdateCount
        }}))
      }}
      if (root.sawSuppressed && !suppressed && !root.requestedBackground) {{
        root.requestedBackground = true
        var next = panelLoader.item.settingsService.normalize(panelLoader.item.settingsService.data)
        next.presentation = "background"
        panelLoader.item.settingsService.save(next)
      }}
    }}
  }}
}}
'''


proc: subprocess.Popen[str] | None = None
address = ""
try:
    run(["hyprctl", "output", "create", "headless", output_name])
    wait_for_output(True)

    with tempfile.TemporaryDirectory() as shell_dir, tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as state_dir:
        config_home = Path(config_dir)
        settings_file = config_home / "omarchy/jobo/desktop-ambience/settings.json"
        settings_file.parent.mkdir(parents=True)
        settings_file.write_text(json.dumps({
            "version": 1,
            "enabled": True,
            "presentation": "foreground",
            "opacity": 1,
            "reduceMotion": False,
            "activeEffects": ["bokeh", "nodeMesh", "rainfall"],
            "effects": {
                "bokeh": {"enabled": True, "intensity": 0.52},
                "nodeMesh": {"enabled": True, "intensity": 0.48, "pointerMode": "off"},
                "rainfall": {"enabled": True, "intensity": 0.72,
                             "precipitationStyle": "snow", "dropCount": 180},
            },
            "backgroundVignette": {"enabled": False, "intensity": 0},
        }), encoding="utf-8")
        palette = Path(state_dir) / "omarchy/current/theme/colors.toml"
        palette.parent.mkdir(parents=True)
        palette.write_text('color11 = "#aabbcc"\n', encoding="utf-8")

        shell_root = Path(shell_dir)
        shell_file = shell_root / "shell.qml"
        shell_file.write_text(qml_source(), encoding="utf-8")
        omarchy_shell = Path(os.environ.get("OMARCHY_PATH", "/usr/share/omarchy")) / "shell"
        for module in ("Commons", "Ui"):
            (shell_root / module).symlink_to(omarchy_shell / module, target_is_directory=True)

        env = os.environ.copy()
        env.update({
            "QT_QPA_PLATFORM": "wayland",
            "XDG_CONFIG_HOME": str(config_home),
            "XDG_STATE_HOME": state_dir,
        })
        proc = subprocess.Popen(
            [shutil.which("quickshell") or "quickshell", "-p", str(shell_file)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        test_client = wait_for_client()
        address = str(test_client["address"])
        test_client = move_to_output(address)

        normal = set_fullscreen_state(address, 0, 0)
        time.sleep(0.5)
        fake = set_fullscreen_state(address, 0, 2)
        time.sleep(0.7)
        real = set_fullscreen_state(address, 2, 2)
        time.sleep(0.7)
        restored = set_fullscreen_state(address, 0, 0)
        time.sleep(1.2)

        proc.terminate()
        stdout, _ = proc.communicate(timeout=10)
        proc = None

    require_no_qml_errors(stdout)
    states = []
    for line in stdout.splitlines():
        marker = line.find("BEHAVE ")
        if marker >= 0:
            states.append(json.loads(line[marker + len("BEHAVE "):].strip()))
    suppression = [state["suppressed"] for state in states]
    if not suppression or suppression[0] is not False or True not in suppression or suppression[-1] is not False:
        raise AssertionError(
            f"unexpected suppression sequence {suppression}\n"
            f"normal={normal}\nfake={fake}\nreal={real}\nrestored={restored}\n"
            f"monitors={monitors()}\n{stdout[-4000:]}"
        )
    if any(state["mapped"] is not True for state in states):
        raise AssertionError(states)
    if any(state["bokehLoaded"] is not True or state["sameBokehObject"] is not True for state in states):
        raise AssertionError(states)
    if any(state["nodeMeshLoaded"] is not True or state["sameNodeMeshObject"] is not True for state in states):
        raise AssertionError(states)
    if any(state["precipitationLoaded"] is not True
           or state["samePrecipitationObject"] is not True
           or state["precipitationStyle"] != "snow" for state in states):
        raise AssertionError(states)
    if not any(state["presentation"] == "foreground" and state["layerName"] == "overlay" for state in states):
        raise AssertionError(states)
    if not any(state["presentation"] == "background" and state["layerName"] == "bottom" for state in states):
        raise AssertionError(states)
    if states[0]["bokehVisible"] is not True or states[-1]["bokehVisible"] is not True:
        raise AssertionError(states)
    if not any(state["suppressed"] and state["bokehVisible"] is False for state in states):
        raise AssertionError(states)
    if states[0]["nodeMeshVisible"] is not True or states[-1]["nodeMeshVisible"] is not True:
        raise AssertionError(states)
    if not any(state["suppressed"] and state["nodeMeshVisible"] is False
               and state["nodeMeshSimulationRunning"] is False for state in states):
        raise AssertionError(states)
    if not any(not state["suppressed"] and state["nodeMeshSimulationRunning"] is True
               and state["nodeMeshUpdateCount"] > 0 for state in states):
        raise AssertionError(states)
    if not any(not state["suppressed"] and state["bokehAnimationsRunning"] is True for state in states):
        raise AssertionError(states)
    if any(state["suppressed"] and state["bokehAnimationsRunning"] is not False for state in states):
        raise AssertionError(states)
    if states[0]["precipitationVisible"] is not True or states[-1]["precipitationVisible"] is not True:
        raise AssertionError(states)
    if not any(state["suppressed"] and state["precipitationVisible"] is False
               and state["precipitationMotionRunning"] is False
               and state["precipitationRunningClockCount"] == 0 for state in states):
        raise AssertionError(states)
    if not any(not state["suppressed"] and state["precipitationMotionRunning"] is True
               and state["precipitationRunningClockCount"] == 1
               and state["precipitationClockUpdateCount"] > 0 for state in states):
        raise AssertionError(states)

    evidence = {
        "schemaVersion": 1,
        "output": output_name,
        "liveSettingsModified": False,
        "coexistsWithInstalledPlugin": True,
        "clientStates": {
            "normal": {"internal": normal["fullscreen"], "client": normal["fullscreenClient"]},
            "fakeFullscreen": {"internal": fake["fullscreen"], "client": fake["fullscreenClient"]},
            "realFullscreen": {"internal": real["fullscreen"], "client": real["fullscreenClient"]},
            "restored": {"internal": restored["fullscreen"], "client": restored["fullscreenClient"]},
        },
        "suppressionSequence": suppression,
        "surfaceRemainedMapped": True,
        "presentationModes": ["foreground", "background"],
        "activeEffects": ["bokeh", "nodeMesh", "rainfall"],
        "bokehLoadedThroughout": True,
        "bokehIdentityPreservedAcrossPresentation": True,
        "bokehAnimatedWhilePaintable": True,
        "bokehStoppedWhileSuppressed": True,
        "nodeMeshLoadedThroughout": True,
        "nodeMeshIdentityPreservedAcrossPresentation": True,
        "nodeMeshAnimatedWhilePaintable": True,
        "nodeMeshStoppedWhileSuppressed": True,
        "precipitationStyle": "snow",
        "precipitationLoadedThroughout": True,
        "precipitationIdentityPreservedAcrossPresentation": True,
        "precipitationAnimatedWhilePaintable": True,
        "precipitationStoppedWhileSuppressed": True,
    }
    evidence_path = Path(os.environ.get(
        "JOBO_AMBIENCE_FULLSCREEN_EVIDENCE",
        ROOT / "docs/release/evidence" / VERSION / "fullscreen.json",
    )).resolve()
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2))
finally:
    if address:
        try:
            set_fullscreen_state(address, 0, 0)
        except Exception:
            pass
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    run(["hyprctl", "output", "remove", output_name], check=False)
    try:
        wait_for_output(False, timeout=5)
    except Exception:
        pass
