from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from qml_harness import HAVE_SESSION, parse_behave, qml_url, require_no_qml_errors, run_quickshell


@unittest.skipUnless(HAVE_SESSION, "needs a quickshell binary and a Wayland session")
class Phase4SettingsBehaviorTests(unittest.TestCase):
    def test_drag_only_slider_snaps_real_and_integer_values_to_declared_steps(self):
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  Loader {{
    id: slider
    source: "{qml_url('components/DragOnlySlider.qml')}"
    onLoaded: {{
      item.minimum = 0.1
      item.maximum = 1.1
      item.step = 0.25
      probe.start()
    }}
  }}
  Timer {{
    id: probe
    interval: 20
    onTriggered: {{
      var realLow = slider.item.snapValue(0.68)
      var realHigh = slider.item.snapValue(0.99)
      slider.item.minimum = 12
      slider.item.maximum = 42
      slider.item.step = 5
      slider.item.integer = true
      console.log("BEHAVE " + JSON.stringify({{
        realLow: realLow,
        realHigh: realHigh,
        integerLow: slider.item.snapValue(24),
        integerHigh: slider.item.snapValue(25)
      }}))
      Qt.quit()
    }}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as config_dir:
            output = run_quickshell(qml, config_home=Path(config_dir), timeout=10)
        require_no_qml_errors(output)
        row = parse_behave(output)[-1]
        self.assertAlmostEqual(row["realLow"], 0.6)
        self.assertAlmostEqual(row["realHigh"], 1.1)
        self.assertEqual(row["integerLow"], 22)
        self.assertEqual(row["integerHigh"], 27)

    def test_node_mesh_add_effect_metadata_and_immediate_save_are_registry_driven(self):
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  id: root
  property int requestedBefore: 0
  Loader {{ id: settingsLoader; source: "{qml_url('services/AmbienceSettings.qml')}" }}
  Loader {{ id: windowLoader; source: "{qml_url('components/SettingsWindow.qml')}" }}
  Connections {{
    target: settingsLoader.item
    function onLoaded() {{
      if (!windowLoader.item) return
      windowLoader.item.settings = settingsLoader.item
      root.requestedBefore = settingsLoader.item.requestedSaveRevision
      if (!windowLoader.item.addEffect("nodeMesh")) {{
        console.log("BEHAVE_ERR Node Mesh was not addable"); Qt.quit(); return
      }}
      windowLoader.item.setEffectField("nodeMesh", "pointerMode", "attract")
      windowLoader.item.setEffectField("nodeMesh", "nodeCount", 72)
      probe.start()
    }}
  }}
  Timer {{
    id: probe; interval: 30; repeat: true; property int attempts: 0
    onTriggered: {{
      attempts += 1
      var service = settingsLoader.item
      var window = windowLoader.item
      if (!service || service.persistenceState !== "saved"
          || service.confirmedSaveRevision !== service.requestedSaveRevision) {{
        if (attempts > 180) {{ console.log("BEHAVE_ERR Node Mesh save did not settle"); Qt.quit() }}
        return
      }}
      var fields = window.fieldsFor("nodeMesh")
      console.log("BEHAVE " + JSON.stringify({{
        activeEffects: service.data.activeEffects,
        pointerMode: service.data.effects.nodeMesh.pointerMode,
        nodeCount: service.data.effects.nodeMesh.nodeCount,
        fieldCount: fields.length,
        fieldTypes: fields.map(function(field) {{ return field.type }}),
        completeMetadata: fields.every(function(field) {{
          return field.label && field.hint && Number(field.step) > 0
        }}),
        requestedBefore: root.requestedBefore,
        requestedAfter: service.requestedSaveRevision,
        confirmedAfter: service.confirmedSaveRevision
      }}))
      Qt.quit()
    }}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as config_dir:
            config_home = Path(config_dir)
            output = run_quickshell(qml, config_home=config_home, timeout=15)
            require_no_qml_errors(output)
            row = parse_behave(output)[-1]
            disk = json.loads((config_home / "omarchy/jobo/desktop-ambience/settings.json").read_text())

        self.assertIn("nodeMesh", row["activeEffects"], output[-2000:])
        self.assertEqual(row["pointerMode"], "attract")
        self.assertEqual(row["nodeCount"], 72)
        self.assertEqual(row["fieldCount"], 13)
        self.assertEqual(set(row["fieldTypes"]), {"bool", "real", "int", "enum"})
        self.assertTrue(row["completeMetadata"])
        self.assertGreater(row["requestedAfter"], row["requestedBefore"])
        self.assertEqual(row["confirmedAfter"], row["requestedAfter"])
        self.assertEqual(disk["effects"]["nodeMesh"]["pointerMode"], "attract")
        self.assertNotIn("nodeMesh", (Path(__file__).resolve().parents[1]
                                     / "components/SettingsWindow.qml").read_text(encoding="utf-8"))

    def test_all_controls_round_trip_and_survive_service_restart(self):
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  property int stage: 0
  property int editedFieldCount: 0
  Loader {{ id: settingsLoader; source: "{qml_url('services/AmbienceSettings.qml')}" }}
  Loader {{
    id: windowLoader
    source: "{qml_url('components/SettingsWindow.qml')}"
    onLoaded: if (settingsLoader.item) item.settings = settingsLoader.item
  }}
  Connections {{
    target: settingsLoader.item
    function onLoaded() {{
      if (stage !== 0 || !windowLoader.item) return
      stage = 1
      var window = windowLoader.item
      window.settings = settingsLoader.item
      window.addEffect("filmGrain")
      window.addEffect("auroraDrift")
      window.moveEffect("auroraDrift", -1)
      window.removeEffect("trackingLines")

      var definitions = window.effectDefinitions
      for (var i = 0; i < definitions.length; i++) {{
        var id = definitions[i].id
        var fields = window.fieldsFor(id)
        for (var j = 0; j < fields.length; j++) {{
          var field = fields[j]
          var target
          if (field.type === "bool") target = true
          else if (field.type === "enum") target = field.values[field.values.length - 1]
          else {{
            target = (Number(field.minimum) + Number(field.maximum)) / 2
            if (field.type === "int") target = Math.round(target)
          }}
          if (window.setEffectField(id, field.key, target)) editedFieldCount += 1
        }}
      }}

      // Match the source interaction: changing vignette intensity enables it.
      window.setVignetteField("intensity", 0.33)
      window.setVignetteField("ignoreBackgroundAnimationLayer", true)
      window.setPresentation("foreground")
      window.setOpacity(0.42)
      window.setReduceMotion(true)
      window.setEnabled(false)
      probe.start()
    }}
  }}
  Timer {{
    id: probe; interval: 30; repeat: true; property int attempts: 0
    onTriggered: {{
      attempts += 1
      var service = settingsLoader.item
      var window = windowLoader.item
      if (!service || service.persistenceState !== "saved"
          || service.confirmedSaveRevision !== service.requestedSaveRevision) {{
        if (attempts > 180) {{ console.log("BEHAVE_ERR settings controls did not settle"); Qt.quit() }}
        return
      }}
      var allFieldsMatch = true
      var allMetadataComplete = true
      var definitions = window.effectDefinitions
      for (var i = 0; i < definitions.length; i++) {{
        var id = definitions[i].id
        var fields = window.fieldsFor(id)
        for (var j = 0; j < fields.length; j++) {{
          var field = fields[j]
          if (!field.label || !field.hint || !(Number(field.step) > 0)) allMetadataComplete = false
          var actual = service.data.effects[id][field.key]
          if (field.type === "bool" && actual !== true) allFieldsMatch = false
          else if (field.type === "enum" && actual !== field.values[field.values.length - 1]) allFieldsMatch = false
          else if (field.type !== "bool" && field.type !== "enum") {{
            var expected = (Number(field.minimum) + Number(field.maximum)) / 2
            if (field.type === "int") expected = Math.round(expected)
            if (Math.abs(Number(actual) - expected) > 0.0001) allFieldsMatch = false
          }}
        }}
      }}
      stop()
      console.log("BEHAVE " + JSON.stringify({{
        enabled: service.data.enabled,
        presentation: service.data.presentation,
        opacity: service.data.opacity,
        reduceMotion: service.data.reduceMotion,
        activeEffects: service.data.activeEffects,
        vignette: service.data.backgroundVignette,
        editedFieldCount: editedFieldCount,
        allFieldsMatch: allFieldsMatch,
        allMetadataComplete: allMetadataComplete,
        persistence: service.persistenceState
      }}))
      Qt.quit()
    }}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as config_dir:
            config_home = Path(config_dir)
            output = run_quickshell(qml, config_home=config_home, timeout=15)
            require_no_qml_errors(output)
            row = parse_behave(output)[-1]
            disk = json.loads((config_home / "omarchy/jobo/desktop-ambience/settings.json").read_text())

            restart_qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  Loader {{ id: service; source: "{qml_url('services/AmbienceSettings.qml')}" }}
  Connections {{
    target: service.item
    function onLoaded() {{
      console.log("BEHAVE " + JSON.stringify(service.item.data))
      Qt.quit()
    }}
  }}
}}
'''
            restart_output = run_quickshell(restart_qml, config_home=config_home, timeout=10)
            require_no_qml_errors(restart_output)
            restarted = parse_behave(restart_output)[-1]

        self.assertFalse(row["enabled"], output[-2000:])
        self.assertEqual(row["presentation"], "foreground", output[-2000:])
        self.assertAlmostEqual(row["opacity"], 0.42, places=4)
        self.assertTrue(row["reduceMotion"])
        self.assertEqual(row["activeEffects"], ["auroraDrift", "filmGrain"])
        self.assertEqual(row["vignette"]["enabled"], True)
        self.assertAlmostEqual(row["vignette"]["intensity"], 0.33, places=4)
        self.assertTrue(row["vignette"]["ignoreBackgroundAnimationLayer"])
        self.assertGreater(row["editedFieldCount"], 60)
        self.assertTrue(row["allFieldsMatch"], output[-2000:])
        self.assertTrue(row["allMetadataComplete"], output[-2000:])
        self.assertEqual(row["persistence"], "saved")
        self.assertEqual(disk, restarted)
        self.assertEqual(disk["activeEffects"], ["auroraDrift", "filmGrain"])

    def test_blood_mode_label_changes_on_open_and_toggle_without_repeating(self):
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  property bool ran: false
  Loader {{ id: settingsLoader; source: "{qml_url('services/AmbienceSettings.qml')}" }}
  Loader {{ id: windowLoader; source: "{qml_url('components/SettingsWindow.qml')}" }}
  Connections {{
    target: settingsLoader.item
    function onLoaded() {{
      if (ran || !windowLoader.item) return
      ran = true
      var view = windowLoader.item
      view.settings = settingsLoader.item
      var initial = view.bloodModeLabel
      view.open('{{"effect":"drip"}}')
      var opened = view.bloodModeLabel
      view.setEffectField("drip", "bloodMode", true)
      var toggled = view.bloodModeLabel
      view.close()
      view.open('{{"effect":"drip"}}')
      var reopened = view.bloodModeLabel
      var phrases = view.bloodModePhrases.slice()
      console.log("BEHAVE " + JSON.stringify({{
        initial: initial, opened: opened, toggled: toggled, reopened: reopened,
        phrases: phrases, persisted: settingsLoader.item.data.effects.drip.bloodMode,
        hint: view.fieldHintFor("drip", {{key: "bloodMode", hint: "description"}})
      }}))
      view.close()
      Qt.quit()
    }}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as config_dir:
            output = run_quickshell(qml, config_home=Path(config_dir), timeout=12)
        require_no_qml_errors(output)
        row = parse_behave(output)[-1]
        self.assertNotEqual(row["initial"], row["opened"])
        self.assertNotEqual(row["opened"], row["toggled"])
        self.assertNotEqual(row["toggled"], row["reopened"])
        self.assertIn("There Will Be Blood", row["phrases"])
        self.assertIn("Blood for the Blood God!", row["phrases"])
        self.assertIn("Fangs Out!", row["phrases"])
        self.assertIn("If It Bleeds, We Can Kill It!", row["phrases"])
        self.assertIn(row["reopened"], row["phrases"])
        self.assertEqual(row["hint"], "")
        self.assertTrue(row["persisted"])

    def test_enum_options_have_human_labels_and_stable_values(self):
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  Loader {{ id: view; source: "{qml_url('components/SettingsWindow.qml')}" }}
  Timer {{ id: probe; interval: 40; running: true; onTriggered: {{
    var fields = view.item.fieldsFor("cinematicLight")
    var style = null
    for (var i = 0; i < fields.length; i++) if (fields[i].key === "stylePreset") style = fields[i]
    var dripFields = view.item.fieldsFor("drip")
    var direction = null
    for (var j = 0; j < dripFields.length; j++) if (dripFields[j].key === "direction") direction = dripFields[j]
    console.log("BEHAVE " + JSON.stringify({{style: style.options, direction: direction.options}}))
    Qt.quit()
  }} }}
}}
'''
        with tempfile.TemporaryDirectory() as config_dir:
            output = run_quickshell(qml, config_home=Path(config_dir), timeout=10)
        require_no_qml_errors(output)
        row = parse_behave(output)[-1]
        self.assertEqual(row["style"][0], {"value": "lightLeak", "label": "Light leak"})
        self.assertEqual(row["style"][2], {"value": "anamorphicGlow", "label": "Anamorphic glow"})
        self.assertEqual(row["direction"][0], {"value": "auto", "label": "Automatic"})
        self.assertEqual(row["direction"][1], {"value": "down", "label": "Down"})

    def test_effect_reset_is_scoped_and_preview_pause_is_session_only(self):
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  property bool ran: false
  property bool pausedBeforeClose: false
  Loader {{ id: settingsLoader; source: "{qml_url('services/AmbienceSettings.qml')}" }}
  Loader {{ id: windowLoader; source: "{qml_url('components/SettingsWindow.qml')}" }}
  Connections {{
    target: settingsLoader.item
    function onLoaded() {{
      if (ran || !windowLoader.item) return
      ran = true
      var view = windowLoader.item
      view.settings = settingsLoader.item
      view.addEffect("drip")
      view.setEffectField("drip", "speed", 4)
      view.resetEffect("drip")
      view.setPreviewPaused(true)
      pausedBeforeClose = view.previewPaused
      view.close()
      probe.start()
    }}
  }}
  Timer {{
    id: probe; interval: 30; repeat: true; property int attempts: 0
    onTriggered: {{
      attempts += 1
      var service = settingsLoader.item
      if (service && service.persistenceState === "saved"
          && service.confirmedSaveRevision === service.requestedSaveRevision) {{
        stop()
        console.log("BEHAVE " + JSON.stringify({{
          activeEffects: service.data.activeEffects,
          drip: service.data.effects.drip,
          pausedBeforeClose: pausedBeforeClose,
          pausedAfterClose: windowLoader.item.previewPaused
        }}))
        Qt.quit()
      }} else if (attempts > 160) {{ console.log("BEHAVE_ERR scoped reset did not settle"); Qt.quit() }}
    }}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as config_dir:
            output = run_quickshell(qml, config_home=Path(config_dir), timeout=12)
        require_no_qml_errors(output)
        row = parse_behave(output)[-1]
        self.assertEqual(row["activeEffects"], ["trackingLines", "drip"])
        self.assertEqual(row["drip"]["speed"], 1)
        self.assertEqual(row["drip"]["dropletCount"], 28)
        self.assertTrue(row["pausedBeforeClose"])
        self.assertFalse(row["pausedAfterClose"])

    def test_reset_restores_defaults_without_touching_unrelated_file(self):
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  property int stage: 0
  Loader {{ id: settingsLoader; source: "{qml_url('services/AmbienceSettings.qml')}" }}
  Loader {{ id: windowLoader; source: "{qml_url('components/SettingsWindow.qml')}" }}
  Connections {{
    target: settingsLoader.item
    function onLoaded() {{
      if (stage !== 0 || !windowLoader.item) return
      stage = 1
      windowLoader.item.settings = settingsLoader.item
      windowLoader.item.resetAll()
      probe.start()
    }}
  }}
  Timer {{
    id: probe; interval: 30; repeat: true; property int attempts: 0
    onTriggered: {{
      attempts += 1
      var service = settingsLoader.item
      if (service && service.persistenceState === "saved"
          && service.confirmedSaveRevision === service.requestedSaveRevision) {{
        stop()
        console.log("BEHAVE " + JSON.stringify(service.data))
        Qt.quit()
      }} else if (attempts > 150) {{ console.log("BEHAVE_ERR reset did not settle"); Qt.quit() }}
    }}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as config_dir:
            config_home = Path(config_dir)
            settings_file = config_home / "omarchy/jobo/desktop-ambience/settings.json"
            settings_file.parent.mkdir(parents=True)
            settings_file.write_text(json.dumps({
                "version": 1,
                "enabled": False,
                "presentation": "foreground",
                "opacity": 0.12,
                "activeEffects": ["filmGrain", "crt"],
                "backgroundVignette": {"enabled": True, "intensity": 0.2},
            }), encoding="utf-8")
            unrelated = config_home / "omarchy/unrelated.json"
            unrelated.parent.mkdir(parents=True, exist_ok=True)
            unrelated.write_text('{"keep":true}\n', encoding="utf-8")

            output = run_quickshell(qml, config_home=config_home, timeout=12)
            require_no_qml_errors(output)
            row = parse_behave(output)[-1]
            disk = json.loads(settings_file.read_text())
            unrelated_text = unrelated.read_text()

        self.assertTrue(row["enabled"], output[-2000:])
        self.assertEqual(row["presentation"], "background")
        self.assertEqual(row["opacity"], 1)
        self.assertEqual(row["activeEffects"], ["trackingLines"])
        self.assertFalse(row["backgroundVignette"]["enabled"])
        self.assertEqual(row["effects"]["nodeMesh"]["nodeCount"], 54)
        self.assertEqual(row["effects"]["nodeMesh"]["pointerMode"], "off")
        self.assertEqual(disk, row)
        self.assertEqual(unrelated_text, '{"keep":true}\n')


if __name__ == "__main__":
    unittest.main()
