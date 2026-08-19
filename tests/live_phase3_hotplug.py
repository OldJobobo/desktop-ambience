#!/usr/bin/env python3
"""Opt-in live Hyprland output lifecycle check for the Phase 3 surface gate."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import uuid
from pathlib import Path

from qml_harness import parse_behave, qml_url, require_no_qml_errors, run_quickshell


if os.environ.get("JOBO_AMBIENCE_LIVE_HOTPLUG") != "1":
    raise SystemExit("set JOBO_AMBIENCE_LIVE_HOTPLUG=1 to run the reversible live hotplug check")

output_name = f"JOBO-PHASE3-{uuid.uuid4().hex[:8]}"

qml = f'''
import Quickshell
import Quickshell.Io
import QtQuick
ShellRoot {{
  property int stage: 0
  property int baseline: -1
  property bool observedAdd: false
  Loader {{ id: panelLoader; source: "{qml_url('Panel.qml')}"; onLoaded: probe.start() }}
  Process {{
    id: createOutput
    command: ["hyprctl", "output", "create", "headless", "{output_name}"]
    onExited: function(code) {{
      if (code !== 0) {{ console.log("BEHAVE_ERR could not create headless output"); Qt.quit() }}
      else stage = 2
    }}
  }}
  Process {{
    id: removeOutput
    command: ["hyprctl", "output", "remove", "{output_name}"]
    onExited: function(code) {{
      if (code !== 0) {{ console.log("BEHAVE_ERR could not remove headless output"); Qt.quit() }}
      else stage = 4
    }}
  }}
  function outputNames(panel) {{
    var names = []
    for (var i = 0; i < panel.productionSurfaces.length; i++) names.push(panel.surfaceAt(i).outputName)
    return names
  }}
  function unique(values) {{
    var seen = {{}}
    for (var i = 0; i < values.length; i++) {{
      if (seen[values[i]]) return false
      seen[values[i]] = true
    }}
    return true
  }}
  Timer {{
    id: probe; interval: 50; repeat: true; property int attempts: 0
    onTriggered: {{
      attempts += 1
      var panel = panelLoader.item
      if (!panel || !panel.settingsService.hasLoaded) return
      var screens = Quickshell.screens.length
      var names = outputNames(panel)
      if (stage === 0 && panel.productionSurfaces.length === screens
          && panel.mappedSurfaceCount() === screens) {{
        baseline = screens
        stage = 1
        createOutput.running = true
      }} else if (stage === 2 && screens === baseline + 1
          && panel.productionSurfaces.length === screens
          && panel.mappedSurfaceCount() === screens
          && names.indexOf("{output_name}") >= 0 && unique(names)) {{
        observedAdd = true
        stage = 3
        removeOutput.running = true
      }} else if (stage === 4 && screens === baseline
          && panel.productionSurfaces.length === baseline
          && panel.mappedSurfaceCount() === baseline
          && names.indexOf("{output_name}") < 0 && unique(names)) {{
        stop()
        console.log("BEHAVE " + JSON.stringify({{baseline: baseline,
          observedAdd: observedAdd, finalScreens: screens,
          finalSurfaces: panel.productionSurfaces.length,
          finalMapped: panel.mappedSurfaceCount(), names: names}}))
        Qt.quit()
      }} else if (attempts > 300) {{
        console.log("BEHAVE_ERR hotplug lifecycle did not settle at stage " + stage
          + " screens=" + screens + " surfaces=" + panel.productionSurfaces.length
          + " mapped=" + panel.mappedSurfaceCount() + " names=" + JSON.stringify(names))
        Qt.quit()
      }}
    }}
  }}
}}
'''

try:
    with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as state_dir:
        config_home = Path(config_dir)
        settings_file = config_home / "omarchy/jobo/desktop-ambience/settings.json"
        settings_file.parent.mkdir(parents=True)
        settings_file.write_text(json.dumps({
            "version": 1,
            "enabled": True,
            "presentation": "background",
            "activeEffects": ["trackingLines"],
            "effects": {"trackingLines": {"enabled": True, "intensity": 0}},
            "backgroundVignette": {"enabled": False},
        }), encoding="utf-8")
        state_home = Path(state_dir)
        palette = state_home / "omarchy/current/theme/colors.toml"
        palette.parent.mkdir(parents=True)
        palette.write_text('color11 = "#aabbcc"\n', encoding="utf-8")
        output = run_quickshell(
            qml,
            config_home=config_home,
            env_overrides={"XDG_STATE_HOME": str(state_home)},
            timeout=25,
        )
    require_no_qml_errors(output)
    row = parse_behave(output)[-1]
    assert row["observedAdd"] is True, row
    assert row["finalScreens"] == row["baseline"], row
    assert row["finalSurfaces"] == row["baseline"], row
    assert row["finalMapped"] == row["baseline"], row
    print(json.dumps(row, indent=2))
finally:
    subprocess.run(
        ["hyprctl", "output", "remove", output_name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
