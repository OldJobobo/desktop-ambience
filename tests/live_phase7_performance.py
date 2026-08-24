#!/usr/bin/env python3
"""Opt-in isolated per-effect Phase 7 performance matrix.

The harness creates three temporary headless outputs and launches a fresh
Quickshell process for every effect/output-count pair. Live plugin settings are
never read or written. Use --target-root to profile an older Git worktree with
the current harness.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

from qml_harness import parse_behave, qml_url, require_no_qml_errors


if os.environ.get("JOBO_AMBIENCE_LIVE_PHASE7") != "1":
    raise SystemExit("set JOBO_AMBIENCE_LIVE_PHASE7=1 to run the Phase 7 performance matrix")
if not os.environ.get("WAYLAND_DISPLAY"):
    raise SystemExit("an active Wayland session is required")
for tool in ("quickshell", "hyprctl"):
    if not shutil.which(tool):
        raise SystemExit(f"missing required tool: {tool}")

REPO_ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ("auroraDrift", "effects/AuroraDriftEffect.qml"),
    ("cinematicLight", "effects/CinematicLightEffect.qml"),
    ("crt", "effects/CrtEffect.qml"),
    ("dustMotes", "effects/DustMotesEffect.qml"),
    ("drip", "effects/DripEffect.qml"),
    ("dripMax", "effects/DripEffect.qml"),
    ("dripReduced", "effects/DripEffect.qml"),
    ("filmGrain", "effects/FilmGrainEffect.qml"),
    ("godRays", "effects/GodRaysEffect.qml"),
    ("rainfall", "effects/RainfallEffect.qml"),
    ("rainDefault", "effects/RainfallEffect.qml"),
    ("snowDefault", "effects/RainfallEffect.qml"),
    ("rainMaximumPopulation", "effects/RainfallEffect.qml"),
    ("snowMaximumPopulation", "effects/RainfallEffect.qml"),
    ("snowMaximumSizeCrystal", "effects/RainfallEffect.qml"),
    ("rainMistSplashMinimum", "effects/RainfallEffect.qml"),
    ("rainMistSplashMaximum", "effects/RainfallEffect.qml"),
    ("rainReducedMotion", "effects/RainfallEffect.qml"),
    ("snowReducedMotion", "effects/RainfallEffect.qml"),
    ("precipitationStyleSwitchChurn", "effects/RainfallEffect.qml"),
    ("rainHidden", "effects/RainfallEffect.qml"),
    ("snowHidden", "effects/RainfallEffect.qml"),
    ("rainFullscreenSuppressed", "effects/RainfallEffect.qml"),
    ("snowFullscreenSuppressed", "effects/RainfallEffect.qml"),
    ("tacticalGrid", "effects/TacticalGridEffect.qml"),
    ("trackingLines", "effects/VhsEffect.qml"),
    ("bokeh", "effects/BokehEffect.qml"),
    ("bokehReducedMotion", "effects/BokehEffect.qml"),
    ("bokehMaximumPopulation", "effects/BokehEffect.qml"),
    ("bokehMaximumSoftness", "effects/BokehEffect.qml"),
    ("bokehHidden", "effects/BokehEffect.qml"),
    ("bokehFullscreenSuppressed", "effects/BokehEffect.qml"),
    ("nodeMeshStatic", "effects/NodeMeshEffect.qml"),
    ("nodeMeshDefault", "effects/NodeMeshEffect.qml"),
    ("nodeMeshMaximum", "effects/NodeMeshEffect.qml"),
    ("nodeMeshPointerOff", "effects/NodeMeshEffect.qml"),
    ("nodeMeshPointerAttract", "effects/NodeMeshEffect.qml"),
    ("nodeMeshPointerRepel", "effects/NodeMeshEffect.qml"),
    ("nodeMeshHidden", "effects/NodeMeshEffect.qml"),
    ("nodeMeshFullscreenSuppressed", "effects/NodeMeshEffect.qml"),
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


def wait_for_outputs(names: list[str], present: bool, timeout: float = 10) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        payload = json.loads(run(["hyprctl", "-j", "monitors", "all"]).stdout)
        current = {str(item.get("name")) for item in payload}
        if all((name in current) is present for name in names):
            return
        time.sleep(0.1)
    raise AssertionError(f"outputs did not settle present={present}: {names}")


def configure_temporary_output(name: str, x: int) -> dict:
    expression = (
        "hl.monitor({"
        f'output = "{name}", mode = "1920x1080@60", position = "{x}x0", '
        "scale = 1, transform = 0"
        "})"
    )
    run(["hyprctl", "eval", expression])
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        payload = json.loads(run(["hyprctl", "-j", "monitors", "all"]).stdout)
        monitor = next((item for item in payload if str(item.get("name")) == name), None)
        if monitor and int(monitor.get("x", 0)) == x:
            return {
                "name": name,
                "x": int(monitor.get("x", 0)),
                "y": int(monitor.get("y", 0)),
                "width": int(monitor.get("width", 0)),
                "height": int(monitor.get("height", 0)),
                "scale": float(monitor.get("scale", 1)),
            }
        time.sleep(0.1)
    raise AssertionError(f"temporary output {name} did not settle at x={x}")


def proc_ticks(pid: int) -> int:
    fields = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").split()
    return int(fields[13]) + int(fields[14])


def proc_rss_kib(pid: int) -> int:
    for line in Path(f"/proc/{pid}/status").read_text(encoding="utf-8").splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1])
    return 0


def make_qml(
    target_root: Path,
    case_id: str,
    source: str,
    output_names: list[str],
    duration_ms: int,
    shared_tracker: bool,
) -> str:
    registry_url = (target_root / "services/EffectRegistry.js").as_uri()
    source_url = (target_root / source).as_uri()
    tracker_source = (target_root / "services/CursorTracker.qml").as_uri() if shared_tracker else ""

    windows = []
    for index, name in enumerate(output_names):
        windows.append(f'''
  PanelWindow {{
    id: renderWindow{index}
    screen: root.renderScreen("{name}")
    visible: true
    color: "#101315"
    WlrLayershell.namespace: "jobo-phase7-{case_id}-{index}"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
    exclusionMode: ExclusionMode.Ignore
    mask: Region {{}}
    anchors {{ top: true; bottom: true; left: true; right: true }}
    Loader {{
      anchors.fill: parent
      source: "{source_url}"
      onLoaded: root.configure(item, "{name}")
    }}
  }}''')

    tracker_loader = f'''
  Loader {{
    id: trackerLoader
    active: true
    source: "{tracker_source}"
  }}''' if shared_tracker else "  QtObject { id: trackerLoader; property var item: null }"

    tracker_assign = ('if ("cursorTracker" in item) item.cursorTracker = '
                      '(caseId.indexOf("nodeMeshPointer") === 0 ? nodeTracker : trackerLoader.item)') if shared_tracker else ""
    stack_tracker_assign = "item.cursorTracker = trackerLoader.item" if shared_tracker else ""
    tracker_start = ('if (trackerLoader.item) trackerLoader.item.active = caseId === "dustMotes" '
                     '|| caseId === "tacticalGrid" || caseId === "nodeMeshPointerAttract" '
                     '|| caseId === "nodeMeshPointerRepel"') if shared_tracker else ""
    tracker_stop = "if (trackerLoader.item) trackerLoader.item.active = false" if shared_tracker else ""
    tracker_count = "trackerLoader.item ? trackerLoader.item.launchCount : -1" if shared_tracker else "-1"

    return f'''
import Quickshell
import Quickshell.Wayland
import QtQuick
import "{registry_url}" as EffectRegistry

ShellRoot {{
  id: root
  property string caseId: "{case_id}"
  property int loadedCount: 0
  property bool measuring: false
  property int frameCount: 0
  property real frameTotalMs: 0
  property real frameMaxMs: 0
  property int framesOver20Ms: 0
  property int allocatedDelegateCount: 0
  property var loadedItems: []
  property int nodeMeshBaselineUpdates: 0
  property int nodeMeshBaselinePaints: 0
  property int precipitationBaselineUpdates: 0
  property int precipitationSwitchCount: 0
  property var precipitationRootIdentities: []
  property var precipitationBeforeShutdown: ({{}})
  readonly property bool precipitationCase: caseId.indexOf("rain") === 0
    || caseId.indexOf("snow") === 0 || caseId === "precipitationStyleSwitchChurn"

  QtObject {{
    id: state
    property real opacity: 1
    property bool reduceMotion: false
    property var effects: ({{}})
  }}

  QtObject {{
    id: nodeTracker
    property var ownerScreen: root.renderScreen("{output_names[0]}")
    property bool hasCursorSample: ownerScreen !== null
    property real cursorX: ownerScreen ? Number(ownerScreen.x) + 960 : -1
    property real cursorY: ownerScreen ? Number(ownerScreen.y) + 540 : -1
    property real displayCursorX: cursorX
    property real displayCursorY: cursorY
  }}

  QtObject {{
    id: theme
    function colorFor(name, fallback) {{
      var colors = {{
        background: "#101315", foreground: "#d8dee9", accent: "#88c0d0",
        color5: "#b48ead", color09: "#bf616a", color10: "#a3be8c",
        color11: "#ebcb8b", color12: "#81a1c1",
        color13: "#b48ead", color14: "#8fbcbb", color15: "#eceff4"
      }}
      return colors[name] || fallback
    }}
  }}

  function renderScreen(name) {{
    for (var i = 0; i < Quickshell.screens.length; i++)
      if (String(Quickshell.screens[i].name) === name) return Quickshell.screens[i]
    return null
  }}

  function windowScreen(name) {{
    for (var i = 0; i < Qt.application.screens.length; i++)
      if (String(Qt.application.screens[i].name) === name) return Qt.application.screens[i]
    return null
  }}

  function bokehMetrics() {{
    var delegates = 0
    var blurLayers = 0
    var animatedOutputs = 0
    var visibleOutputs = 0
    for (var i = 0; i < loadedItems.length; i++) {{
      var item = loadedItems[i]
      if (!item || item.activeBlurLayerCount === undefined) continue
      delegates += Number(item.boundedDelegateCount)
      blurLayers += Number(item.activeBlurLayerCount)
      if (item.animationRunning) animatedOutputs += 1
      if (item.effectVisible) visibleOutputs += 1
    }}
    return {{delegateCount: delegates, blurLayerCount: blurLayers,
      animatedOutputs: animatedOutputs, visibleOutputs: visibleOutputs}}
  }}

  function precipitationMetrics() {{
    var loadedStyles = 0
    var rainOutputs = 0
    var snowOutputs = 0
    var particles = 0
    var crystals = 0
    var primitives = 0
    var animationObjects = 0
    var runningAnimations = 0
    var clockObjects = 0
    var runningClocks = 0
    var clockUpdates = 0
    var autonomousOutputs = 0
    var visibleOutputs = 0
    var generations = 0
    var destructions = 0
    var rootsStable = true
    for (var i = 0; i < loadedItems.length; i++) {{
      var item = loadedItems[i]
      if (!item || item.selectedStyle === undefined) continue
      loadedStyles += Number(item.loadedStyleCount)
      if (item.selectedStyle === "snow") snowOutputs += 1
      else rainOutputs += 1
      particles += Number(item.boundedParticleCount)
      crystals += Number(item.snowCrystalCount)
      primitives += item.selectedStyle === "snow"
        ? Number(item.snowPrimitiveCount) : Number(item.boundedParticleCount)
      animationObjects += Number(item.animationObjectCount)
      runningAnimations += Number(item.runningAnimationCount)
      clockObjects += Number(item.clockObjectCount)
      runningClocks += Number(item.runningClockCount)
      clockUpdates += Number(item.snowClockUpdateCount)
      if (item.autonomousMotionRunning) autonomousOutputs += 1
      if (item.effectVisible) visibleOutputs += 1
      generations += Number(item.styleGeneration)
      destructions += Number(item.destroyedStyleCount)
      if (precipitationRootIdentities.length > i
          && precipitationRootIdentities[i] !== item) rootsStable = false
    }}
    return {{loadedStyleCount: loadedStyles, rainOutputs: rainOutputs, snowOutputs: snowOutputs,
      particleCount: particles, crystalCount: crystals, primitiveCount: primitives,
      animationObjectCount: animationObjects, runningAnimationCount: runningAnimations,
      clockObjectCount: clockObjects, runningClockCount: runningClocks,
      clockUpdates: clockUpdates,
      clockUpdateDelta: Math.max(0, clockUpdates - precipitationBaselineUpdates),
      autonomousOutputs: autonomousOutputs, visibleOutputs: visibleOutputs,
      styleGeneration: generations, destroyedStyleCount: destructions,
      rootIdentityStable: rootsStable, styleSwitchCount: precipitationSwitchCount}}
  }}

  function togglePrecipitationStyle() {{
    if (!precipitationCase) return
    for (var i = 0; i < loadedItems.length; i++) {{
      var item = loadedItems[i]
      if (!item || item.selectedStyle === undefined) continue
      var next = Object.assign({{}}, item.effectSettings)
      next.precipitationStyle = item.selectedStyle === "snow" ? "rain" : "snow"
      item.effectSettings = next
    }}
    precipitationSwitchCount += 1
  }}

  function stopPrecipitation() {{
    for (var i = 0; i < loadedItems.length; i++) {{
      var item = loadedItems[i]
      if (item && item.selectedStyle !== undefined) item.runtimeEnabled = false
    }}
  }}

  function nodeMeshMetrics() {{
    var updates = 0
    var paints = 0
    var nodes = 0
    var edges = 0
    var paths = 0
    var runningOutputs = 0
    var visibleOutputs = 0
    var pointerOwnedOutputs = 0
    var pointerActiveOutputs = 0
    for (var i = 0; i < loadedItems.length; i++) {{
      var item = loadedItems[i]
      if (!item || item.simulationUpdateCount === undefined) continue
      updates += Number(item.simulationUpdateCount)
      paints += Number(item.paintRequestCount)
      nodes += Number(item.acceptedNodeCount)
      edges += Number(item.edgeCount)
      paths += Number(item.shapePathCount)
      if (item.simulationRunning) runningOutputs += 1
      if (item.effectVisible) visibleOutputs += 1
      if (item.cursorOwned) pointerOwnedOutputs += 1
      if (item.pointerForceActive) pointerActiveOutputs += 1
    }}
    return {{updates: updates, paints: paints, nodeCount: nodes, edgeCount: edges,
      pathCount: paths, runningOutputs: runningOutputs, visibleOutputs: visibleOutputs,
      pointerOwnedOutputs: pointerOwnedOutputs, pointerActiveOutputs: pointerActiveOutputs}}
  }}

  function reportResult() {{
    var nodeMetrics = root.nodeMeshMetrics()
    nodeMetrics.updateDelta = nodeMetrics.updates - root.nodeMeshBaselineUpdates
    nodeMetrics.paintDelta = nodeMetrics.paints - root.nodeMeshBaselinePaints
    console.log("BEHAVE " + JSON.stringify({{
      caseId: caseId,
      outputs: {len(output_names)},
      frameCount: frameCount,
      meanFrameMs: frameCount > 0 ? frameTotalMs / frameCount : 0,
      maxFrameMs: frameMaxMs,
      framesOver20Ms: framesOver20Ms,
      cursorLaunchCount: {tracker_count},
      bokeh: root.bokehMetrics(),
      nodeMesh: nodeMetrics,
      precipitation: root.precipitationCase ? root.precipitationBeforeShutdown : ({{}}),
      precipitationAfterShutdown: root.precipitationCase ? root.precipitationMetrics() : ({{}}),
      allocatedDelegateCount: root.allocatedDelegateCount
    }}))
    Qt.quit()
  }}

  function configure(item, outputName) {{
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
      item.settings = state
      item.theme = theme
      {stack_tracker_assign}
      item.activeEffects = ["auroraDrift", "rainfall", "filmGrain"]
      item.productionEffectsEnabled = true
      item.paintEnabled = true
    }} else {{
      var registryId = caseId.indexOf("bokeh") === 0 ? "bokeh"
        : (caseId.indexOf("nodeMesh") === 0 ? "nodeMesh"
          : (caseId.indexOf("drip") === 0 ? "drip"
            : (root.precipitationCase ? "rainfall" : caseId)))
      var effectSettings = EffectRegistry.defaultsFor(registryId)
      if (caseId === "dripMax") effectSettings.dropletCount = 72
      else if (caseId === "bokehMaximumPopulation") effectSettings.lightCount = 72
      else if (caseId === "bokehMaximumSoftness") {{
        effectSettings.lightSize = 240
        effectSettings.blurSoftness = 1
        effectSettings.driftAmount = 1
      }} else if (caseId === "nodeMeshMaximum") {{
        effectSettings.nodeCount = 120
        effectSettings.connectionDistance = 260
        effectSettings.lineOpacity = 1
      }} else if (caseId === "nodeMeshPointerOff") {{
        effectSettings.pointerMode = "off"
        effectSettings.mouseInfluence = 1
      }} else if (caseId === "nodeMeshPointerAttract") {{
        effectSettings.pointerMode = "attract"
        effectSettings.mouseInfluence = 1
      }} else if (caseId === "nodeMeshPointerRepel") {{
        effectSettings.pointerMode = "repel"
        effectSettings.mouseInfluence = 1
      }} else if (root.precipitationCase) {{
        effectSettings.precipitationStyle = caseId.indexOf("snow") === 0 ? "snow" : "rain"
        if (caseId === "rainMaximumPopulation" || caseId === "snowMaximumPopulation"
            || caseId === "snowMaximumSizeCrystal") effectSettings.dropCount = 320
        if (caseId === "snowMaximumSizeCrystal") {{
          effectSettings.flakeSize = 18
          effectSettings.flakeDetail = "crystal"
          effectSettings.flutterAmount = 1
        }}
        if (caseId === "rainMistSplashMinimum") {{
          effectSettings.mistAmount = 0
          effectSettings.splashAmount = 0
        }} else if (caseId === "rainMistSplashMaximum") {{
          effectSettings.mistAmount = 1
          effectSettings.splashAmount = 1
        }}
      }}
      item.effectSettings = effectSettings
      item.globalOpacity = (caseId === "bokehHidden" || caseId === "nodeMeshHidden"
        || caseId === "rainHidden" || caseId === "snowHidden") ? 0 : 1
      item.reducedMotion = caseId === "dripReduced" || caseId === "bokehReducedMotion"
        || caseId === "nodeMeshStatic" || caseId === "rainReducedMotion" || caseId === "snowReducedMotion"
      if (caseId === "bokehFullscreenSuppressed" || caseId === "nodeMeshFullscreenSuppressed"
          || caseId === "rainFullscreenSuppressed" || caseId === "snowFullscreenSuppressed")
        item.runtimeEnabled = false
      if ("theme" in item) item.theme = theme
      if ("barState" in item) item.barState = {{available: true, position: "top", size: 28, hidden: false, color: "#101315"}}
      {tracker_assign}
    }}
    if ("targetScreen" in item) item.targetScreen = renderScreen(outputName)
    if ("allocatedDropletCount" in item) allocatedDelegateCount += Number(item.allocatedDropletCount)
    loadedItems = loadedItems.concat([item])
    loadedCount += 1
    if (loadedCount === {len(output_names)}) warmup.start()
  }}

  {tracker_loader}

  Timer {{
    id: warmup
    interval: 1200
    onTriggered: {{
      {tracker_start}
      var nodeMetrics = root.nodeMeshMetrics()
      root.nodeMeshBaselineUpdates = nodeMetrics.updates
      root.nodeMeshBaselinePaints = nodeMetrics.paints
      var precipitation = root.precipitationMetrics()
      root.precipitationBaselineUpdates = precipitation.clockUpdates
      root.precipitationRootIdentities = root.loadedItems.slice()
      if (caseId === "precipitationStyleSwitchChurn") styleChurn.start()
      root.measuring = true
      sample.stop()
      sample.start()
    }}
  }}

  FrameAnimation {{
    running: root.measuring
    onTriggered: {{
      var milliseconds = frameTime * 1000
      root.frameCount += 1
      root.frameTotalMs += milliseconds
      root.frameMaxMs = Math.max(root.frameMaxMs, milliseconds)
      if (milliseconds > 20) root.framesOver20Ms += 1
    }}
  }}

  Timer {{
    id: styleChurn
    interval: 120
    repeat: true
    onTriggered: root.togglePrecipitationStyle()
  }}

  Timer {{
    id: sample
    interval: {duration_ms}
    onTriggered: {{
      root.measuring = false
      {tracker_stop}
      styleChurn.stop()
      if (root.precipitationCase) {{
        root.precipitationBeforeShutdown = root.precipitationMetrics()
        root.stopPrecipitation()
        shutdownProbe.start()
      }} else root.reportResult()
    }}
  }}

  Timer {{
    id: shutdownProbe
    interval: 180
    onTriggered: root.reportResult()
  }}

  {''.join(windows)}
}}
'''


def profile_case(
    target_root: Path,
    case_id: str,
    source: str,
    output_names: list[str],
    duration_ms: int,
    shared_tracker: bool,
) -> dict:
    qml = make_qml(target_root, case_id, source, output_names, duration_ms, shared_tracker)
    with tempfile.TemporaryDirectory() as directory:
        temp = Path(directory)
        shell = temp / "shell.qml"
        shell.write_text(qml, encoding="utf-8")
        omarchy_shell = Path(os.environ.get("OMARCHY_PATH", "/usr/share/omarchy")) / "shell"
        for module in ("Commons", "Ui"):
            source_dir = omarchy_shell / module
            if source_dir.is_dir():
                (temp / module).symlink_to(source_dir, target_is_directory=True)
        env = os.environ.copy()
        env["QT_QPA_PLATFORM"] = "wayland"
        env["XDG_CONFIG_HOME"] = str(temp / "config")
        env["XDG_STATE_HOME"] = str(temp / "state")
        proc = subprocess.Popen(
            ["quickshell", "-p", str(shell)], env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        try:
            time.sleep(1.7)
            started_at = time.monotonic()
            start_ticks = proc_ticks(proc.pid)
            end_ticks = start_ticks
            peak_rss = 0
            samples = 0
            while proc.poll() is None:
                end_ticks = proc_ticks(proc.pid)
                peak_rss = max(peak_rss, proc_rss_kib(proc.pid))
                samples += 1
                time.sleep(0.1)
            elapsed = max(0.001, time.monotonic() - started_at)
            stdout, stderr = proc.communicate(timeout=5)
        except Exception:
            proc.kill()
            stdout, stderr = proc.communicate()
            raise
    output = stdout + stderr
    require_no_qml_errors(output)
    rows = parse_behave(output)
    if proc.returncode != 0 or not rows:
        raise AssertionError(f"performance case failed: {case_id}/{len(output_names)}\n{output[-4000:]}")
    row = rows[-1]
    ticks_per_second = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
    row.update({
        "averageCpuPercent": (end_ticks - start_ticks) / ticks_per_second / elapsed * 100,
        "peakRssKiB": peak_rss,
        "processSamples": samples,
        "sharedCursorTracker": shared_tracker,
        "legacyExpectedCursorLaunchesPerSecond": (
            len(output_names) * 1000 / 120 if case_id == "dustMotes" and not shared_tracker else 0
        ),
    })
    if case_id.startswith("nodeMesh"):
        metrics = row["nodeMesh"]
        population = 120 if case_id == "nodeMeshMaximum" else 54
        expected_nodes = population * len(output_names)
        expected_paths = 8 * len(output_names)
        if metrics["nodeCount"] != expected_nodes or metrics["pathCount"] != expected_paths:
            raise AssertionError(row)
        expected_edge_ceiling = population * 2 * len(output_names)
        if metrics["edgeCount"] > expected_edge_ceiling:
            raise AssertionError(row)
        maximum_updates = (duration_ms / 1000) * 31 * len(output_names)
        if metrics["updateDelta"] > maximum_updates or metrics["paintDelta"] < metrics["updateDelta"]:
            raise AssertionError(row)
        stopped = case_id in {"nodeMeshStatic", "nodeMeshHidden", "nodeMeshFullscreenSuppressed"}
        if stopped and (metrics["updateDelta"] != 0 or metrics["runningOutputs"] != 0):
            raise AssertionError(row)
        if not stopped and metrics["updateDelta"] <= 0:
            raise AssertionError(row)
        if case_id in {"nodeMeshPointerAttract", "nodeMeshPointerRepel"}:
            if (metrics["pointerOwnedOutputs"] != 1 or metrics["pointerActiveOutputs"] != 1
                    or row["cursorLaunchCount"] <= 0):
                raise AssertionError(row)
        if case_id == "nodeMeshPointerOff":
            if metrics["pointerActiveOutputs"] != 0 or row["cursorLaunchCount"] != 0:
                raise AssertionError(row)
    precipitation_case = (
        case_id.startswith("rain") or case_id.startswith("snow")
        or case_id == "precipitationStyleSwitchChurn"
    )
    if precipitation_case:
        metrics = row["precipitation"]
        stopped_metrics = row["precipitationAfterShutdown"]
        outputs = len(output_names)
        if metrics["loadedStyleCount"] != outputs or not metrics["rootIdentityStable"]:
            raise AssertionError(row)
        if not 16 * outputs <= metrics["particleCount"] <= 500 * outputs:
            raise AssertionError(row)
        if not metrics["particleCount"] <= metrics["primitiveCount"] <= 1280 * outputs:
            raise AssertionError(row)
        if metrics["animationObjectCount"] > 520 * outputs or metrics["clockObjectCount"] > outputs:
            raise AssertionError(row)
        stopped = case_id in {
            "rainReducedMotion", "snowReducedMotion", "rainHidden", "snowHidden",
            "rainFullscreenSuppressed", "snowFullscreenSuppressed",
        }
        if stopped:
            if any(metrics[key] != 0 for key in (
                "autonomousOutputs", "runningAnimationCount", "runningClockCount", "clockUpdateDelta"
            )):
                raise AssertionError(row)
        elif metrics["autonomousOutputs"] != outputs:
            raise AssertionError(row)
        if case_id.startswith("snow"):
            if metrics["snowOutputs"] != outputs or metrics["clockObjectCount"] != outputs:
                raise AssertionError(row)
            if not stopped and metrics["clockUpdateDelta"] <= 0:
                raise AssertionError(row)
        if case_id.startswith("rain") or case_id == "rainfall":
            if metrics["rainOutputs"] != outputs or metrics["clockObjectCount"] != 0:
                raise AssertionError(row)
        if case_id == "precipitationStyleSwitchChurn":
            if (metrics["styleSwitchCount"] < 4
                    or metrics["styleGeneration"] <= outputs
                    or metrics["destroyedStyleCount"] < outputs):
                raise AssertionError(row)
        if any(stopped_metrics[key] != 0 for key in (
            "autonomousOutputs", "visibleOutputs", "runningAnimationCount", "runningClockCount"
        )):
            raise AssertionError(row)
        if stopped_metrics["loadedStyleCount"] != outputs or not stopped_metrics["rootIdentityStable"]:
            raise AssertionError(row)
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--duration-ms", type=int, default=4000)
    parser.add_argument("--output-counts", default="1,3")
    parser.add_argument("--cases", default="")
    parser.add_argument("--repetitions", type=int, default=1)
    args = parser.parse_args()
    target_root = args.target_root.resolve()
    version = json.loads((target_root / "manifest.json").read_text(encoding="utf-8"))["version"]
    shared_tracker = (target_root / "services/CursorTracker.qml").is_file()
    output_counts = [int(value) for value in args.output_counts.split(",")]
    if not output_counts or min(output_counts) < 1 or max(output_counts) > 3:
        raise SystemExit("--output-counts must contain values from 1 through 3")
    requested_cases = {value for value in args.cases.split(",") if value}
    selected_cases = [case for case in CASES if not requested_cases or case[0] in requested_cases]
    if requested_cases and {case[0] for case in selected_cases} != requested_cases:
        raise SystemExit("--cases contains an unknown effect ID")
    if args.repetitions < 1:
        raise SystemExit("--repetitions must be positive")

    output_names = [f"JOBO-PHASE7-PERF-{uuid.uuid4().hex[:8]}-{index}" for index in range(3)]
    results: list[dict] = []
    output_layout: list[dict] = []
    try:
        for name in output_names:
            run(["hyprctl", "output", "create", "headless", name])
        wait_for_outputs(output_names, True)
        for index, name in enumerate(output_names):
            output_layout.append(configure_temporary_output(name, -5760 + index * 1920))
        for repetition in range(1, args.repetitions + 1):
            for count in output_counts:
                for case_id, source in selected_cases:
                    result = profile_case(
                        target_root, case_id, source, output_names[:count],
                        args.duration_ms, shared_tracker,
                    )
                    result["repetition"] = repetition
                    result["outputGeometry"] = output_layout[:count]
                    results.append(result)
                    print(
                        f"{case_id:22} outputs={count} run={repetition} "
                        f"cpu={result['averageCpuPercent']:.2f}% "
                        f"rss={result['peakRssKiB'] / 1024:.1f}MiB frame={result['meanFrameMs']:.2f}ms"
                    )
    finally:
        for name in reversed(output_names):
            run(["hyprctl", "output", "remove", name], check=False)
        wait_for_outputs(output_names, False)

    evidence = {
        "schemaVersion": 1,
        "pluginVersion": version,
        "targetRoot": str(target_root),
        "isolatedConfig": True,
        "liveSettingsModified": False,
        "durationMs": args.duration_ms,
        "repetitions": args.repetitions,
        "cases": [case[0] for case in selected_cases],
        "temporaryOutputLayout": output_layout,
        "negativeOriginCovered": any(item["x"] < 0 or item["y"] < 0 for item in output_layout),
        "results": results,
    }
    output_path = args.output or REPO_ROOT / "docs/performance/evidence" / version / "phase7-performance.json"
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
