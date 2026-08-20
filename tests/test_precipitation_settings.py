from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from qml_harness import HAVE_SESSION, parse_behave, qml_url, require_no_qml_errors, run_quickshell


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def field_keys(fields: list[dict]) -> list[str]:
    return [str(field["key"]) for field in fields]


def write_settings(config_home: Path, document: dict) -> Path:
    settings_file = config_home / "omarchy/jobo/desktop-ambience/settings.json"
    settings_file.parent.mkdir(parents=True)
    settings_file.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return settings_file


def initial_document() -> dict:
    return {
        "version": 1,
        "enabled": True,
        "presentation": "foreground",
        "opacity": 0.77,
        "reduceMotion": False,
        "activeEffects": ["rainfall", "filmGrain"],
        "effects": {
            "rainfall": {
                "enabled": True,
                "intensity": 0.61,
                "speed": 0.73,
                "precipitationStyle": "rain",
                "dropCount": 177,
                "slant": -0.11,
                "accentBlend": 0.31,
                "vignette": False,
                "mistAmount": 0.17,
                "splashAmount": 0.23,
                "flakeSize": 14,
                "flutterAmount": 0.71,
                "flakeDetail": "crystal",
                "futurePrecipitation": {"hail": [1, None, False]},
            },
            "filmGrain": {"enabled": True, "intensity": 0.19, "speed": 1.3,
                          "grainCount": 91, "grainSize": 1.7, "accentBlend": 0.27},
        },
        "backgroundVignette": {"enabled": False, "intensity": 0.2,
                               "ignoreBackgroundAnimationLayer": False},
        "futureRoot": {"safe": True},
    }


def test_registry_declares_compatible_precipitation_schema_and_json_safe_conditions():
    registry = read("services/EffectRegistry.js")
    rainfall = registry.split('id: "rainfall", label: "Rainfall"', 1)[1].split("\n  },", 1)[0]
    for token in (
        'precipitationStyle: enumField("rain", ["rain", "snow"])',
        'dropCount: intField(180, 16, 320)',
        'flakeSize: conditionalField(realField(6, 2, 18), "precipitationStyle", ["snow"])',
        'flutterAmount: conditionalField(realField(0.58, 0, 1), "precipitationStyle", ["snow"])',
        'flakeDetail: conditionalField(enumField("mixed", ["soft", "crystal", "mixed"])',
        'mistAmount: conditionalField(realField(0.34, 0, 1), "precipitationStyle", ["rain"])',
        'splashAmount: conditionalField(realField(0.38, 0, 1), "precipitationStyle", ["rain"])',
    ):
        assert token in rainfall
    assert 'dropCount: "Precipitation Count"' in registry
    assert 'visibleWhen = { field: String(conditionField || ""), values: values.slice() }' in registry
    assert "var field = deepCopy(entry.fields[key])" in registry


def test_settings_visibility_is_generic_and_loader_lifecycle_uses_it():
    window = read("components/SettingsWindow.qml")
    assert "function fieldIsVisible(effectId, field)" in window
    assert "function visibleFieldsFor(effectId)" in window
    assert "condition.values.indexOf" in window
    assert "visible: root.fieldIsVisible(root.selectedEffectId, modelData)" in window
    assert "active: visible" in window
    assert "rainfall" not in window.lower()


