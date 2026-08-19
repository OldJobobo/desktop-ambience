import json
import tempfile
import unittest
from pathlib import Path

from qml_harness import HAVE_SESSION, parse_behave, qml_url, require_no_qml_errors, run_quickshell


@unittest.skipUnless(HAVE_SESSION, "needs a quickshell binary and a Wayland session")
class QmlLoadSmokeTests(unittest.TestCase):
    def test_all_eight_effect_files_load_with_complete_normalized_settings(self):
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  Loader {{ id: settingsLoader; source: "{qml_url('services/AmbienceSettings.qml')}" }}
  QtObject {{
    id: state
    property var activeEffects: ["auroraDrift", "cinematicLight", "crt", "dustMotes", "filmGrain", "godRays", "rainfall", "trackingLines"]
    property real opacity: 1
    property bool reduceMotion: true
    property var effects: settingsLoader.item ? settingsLoader.item.effects : ({{}})
  }}
  Item {{
    width: 32; height: 32
    Loader {{
      id: stackLoader
      anchors.fill: parent
      source: "{qml_url('components/AmbienceStack.qml')}"
      onLoaded: {{
        item.settings = state
        item.paintEnabled = true
        probe.start()
      }}
    }}
  }}
  Timer {{
    id: probe; interval: 50; repeat: true; property int attempts: 0
    onTriggered: {{
      attempts += 1
      if (!settingsLoader.item || !settingsLoader.item.hasLoaded || !stackLoader.item
          || stackLoader.item.activeProductionEffectCount !== 8) {{
        if (attempts > 30) {{
          var status = {{count: stackLoader.item ? stackLoader.item.activeProductionEffectCount : -1, ids: []}}
          if (stackLoader.item) for (var j = 0; j < stackLoader.item.supportedEffects.length; j++) {{
            var id = stackLoader.item.supportedEffects[j]
            status.ids.push([id, stackLoader.item.productionEffectActive(id), stackLoader.item.productionEffectObject(id) !== null])
          }}
          console.log("BEHAVE_ERR all effects did not load " + JSON.stringify(status)); Qt.quit()
        }}
        return
      }}
      var ids = stackLoader.item.supportedEffects
      var loaded = []
      for (var i = 0; i < ids.length; i++)
        if (stackLoader.item.productionEffectObject(ids[i]) !== null) loaded.push(ids[i])
      console.log("BEHAVE " + JSON.stringify({{count: loaded.length, ids: loaded}}))
      Qt.quit()
    }}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as config_home:
            output = run_quickshell(qml, config_home=Path(config_home), timeout=15)
        require_no_qml_errors(output)
        row = parse_behave(output)[-1]
        self.assertEqual(row["count"], 8, output[-2000:])
        self.assertEqual(
            row["ids"],
            ["auroraDrift", "cinematicLight", "crt", "dustMotes", "filmGrain", "godRays", "rainfall", "trackingLines"],
        )

    def test_panel_root_loads_inert_from_temp_disabled_config(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as state_dir:
            config_home = Path(config_dir)
            settings_file = config_home / "omarchy/jobo/desktop-ambience/settings.json"
            settings_file.parent.mkdir(parents=True)
            settings_file.write_text(
                json.dumps({"version": 1, "enabled": False, "activeEffects": [], "effects": {},
                            "backgroundVignette": {"enabled": False}}),
                encoding="utf-8",
            )
            state_home = Path(state_dir)
            palette = state_home / "omarchy/current/theme/colors.toml"
            palette.parent.mkdir(parents=True)
            palette.write_text('color11 = "#aabbcc"\ncolor15 = "#ffffff"\n', encoding="utf-8")
            qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  Loader {{ id: panelLoader; source: "{qml_url('Panel.qml')}"; onLoaded: probe.start() }}
  Timer {{
    id: probe; interval: 60; repeat: true; property int attempts: 0
    onTriggered: {{
      attempts += 1
      var panel = panelLoader.item
      if (!panel || panel.mappingMode !== "none" || panel.loadedEffectCount() !== 0) {{
        if (attempts > 30) {{ console.log("BEHAVE_ERR inert panel did not settle"); Qt.quit() }}
        return
      }}
      console.log("BEHAVE " + JSON.stringify({{mappingMode: panel.mappingMode,
        loadedEffectCount: panel.loadedEffectCount(), enabled: panel.ambienceEnabled}}))
      Qt.quit()
    }}
  }}
}}
'''
            output = run_quickshell(
                qml,
                config_home=config_home,
                env_overrides={"XDG_STATE_HOME": str(state_home)},
                timeout=15,
            )
        require_no_qml_errors(output)
        row = parse_behave(output)[-1]
        self.assertEqual(row["mappingMode"], "none", output[-2000:])
        self.assertEqual(row["loadedEffectCount"], 0, output[-2000:])
        self.assertFalse(row["enabled"], output[-2000:])


if __name__ == "__main__":
    unittest.main()
