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
    ("rainExtractionParity", "effects/RainfallEffect.qml"),
    ("rainMistSplashMinimum", "effects/RainfallEffect.qml"),
    ("rainMistSplashMaximum", "effects/RainfallEffect.qml"),
    ("rainReducedMotion", "effects/RainfallEffect.qml"),
    ("snowMinimumPopulation", "effects/RainfallEffect.qml"),
    ("snowDefault", "effects/RainfallEffect.qml"),
    ("snowMaximumPopulation", "effects/RainfallEffect.qml"),
    ("snowMinimumSize", "effects/RainfallEffect.qml"),
    ("snowMaximumSize", "effects/RainfallEffect.qml"),
    ("snowLowFlutterNegativeSlant", "effects/RainfallEffect.qml"),
    ("snowHighFlutterPositiveSlant", "effects/RainfallEffect.qml"),
    ("snowSoft", "effects/RainfallEffect.qml"),
    ("snowCrystal", "effects/RainfallEffect.qml"),
    ("snowMixed", "effects/RainfallEffect.qml"),
    ("snowReducedMotion", "effects/RainfallEffect.qml"),
    ("rainBackground", "components/AmbienceStack.qml"),
    ("rainForeground", "components/AmbienceStack.qml"),
    ("snowBackground", "components/AmbienceStack.qml"),
    ("snowForeground", "components/AmbienceStack.qml"),
    ("tacticalGrid", "effects/TacticalGridEffect.qml"),
    ("trackingLines", "effects/VhsEffect.qml"),
    ("bokeh", "effects/BokehEffect.qml"),
    ("bokehMinimum", "effects/BokehEffect.qml"),
    ("bokehMaximum", "effects/BokehEffect.qml"),
    ("bokehSharp", "effects/BokehEffect.qml"),
    ("bokehSoft", "effects/BokehEffect.qml"),
    ("bokehNoDrift", "effects/BokehEffect.qml"),
    ("bokehTwinkleOff", "effects/BokehEffect.qml"),
    ("bokehContrastingRoles", "effects/BokehEffect.qml"),
    ("bokehReducedMotion", "effects/BokehEffect.qml"),
    ("nodeMesh", "effects/NodeMeshEffect.qml"),
    ("nodeMeshMinimum", "effects/NodeMeshEffect.qml"),
    ("nodeMeshMaximum", "effects/NodeMeshEffect.qml"),
    ("nodeMeshShortDistance", "effects/NodeMeshEffect.qml"),
    ("nodeMeshLongDistance", "effects/NodeMeshEffect.qml"),
    ("nodeMeshLowOpacity", "effects/NodeMeshEffect.qml"),
    ("nodeMeshHighOpacity", "effects/NodeMeshEffect.qml"),
    ("nodeMeshPointerOff", "effects/NodeMeshEffect.qml"),
    ("nodeMeshAttractCenter", "effects/NodeMeshEffect.qml"),
    ("nodeMeshAttractEdge", "effects/NodeMeshEffect.qml"),
    ("nodeMeshRepelCenter", "effects/NodeMeshEffect.qml"),
    ("nodeMeshRepelEdge", "effects/NodeMeshEffect.qml"),
    ("nodeMeshReducedMotion", "effects/NodeMeshEffect.qml"),
    ("nodeMeshBackground", "components/AmbienceStack.qml"),
    ("nodeMeshForeground", "components/AmbienceStack.qml"),
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
        monitors = json.loads(run(["hyprctl", "-j", "monitors", "all"]).stdout)
        monitor = next((item for item in monitors if str(item.get("name")) == output_name), None)
        if monitor and int(monitor.get("x", 0)) == -1920 and int(monitor.get("y", 0)) == -1080:
            return {key: monitor.get(key) for key in (
                "name", "x", "y", "width", "height", "scale", "transform"
            )}
        time.sleep(0.1)
    raise AssertionError("headless output geometry did not settle at its negative origin")


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
import Quickshell.Wayland
import QtQuick
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
  property bool edgeCursor: false

  QtObject {{
    id: state
    property real opacity: 1
    property bool reduceMotion: false
    property var effects: ({{}})
  }}

  QtObject {{
    id: tracker
    property real cursorX: root.renderScreen ? Number(root.renderScreen.x)
      + renderWindow.width * (root.edgeCursor ? 0.94 : 0.5) : -1
    property real cursorY: root.renderScreen ? Number(root.renderScreen.y)
      + renderWindow.height * (root.edgeCursor ? 0.08 : 0.5) : -1
    property real displayCursorX: cursorX
    property real displayCursorY: cursorY
    property bool hasCursorSample: root.renderScreen !== null
  }}

  QtObject {{
    id: theme
    property bool alternate: false
    function colorFor(name, fallback) {{
      var colors = alternate ? {{
        background: "#17120f", foreground: "#f0ddc5", accent: "#e06c75",
        color5: "#c678dd", color09: "#d19a66", color10: "#98c379",
        color11: "#e5c07b", color12: "#61afef",
        color13: "#c678dd", color14: "#56b6c2", color15: "#f5e6d3"
      }} : {{
        background: "#101315", foreground: "#d8dee9", accent: "#88c0d0",
        color5: "#b48ead", color09: "#bf616a", color10: "#a3be8c",
        color11: "#ebcb8b", color12: "#81a1c1",
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
    root.edgeCursor = caseId.indexOf("Edge") >= 0
    if (caseId === "backgroundVignette") {{
      item.settings = EffectRegistry.vignetteDefaults()
      item.settings.enabled = true
      item.paintEnabled = true
    }} else if (caseId === "threeEffectStack"
        || caseId === "nodeMeshBackground" || caseId === "nodeMeshForeground"
        || caseId === "rainBackground" || caseId === "rainForeground"
        || caseId === "snowBackground" || caseId === "snowForeground") {{
      var ids = EffectRegistry.orderedIds()
      var values = {{}}
      for (var i = 0; i < ids.length; i++) values[ids[i]] = EffectRegistry.defaultsFor(ids[i])
      values.dustMotes.mouseReactive = false
      if (caseId.indexOf("snow") === 0) values.rainfall.precipitationStyle = "snow"
      state.effects = values
      state.reduceMotion = false
      item.settings = state
      item.theme = theme
      item.cursorTracker = tracker
      item.targetScreen = root.renderScreen
      item.activeEffects = caseId.indexOf("nodeMesh") === 0
        ? ["nodeMesh"] : (caseId.indexOf("rain") === 0 || caseId.indexOf("snow") === 0
          ? ["rainfall"] : ["auroraDrift", "rainfall", "filmGrain"])
      item.foregroundOverlay = caseId === "nodeMeshForeground"
        || caseId === "rainForeground" || caseId === "snowForeground"
      item.productionEffectsEnabled = true
      item.paintEnabled = true
    }} else {{
      var precipitationCase = caseId.indexOf("rain") === 0 || caseId.indexOf("snow") === 0
      var registryId = caseId.indexOf("bokeh") === 0 ? "bokeh"
        : (caseId.indexOf("nodeMesh") === 0 ? "nodeMesh"
          : (precipitationCase ? "rainfall" : caseId))
      var settings = EffectRegistry.defaultsFor(registryId)
      if (caseId === "dustMotes") settings.mouseReactive = false
      if (caseId === "bokehMinimum") settings.lightCount = 6
      else if (caseId === "bokehMaximum") {{
        settings.lightCount = 72
        settings.lightSize = 240
        settings.blurSoftness = 1
        settings.driftAmount = 1
        settings.twinkleAmount = 1
      }} else if (caseId === "bokehSharp") {{
        settings.lightSize = 36
        settings.blurSoftness = 0.12
      }} else if (caseId === "bokehSoft") {{
        settings.lightSize = 200
        settings.blurSoftness = 1
      }} else if (caseId === "bokehNoDrift") settings.driftAmount = 0
      else if (caseId === "bokehTwinkleOff") settings.twinkleAmount = 0
      else if (caseId === "bokehContrastingRoles") {{
        settings.primaryColorRole = "foreground"
        settings.secondaryColorRole = "color10"
      }} else if (caseId === "nodeMeshMinimum") settings.nodeCount = 12
      else if (caseId === "nodeMeshMaximum") {{
        settings.nodeCount = 120
        settings.connectionDistance = 260
        settings.lineOpacity = 1
      }} else if (caseId === "nodeMeshShortDistance") settings.connectionDistance = 40
      else if (caseId === "nodeMeshLongDistance") settings.connectionDistance = 260
      else if (caseId === "nodeMeshLowOpacity") settings.lineOpacity = 0.08
      else if (caseId === "nodeMeshHighOpacity") settings.lineOpacity = 1
      else if (caseId === "nodeMeshPointerOff") settings.pointerMode = "off"
      else if (caseId.indexOf("nodeMeshAttract") === 0) {{
        settings.pointerMode = "attract"
        settings.mouseInfluence = 1
      }} else if (caseId.indexOf("nodeMeshRepel") === 0) {{
        settings.pointerMode = "repel"
        settings.mouseInfluence = 1
      }} else if (precipitationCase) {{
        settings.precipitationStyle = caseId.indexOf("snow") === 0 ? "snow" : "rain"
        if (caseId === "rainMistSplashMinimum") {{
          settings.mistAmount = 0
          settings.splashAmount = 0
        }} else if (caseId === "rainMistSplashMaximum") {{
          settings.mistAmount = 1
          settings.splashAmount = 1
        }} else if (caseId === "snowMinimumPopulation") settings.dropCount = 16
        else if (caseId === "snowMaximumPopulation") settings.dropCount = 320
        else if (caseId === "snowMinimumSize") settings.flakeSize = 2
        else if (caseId === "snowMaximumSize") settings.flakeSize = 18
        else if (caseId === "snowLowFlutterNegativeSlant") {{
          settings.flutterAmount = 0
          settings.slant = -0.2
        }} else if (caseId === "snowHighFlutterPositiveSlant") {{
          settings.flutterAmount = 1
          settings.slant = 0.35
        }} else if (caseId === "snowSoft") settings.flakeDetail = "soft"
        else if (caseId === "snowCrystal") settings.flakeDetail = "crystal"
        else if (caseId === "snowMixed") settings.flakeDetail = "mixed"
      }}
      item.effectSettings = settings
      item.globalOpacity = 1
      item.reducedMotion = caseId !== "rainfall" && caseId !== "tacticalGrid"
      if (precipitationCase) item.reducedMotion = caseId === "rainExtractionParity"
        || caseId === "rainReducedMotion" || caseId === "snowReducedMotion"
      if (caseId.indexOf("bokeh") === 0) item.reducedMotion = caseId === "bokehReducedMotion"
      if (caseId.indexOf("nodeMesh") === 0) item.reducedMotion = caseId === "nodeMeshReducedMotion"
      if ("theme" in item) item.theme = theme
      if ("cursorTracker" in item) item.cursorTracker = tracker
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
      var caseId = cases[caseIndex].id
      var themeSwitchCase = caseId === "threeEffectStack" || caseId === "bokehReducedMotion"
        || caseId === "nodeMeshReducedMotion" || caseId === "snowReducedMotion"
      var themeSwitchFile = caseId === "bokehReducedMotion"
        ? "{str((ARTIFACT_DIR / 'bokehThemeSwitch.png').resolve())}"
        : (caseId === "nodeMeshReducedMotion"
          ? "{str((ARTIFACT_DIR / 'nodeMeshThemeSwitch.png').resolve())}"
          : (caseId === "snowReducedMotion"
            ? "{str((ARTIFACT_DIR / 'snowThemeSwitch.png').resolve())}"
            : "{str((ARTIFACT_DIR / 'threeEffectStackThemeSwitch.png').resolve())}"))
      var outputFile = themeSwitchCase && root.themeSwitchPending
        ? themeSwitchFile : cases[caseIndex].file
      var saved = result.saveToFile(outputFile)
      if (!saved) console.log("BEHAVE_ERR failed to save " + outputFile)
      if (themeSwitchCase && !root.themeSwitchPending) {{
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

  PanelWindow {{
    id: renderWindow
    screen: root.renderScreen
    visible: false
    color: "#101315"
    WlrLayershell.namespace: "{window_title}"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
    exclusionMode: ExclusionMode.Ignore
    mask: Region {{}}
    anchors {{ top: true; bottom: true; left: true; right: true }}

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


def process_cpu_ticks(pid: int) -> int:
    fields = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").split()
    return int(fields[13]) + int(fields[14])


def bright_fraction(path: Path, geometry: str) -> float:
    proc = run([
        "magick", str(path), "-crop", geometry, "+repage", "-colorspace", "gray",
        "-threshold", "18%", "-format", "%[fx:mean]", "info:",
    ])
    return float(proc.stdout.strip())


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
    output_geometry = configure_output()

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
        start_ticks = process_cpu_ticks(proc.pid)
        end_ticks = start_ticks
        peak_rss_kib = 0
        deadline = started + max(45, len(CASES) * 1.1 + 15)
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
    image_case_ids = [case_id for case_id, _ in CASES] + [
        "bokehThemeSwitch", "nodeMeshThemeSwitch", "snowThemeSwitch",
        "threeEffectStackThemeSwitch",
    ]
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
    bokeh_hash = next(image["sha256"] for image in images if image["case"] == "bokehReducedMotion")
    bokeh_switched_hash = next(
        image["sha256"] for image in images if image["case"] == "bokehThemeSwitch"
    )
    if stack_hash == switched_hash:
        raise AssertionError("active stack pixels did not change after the theme switch")
    if bokeh_hash == bokeh_switched_hash:
        raise AssertionError("static Bokeh pixels did not change after the theme switch")
    snow_hash = next(image["sha256"] for image in images if image["case"] == "snowReducedMotion")
    snow_switched_hash = next(
        image["sha256"] for image in images if image["case"] == "snowThemeSwitch"
    )
    if snow_hash == snow_switched_hash:
        raise AssertionError("static Snow pixels did not change after the theme switch")
    node_mesh_hash = next(
        image["sha256"] for image in images if image["case"] == "nodeMeshReducedMotion"
    )
    node_mesh_switched_hash = next(
        image["sha256"] for image in images if image["case"] == "nodeMeshThemeSwitch"
    )
    if node_mesh_hash == node_mesh_switched_hash:
        raise AssertionError("static Node Mesh pixels did not change after the theme switch")

    rainfall_path = ARTIFACT_DIR / "rainfall.png"
    rainfall_top = bright_fraction(rainfall_path, "1920x540+0+0")
    rainfall_bottom = bright_fraction(rainfall_path, "1920x540+0+540")
    if rainfall_top <= 0.01 or rainfall_bottom <= 0.01:
        raise AssertionError(
            f"rainfall startup did not populate the full output: top={rainfall_top} bottom={rainfall_bottom}"
        )

    contact_sheet = ARTIFACT_DIR / "contact-sheet.webp"
    run([
        "magick", "montage",
        *[str(ARTIFACT_DIR / f"{case_id}.png") for case_id in image_case_ids],
        "-thumbnail", "360x203", "-tile", "6x10", "-geometry", "+8+24",
        "-background", "#111318", "-fill", "white", "-pointsize", "17",
        "-set", "label", "%t", str(contact_sheet),
    ], timeout=60)

    evidence = {
        "schemaVersion": 1,
        "pluginVersion": VERSION,
        "headlessOutput": output_name,
        "headlessOutputGeometry": output_geometry,
        "negativeOriginCovered": int(output_geometry["x"]) < 0 or int(output_geometry["y"]) < 0,
        "isolatedConfig": True,
        "liveSettingsModified": False,
        "renderCases": image_case_ids,
        "themeSwitchChangedPixels": stack_hash != switched_hash,
        "bokehThemeSwitchChangedPixels": bokeh_hash != bokeh_switched_hash,
        "nodeMeshThemeSwitchChangedPixels": node_mesh_hash != node_mesh_switched_hash,
        "precipitationThemeSwitchChangedPixels": snow_hash != snow_switched_hash,
        "precipitationPresentationCases": [
            "rainBackground", "rainForeground", "snowBackground", "snowForeground"
        ],
        "precipitationVisualCases": [
            case_id for case_id, _ in CASES
            if case_id.startswith("rain") or case_id.startswith("snow")
        ],
        "rainExtractionParityEvidence": "rainfall-extraction-parity.json",
        "nodeMeshPresentationCases": ["nodeMeshBackground", "nodeMeshForeground"],
        "rainfallStartupCoverage": {
            "topBrightFraction": rainfall_top,
            "bottomBrightFraction": rainfall_bottom,
        },
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