@unittest.skipUnless(HAVE_SESSION, "needs a quickshell binary and a Wayland session")
class PrecipitationSettingsBehaviorTests(unittest.TestCase):
    def test_style_visibility_switches_immediately_and_hidden_values_persist(self):
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  id: root
  property int stage: 0
  property var rainKeys: []
  property var immediateSnowKeys: []
  property var immediateRainKeys: []
  Loader {{ id: settingsLoader; source: "{qml_url('services/AmbienceSettings.qml')}" }}
  Loader {{ id: windowLoader; source: "{qml_url('components/SettingsWindow.qml')}" }}
  Connections {{
    target: settingsLoader.item
    function onLoaded() {{
      if (root.stage !== 0 || !windowLoader.item) return
      root.stage = 1
      var window = windowLoader.item
      window.settings = settingsLoader.item
      window.selectedEffectId = "rainfall"
      root.rainKeys = window.visibleFieldsFor("rainfall").map(function(field) {{ return field.key }})
      window.setEffectField("rainfall", "precipitationStyle", "snow")
      root.immediateSnowKeys = window.visibleFieldsFor("rainfall").map(function(field) {{ return field.key }})
      settle.start()
    }}
  }}
  Timer {{
    id: settle; interval: 25; repeat: true; property int attempts: 0
    onTriggered: {{
      attempts += 1
      var service = settingsLoader.item
      var window = windowLoader.item
      if (!service || service.persistenceState !== "saved"
          || service.confirmedSaveRevision !== service.requestedSaveRevision) {{
        if (attempts > 240) {{ console.log("BEHAVE_ERR precipitation settings did not settle"); Qt.quit() }}
        return
      }}
      var rain = service.data.effects.rainfall
      if (root.stage === 1 && rain.precipitationStyle === "snow") {{
        root.stage = 2
        window.setEffectField("rainfall", "flakeSize", 15)
        window.setEffectField("rainfall", "flutterAmount", 0.82)
        window.setEffectField("rainfall", "flakeDetail", "soft")
        return
      }}
      if (root.stage === 2 && rain.flakeSize === 15
          && Math.abs(rain.flutterAmount - 0.82) < 0.001 && rain.flakeDetail === "soft") {{
        root.stage = 3
        window.setEffectField("rainfall", "precipitationStyle", "rain")
        root.immediateRainKeys = window.visibleFieldsFor("rainfall").map(function(field) {{ return field.key }})
        return
      }}
      if (root.stage !== 3 || rain.precipitationStyle !== "rain") return
      stop()
      var definitions = window.fieldsFor("rainfall")
      console.log("BEHAVE " + JSON.stringify({{
        rainKeys: root.rainKeys,
        immediateSnowKeys: root.immediateSnowKeys,
        immediateRainKeys: root.immediateRainKeys,
        metadata: definitions,
        version: service.data.version,
        activeEffects: service.data.activeEffects,
        rainfall: rain,
        filmGrain: service.data.effects.filmGrain,
        futureRoot: service.data.futureRoot
      }}))
      Qt.quit()
    }}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as config_dir:
            config_home = Path(config_dir)
            settings_file = write_settings(config_home, initial_document())
            output = run_quickshell(qml, config_home=config_home, timeout=15)
            require_no_qml_errors(output)
            row = parse_behave(output)[-1]
            disk = json.loads(settings_file.read_text(encoding="utf-8"))

            restart_qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  Loader {{ id: service; source: "{qml_url('services/AmbienceSettings.qml')}" }}
  Connections {{
    target: service.item
    function onLoaded() {{ console.log("BEHAVE " + JSON.stringify(service.item.data)); Qt.quit() }}
  }}
}}
'''
            restart_output = run_quickshell(restart_qml, config_home=config_home, timeout=10)
            require_no_qml_errors(restart_output)
            restarted = parse_behave(restart_output)[-1]

        shared = {"enabled", "intensity", "speed", "precipitationStyle", "dropCount",
                  "slant", "accentBlend", "vignette"}
        self.assertEqual(set(row["rainKeys"]), shared | {"mistAmount", "splashAmount"})
        self.assertEqual(set(row["immediateSnowKeys"]),
                         shared | {"flakeSize", "flutterAmount", "flakeDetail"})
        self.assertEqual(set(row["immediateRainKeys"]), shared | {"mistAmount", "splashAmount"})

        metadata = {field["key"]: field for field in row["metadata"]}
        self.assertEqual(len(metadata), 13)
        self.assertEqual(metadata["dropCount"]["label"], "Precipitation Count")
        self.assertEqual(metadata["mistAmount"]["visibleWhen"],
                         {"field": "precipitationStyle", "values": ["rain"]})
        self.assertEqual(metadata["flakeDetail"]["visibleWhen"],
                         {"field": "precipitationStyle", "values": ["snow"]})
        self.assertTrue(all(field["label"] and field["hint"] for field in metadata.values()))

        self.assertEqual(row["version"], 1)
        self.assertEqual(row["activeEffects"], ["rainfall", "filmGrain"])
        self.assertEqual(row["rainfall"]["precipitationStyle"], "rain")
        self.assertEqual(row["rainfall"]["mistAmount"], 0.17)
        self.assertEqual(row["rainfall"]["splashAmount"], 0.23)
        self.assertEqual(row["rainfall"]["flakeSize"], 15)
        self.assertAlmostEqual(row["rainfall"]["flutterAmount"], 0.82, places=3)
        self.assertEqual(row["rainfall"]["flakeDetail"], "soft")
        self.assertEqual(row["rainfall"]["futurePrecipitation"], {"hail": [1, None, False]})
        self.assertEqual(row["filmGrain"]["grainCount"], 91)
        self.assertEqual(row["futureRoot"], {"safe": True})
        self.assertEqual(disk, restarted)
        self.assertEqual(disk["effects"]["rainfall"], row["rainfall"])

    def test_reset_restores_rain_and_snow_defaults(self):
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  id: root
  property bool requested: false
  Loader {{ id: settingsLoader; source: "{qml_url('services/AmbienceSettings.qml')}" }}
  Loader {{ id: windowLoader; source: "{qml_url('components/SettingsWindow.qml')}" }}
  Connections {{
    target: settingsLoader.item
    function onLoaded() {{
      if (root.requested || !windowLoader.item) return
      root.requested = true
      windowLoader.item.settings = settingsLoader.item
      windowLoader.item.resetAll()
      probe.start()
    }}
  }}
  Timer {{
    id: probe; interval: 25; repeat: true; property int attempts: 0
    onTriggered: {{
      attempts += 1
      var service = settingsLoader.item
      if (service && service.persistenceState === "saved"
          && service.confirmedSaveRevision === service.requestedSaveRevision) {{
        stop()
        console.log("BEHAVE " + JSON.stringify(service.data))
        Qt.quit()
      }} else if (attempts > 200) {{ console.log("BEHAVE_ERR reset did not settle"); Qt.quit() }}
    }}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as config_dir:
            config_home = Path(config_dir)
            settings_file = write_settings(config_home, initial_document())
            output = run_quickshell(qml, config_home=config_home, timeout=15)
            require_no_qml_errors(output)
            row = parse_behave(output)[-1]
            disk = json.loads(settings_file.read_text(encoding="utf-8"))

        rain = row["effects"]["rainfall"]
        self.assertEqual(rain, {
            "enabled": True, "intensity": 0.72, "speed": 0.62,
            "precipitationStyle": "rain", "dropCount": 180, "slant": 0.08,
            "accentBlend": 0.42, "vignette": True, "mistAmount": 0.34,
            "splashAmount": 0.38, "flakeSize": 6, "flutterAmount": 0.58,
            "flakeDetail": "mixed",
        })
        self.assertEqual(row["version"], 1)
        self.assertEqual(row["activeEffects"], ["trackingLines"])
        self.assertEqual(disk, row)
