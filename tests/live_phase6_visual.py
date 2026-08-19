#!/usr/bin/env python3
"""Opt-in isolated visual and frame-cadence evidence for Phase 6.

Creates a temporary headless Hyprland output, renders every production effect
with temporary XDG homes, records screenshots and QML frame callback timing,
and removes the output in a finally block. It never reads or writes live plugin
settings.
"""

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


if os.environ.get("JOBO_AMBIENCE_LIVE_PHASE6") != "1":
    raise SystemExit("set JOBO_AMBIENCE_LIVE_PHASE6=1 to run the isolated Phase 6 visual check")

ROOT = Path(__file__).resolve().parents[1]
VERSION = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))["version"]
ARTIFACT_DIR = Path(
    os.environ.get(
        "JOBO_AMBIENCE_PHASE6_ARTIFACTS",
        ROOT / "docs/release/evidence" / VERSION,
    )
).resolve()
TOOLS = ("quickshell", "hyprctl", "magick", "ps")
missing = [tool for tool in TOOLS if not shutil.which(tool)]
if missing:
    raise SystemExit(f"missing required tools: {', '.join(missing)}")
if not os.environ.get("WAYLAND_DISPLAY"):
    raise SystemExit("an active Wayland session is required")

output_name = f"JOBO-PHASE6-{uuid.uuid4().hex[:8]}"
window_title = f"jobo-phase6-visual-{uuid.uuid4().hex[:8]}"
CASES = [
    ("auroraDrift", "effects/AuroraDriftEffect.qml"),
    ("cinematicLight", "effects/CinematicLightEffect.qml"),
    ("crt", "effects/CrtEffect.qml"),
    ("dustMotes", "effects/DustMotesEffect.qml"),
    ("filmGrain", "effects/FilmGrainEffect.qml"),
    ("godRays", "effects/GodRaysEffect.qml"),
    ("rainfall", "effects/RainfallEffect.qml"),
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


def wait_for_output(present: bool, timeout: float = 8) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        monitors = json.loads(run(["hyprctl", "-j", "monitors", "all"]).stdout)
        found = any(str(monitor.get("name")) == output_name for monitor in monitors)
        if found is present:
            return
        time.sleep(0.1)
    raise AssertionError(f"headless output {output_name} present={present} did not settle")


def make_qml() -> str:
    cases = json.dumps(
        [
            {
                "id": case_id,
                "source": qml_url(source),
                "file": str(ARTIFACT_DIR / f"{case_id}.png"),
            }
            for case_id, source in CASES
        ]
    )
    return f'''
import Quickshell
import QtQuick
import QtQuick.Window
import "{qml_url('services/EffectRegistry.js')}" as EffectRegistry

ShellRoot {{
  id: root
  property var renderScreen: null
  property var windowScreen: null
  property var cases: {cases}
  property int caseIndex: -1
  property bool stackMeasuring: false
  property bool capturePending: false
  property bool themeSwitchPending: false
  property double frameStartedAt: 0
  property int frameCount: 0
  property real frameTotalMs: 0
  property real frameMaxMs: 0
  property int framesOverBudget: 0

  QtObject {{
    id: state
    property real opacity: 1
    property bool reduceMotion: false
    property var effects: ({{}})
  }}

  QtObject {{
    id: theme
    property bool alternate: false
    function colorFor(name, fallback) {{
      var colors = alternate ? {{
        background: "#17120f", foreground: "#f0ddc5", accent: "#e06c75",
        color5: "#c678dd", color11: "#e5c07b", color12: "#61afef",
        color13: "#c678dd", color14: "#56b6c2", color15: "#f5e6d3"
      }} : {{
        background: "#101315", foreground: "#d8dee9", accent: "#88c0d0",
        color5: "#b48ead", color11: "#ebcb8b", color12: "#81a1c1",
        color13: "#b48ead", color14: "#8fbcbb", color15: "#eceff4"
      }}
      return colors[name] || fallback
    }}
  }}

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

  function configure(item, caseId) {{
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
      state.reduceMotion = false
      item.settings = state
      item.theme = theme
      item.activeEffects = ["auroraDrift", "rainfall", "filmGrain"]
      item.productionEffectsEnabled = true
      item.paintEnabled = true
    }} else {{
      var settings = EffectRegistry.defaultsFor(caseId)
      if (caseId === "dustMotes") settings.mouseReactive = false
      item.effectSettings = settings
      item.globalOpacity = 1
      item.reducedMotion = true
      if ("theme" in item) item.theme = theme
    }}
    if ("targetScreen" in item) item.targetScreen = root.renderScreen
  }}

  function nextCase() {{
    caseIndex += 1
    if (caseIndex >= cases.length) {{
      console.log("BEHAVE " + JSON.stringify({{
        output: "{output_name}", cases: cases.length,
        frameCount: frameCount,
        meanFrameMs: frameCount > 0 ? frameTotalMs / frameCount : 0,
        maxFrameMs: frameMaxMs,
        framesOverBudget: framesOverBudget
      }}))
      Qt.quit()
      return
    }}
    stackMeasuring = false
    capturePending = false
    themeSwitchPending = false
    theme.alternate = false
    effectLoader.source = ""
    Qt.callLater(function() {{ effectLoader.source = cases[caseIndex].source }})
  }}

  function captureCurrent() {{
    if (capturePending || !effectLoader.item) return
    capturePending = true
    effectLoader.item.grabToImage(function(result) {{
      var stackCase = cases[caseIndex].id === "threeEffectStack"
      var outputFile = stackCase && root.themeSwitchPending
        ? "{str((ARTIFACT_DIR / 'threeEffectStackThemeSwitch.png').resolve())}"
        : cases[caseIndex].file
      var saved = result.saveToFile(outputFile)
      if (!saved) console.log("BEHAVE_ERR failed to save " + outputFile)
      if (stackCase && !root.themeSwitchPending) {{
        root.capturePending = false
        root.themeSwitchPending = true
        theme.alternate = true
        themeSettle.start()
      }} else root.nextCase()
    }})
  }}

  Component.onCompleted: screenProbe.start()

  Timer {{
    id: screenProbe
    interval: 50
    repeat: true
    property int attempts: 0
    onTriggered: {{
      attempts += 1
      root.renderScreen = root.findScreen()
      root.windowScreen = root.findWindowScreen()
      if (root.renderScreen && root.windowScreen) {{ stop(); renderWindow.visible = true; startDelay.start() }}
      else if (attempts > 160) {{ console.log("BEHAVE_ERR headless screen missing"); Qt.quit() }}
    }}
  }}

  Timer {{ id: startDelay; interval: 1200; onTriggered: root.nextCase() }}

  Window {{
    id: renderWindow
    screen: root.windowScreen
    visibility: Window.FullScreen
    visible: false
    title: "{window_title}"
    color: "#101315"

    Loader {{
      id: effectLoader
      anchors.fill: parent
      onLoaded: {{
        root.configure(item, root.cases[root.caseIndex].id)
        settle.restart()
      }}
    }}

    Timer {{ id: themeSettle; interval: 650; onTriggered: root.captureCurrent() }}

    Timer {{
      id: settle
      interval: 650
      onTriggered: {{
        if (root.cases[root.caseIndex].id === "threeEffectStack") {{
          root.frameCount = 0
          root.frameTotalMs = 0
          root.frameMaxMs = 0
          root.framesOverBudget = 0
          root.frameStartedAt = Date.now()
          root.stackMeasuring = true
        }} else root.captureCurrent()
      }}
    }}

    FrameAnimation {{
      running: root.stackMeasuring
      onTriggered: {{
        var milliseconds = frameTime * 1000
        if (milliseconds > 0 && milliseconds < 1000) {{
          root.frameCount += 1
          root.frameTotalMs += milliseconds
          root.frameMaxMs = Math.max(root.frameMaxMs, milliseconds)
          if (milliseconds > 20) root.framesOverBudget += 1
        }}
        if (Date.now() - root.frameStartedAt >= 4000) {{
          root.stackMeasuring = false
          root.captureCurrent()
        }}
      }}
    }}
  }}
}}
'''


def place_render_window() -> None:
    output = next((item for item in json.loads(run(["hyprctl", "-j", "monitors", "all"]).stdout)
                   if item.get("name") == output_name), None)
    if not output:
        raise AssertionError(f"headless output disappeared: {output_name}")
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
            if not address.startswith("0x") or any(char not in "0123456789abcdefABCDEF" for char in address[2:]):
                raise AssertionError(f"invalid compositor address: {address}")
            selector = f"address:{address}"
            expression = (
                'hl.dsp.window.move({'
                f'monitor = "{output_name}", follow = false, window = "{selector}"'
                '})'
            )
            run(["hyprctl", "dispatch", expression])
            move_deadline = time.monotonic() + 5
            while time.monotonic() < move_deadline:
                current = next((client for client in json.loads(run(["hyprctl", "-j", "clients"]).stdout)
                                if str(client.get("title")) == window_title), None)
                if current and int(current.get("monitor", -1)) == int(output["id"]):
                    return
                time.sleep(0.1)
            raise AssertionError(f"render window did not move to {output_name}")
        time.sleep(0.1)
    raise AssertionError("render window did not appear")


def process_cpu_ticks(pid: int) -> int:
    fields = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").split()
    return int(fields[13]) + int(fields[14])


def image_metrics(path: Path) -> dict[str, object]:
    proc = run(
        [
            "magick", str(path), "-format",
            "%w %h %[fx:mean] %[fx:standard_deviation] %[entropy]", "info:",
        ]
    )
    width, height, mean, deviation, entropy = proc.stdout.strip().split()
    return {
        "file": path.name,
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "width": int(width),
        "height": int(height),
        "mean": float(mean),
        "standardDeviation": float(deviation),
        "entropy": float(entropy),
    }


ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
for old in ARTIFACT_DIR.glob("*.png"):
    old.unlink()

try:
    run(["hyprctl", "output", "create", "headless", output_name])
    wait_for_output(True)

    with tempfile.TemporaryDirectory() as shell_dir, tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as state_dir:
        shell_root = Path(shell_dir)
        shell_file = shell_root / "shell.qml"
        shell_file.write_text(make_qml(), encoding="utf-8")
        omarchy_shell = Path(os.environ.get("OMARCHY_PATH", "/usr/share/omarchy")) / "shell"
        for module in ("Commons", "Ui"):
            (shell_root / module).symlink_to(omarchy_shell / module, target_is_directory=True)

        env = os.environ.copy()
        env.update({
            "QT_QPA_PLATFORM": "wayland",
            "XDG_CONFIG_HOME": config_dir,
            "XDG_STATE_HOME": state_dir,
        })
        started = time.monotonic()
        proc = subprocess.Popen(
            [shutil.which("quickshell") or "quickshell", "-p", str(shell_file)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        place_render_window()
        start_ticks = process_cpu_ticks(proc.pid)
        end_ticks = start_ticks
        peak_rss_kib = 0
        deadline = started + 45
        while proc.poll() is None and time.monotonic() < deadline:
            time.sleep(0.2)
            if Path(f"/proc/{proc.pid}/stat").exists():
                end_ticks = process_cpu_ticks(proc.pid)
                status = Path(f"/proc/{proc.pid}/status").read_text(encoding="utf-8")
                for line in status.splitlines():
                    if line.startswith("VmRSS:"):
                        peak_rss_kib = max(peak_rss_kib, int(line.split()[1]))
                        break
        if proc.poll() is None:
            proc.kill()
            stdout, _ = proc.communicate()
            raise AssertionError(f"visual harness timed out\n{stdout[-4000:]}")
        stdout, _ = proc.communicate()
        elapsed = time.monotonic() - started
        clock_ticks = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
        cpu_percent = ((end_ticks - start_ticks) / clock_ticks) / max(elapsed, 0.001) * 100

    require_no_qml_errors(stdout)
    rows = parse_behave(stdout)
    if not rows:
        raise AssertionError(f"visual harness produced no result\n{stdout[-4000:]}")
    runtime = rows[-1]
    if runtime["cases"] != len(CASES):
        raise AssertionError(runtime)
    if runtime["frameCount"] < 30 or runtime["meanFrameMs"] <= 0:
        raise AssertionError(runtime)

    images = []
    image_case_ids = [case_id for case_id, _ in CASES] + ["threeEffectStackThemeSwitch"]
    for case_id in image_case_ids:
        path = ARTIFACT_DIR / f"{case_id}.png"
        if not path.is_file() or path.stat().st_size < 1024:
            raise AssertionError(f"missing or empty visual artifact: {path}")
        metrics = image_metrics(path)
        if metrics["standardDeviation"] <= 0.001:
            raise AssertionError(f"flat visual artifact: {metrics}")
        images.append({"case": case_id, **metrics})

    stack_hash = next(image["sha256"] for image in images if image["case"] == "threeEffectStack")
    switched_hash = next(
        image["sha256"] for image in images if image["case"] == "threeEffectStackThemeSwitch"
    )
    if stack_hash == switched_hash:
        raise AssertionError("active stack pixels did not change after the theme switch")

    contact_sheet = ARTIFACT_DIR / "contact-sheet.webp"
    run([
        "magick", "montage",
        *[str(ARTIFACT_DIR / f"{case_id}.png") for case_id in image_case_ids],
        "-thumbnail", "360x203", "-tile", "3x4", "-geometry", "+8+24",
        "-background", "#111318", "-fill", "white", "-pointsize", "17",
        "-set", "label", "%t", str(contact_sheet),
    ], timeout=60)

    evidence = {
        "schemaVersion": 1,
        "pluginVersion": VERSION,
        "headlessOutput": output_name,
        "isolatedConfig": True,
        "liveSettingsModified": False,
        "renderCases": image_case_ids,
        "themeSwitchChangedPixels": stack_hash != switched_hash,
        "qmlFrameCadence": {
            "sampleFrames": runtime["frameCount"],
            "meanMs": runtime["meanFrameMs"],
            "maxMs": runtime["maxFrameMs"],
            "over20ms": runtime["framesOverBudget"],
        },
        "isolatedProcess": {
            "elapsedSeconds": elapsed,
            "averageCpuPercent": cpu_percent,
            "peakRssKiB": peak_rss_kib,
            "scope": "isolated Quickshell process rendering the release matrix; not the full desktop shell",
        },
        "contactSheet": contact_sheet.name,
        "images": images,
    }
    (ARTIFACT_DIR / "visual-performance.json").write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(evidence, indent=2))
finally:
    run(["hyprctl", "output", "remove", output_name], check=False)
    try:
        wait_for_output(False, timeout=5)
    except Exception:
        pass
