from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from qml_harness import HAVE_SESSION, parse_behave, qml_url, require_no_qml_errors, run_quickshell

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def qml_json(value: object) -> str:
    return json.dumps(json.dumps(value, separators=(",", ":")))


def normalize_probe(*values: object) -> list[dict]:
    calls = ",".join(f"serviceLoader.item.normalize(JSON.parse({qml_json(value)}))" for value in values)
    qml = f"""
import Quickshell
import QtQuick
ShellRoot {{
  Loader {{ id: serviceLoader; source: "{qml_url('services/AmbienceSettings.qml')}" }}
  Timer {{
    interval: 80
    running: serviceLoader.item !== null
    onTriggered: {{
      console.log("BEHAVE " + JSON.stringify([{calls}]))
      Qt.quit()
    }}
  }}
}}
"""
    with tempfile.TemporaryDirectory() as tmp:
        output = run_quickshell(qml, config_home=Path(tmp), timeout=10)
    require_no_qml_errors(output)
    return parse_behave(output)[-1]


def test_static_settings_owner_contract():
    settings = read("services/AmbienceSettings.qml")
    registry = read("services/EffectRegistry.js")
    assert 'configHome + "/omarchy/jobo/desktop-ambience"' in settings
    assert 'settingsDir + "/settings.json"' in settings
    assert 'resolveBasePath("XDG_CONFIG_HOME", "/.config")' in settings
    assert "readonly property bool pathReady" in settings
    assert "atomicWrites: true" in settings
    assert "watchChanges: true" in settings
    assert 'persistenceState: "idle"' in settings
    assert "requestedSaveRevision" in settings
    assert "confirmedSaveRevision" in settings
    assert "queuedSavePayload" in settings
    assert "retrySavePayload" in settings
    assert "directoryFailed" in settings
    assert "diskDiverged" in settings
    assert "retryPersistence" in settings
    assert '["mkdir", "-p", root.settingsDir]' in settings
    assert "hasLoaded ? lastValidData : normalize(data)" in settings
    assert "const effects" not in registry
    assert "var orderedEffects" in registry
    assert "var dedicatedVignette" in registry
    for forbidden in ("/omarchy/lacuna", "lacuna.", "lacuna-"):
        assert forbidden not in settings.lower()
        assert forbidden not in registry.lower()
    assert 'id: "vhs"' not in registry


@unittest.skipUnless(HAVE_SESSION, "needs a quickshell binary and a Wayland session")
class AmbienceSettingsBehaviorTests(unittest.TestCase):
    def test_defaults_bounds_unknown_fields_and_order(self):
        high = {
            "version": 99,
            "enabled": False,
            "presentation": "invalid",
            "opacity": 9,
            "reduceMotion": True,
            "activeEffects": ["vhs", "filmGrain", "filmGrain", "futureGlow", "backgroundVignette", "trackingLines", "bogus"],
            "effects": {
                "auroraDrift": {"intensity": 9, "speed": 9, "ribbonCount": 99, "blurSoftness": 9, "accentBlend": 9, "future": {"ok": True}},
                "cinematicLight": {"stylePreset": "bad", "slowDrift": False, "occasionalSweeps": False, "activeShimmer": False, "flareCount": 99},
                "crt": {"scanlineSpacing": 99, "staticBandHeight": 999, "bloomPulseInterval": 999999},
                "dustMotes": {"moteCount": 999, "moteSize": 99, "mouseInfluence": 9},
                "filmGrain": {"speed": 99, "grainCount": 999, "grainSize": 99},
                "godRays": {"rayCount": 99, "raySpread": 9, "origin": "bad"},
                "rainfall": {"dropCount": 999, "slant": 9},
                "trackingLines": {"lineSpacing": 99, "trackingBands": 99},
                "vhs": {"enabled": True},
                "backgroundVignette": {"enabled": True},
                "futureGlow": {"enabled": True, "amount": 0.37, "nested": [1, None, False]},
            },
            "backgroundVignette": {"enabled": True, "intensity": 9, "futureVignette": [1, None]},
            "futureRoot": {"safe": [1, True, None]},
        }
        low = {
            "activeEffects": [],
            "effects": {
                "auroraDrift": {"speed": -9, "ribbonCount": -9},
                "cinematicLight": {"intensity": -9, "flareCount": -9},
                "crt": {"scanlineSpacing": -9, "staticBandHeight": -9, "bloomPulseInterval": -9},
                "dustMotes": {"moteCount": -9, "moteSize": -9},
                "filmGrain": {"speed": -9, "grainCount": -9, "grainSize": -9},
                "godRays": {"rayCount": -9, "raySpread": -9, "origin": "bottom-right"},
                "rainfall": {"dropCount": -9, "slant": -9},
                "trackingLines": {"lineSpacing": -9, "trackingBands": -9},
            },
            "backgroundVignette": {"intensity": -9},
        }
        defaults, upper, lower = normalize_probe({}, high, low)
        self.assertEqual(defaults["version"], 1)
        self.assertTrue(defaults["enabled"])
        self.assertEqual(defaults["presentation"], "background")
        self.assertEqual(defaults["activeEffects"], ["trackingLines"])
        self.assertEqual(set(defaults["effects"]), {"auroraDrift", "cinematicLight", "crt", "dustMotes", "filmGrain", "godRays", "rainfall", "trackingLines"})
        self.assertEqual(defaults["effects"]["trackingLines"]["trackingBands"], 4)
        self.assertFalse(defaults["backgroundVignette"]["enabled"])
        self.assertEqual(defaults["backgroundVignette"]["intensity"], 0.85)

        self.assertFalse(upper["enabled"])
        self.assertEqual(upper["presentation"], "background")
        self.assertEqual(upper["opacity"], 1)
        self.assertEqual(upper["activeEffects"], ["filmGrain", "trackingLines"])
        self.assertNotIn("vhs", upper["effects"])
        self.assertNotIn("backgroundVignette", upper["effects"])
        self.assertNotIn("futureGlow", upper["activeEffects"])
        self.assertEqual(upper["effects"]["futureGlow"], {"enabled": True, "amount": 0.37, "nested": [1, None, False]})
        self.assertEqual(upper["effects"]["auroraDrift"]["ribbonCount"], 9)
        self.assertEqual(upper["effects"]["cinematicLight"]["stylePreset"], "lightLeak")
        self.assertTrue(upper["effects"]["cinematicLight"]["slowDrift"])
        self.assertEqual(upper["effects"]["crt"]["bloomPulseInterval"], 60000)
        self.assertEqual(upper["effects"]["dustMotes"]["moteCount"], 180)
        self.assertEqual(upper["effects"]["filmGrain"]["grainCount"], 520)
        self.assertEqual(upper["effects"]["godRays"]["origin"], "top-left")
        self.assertEqual(upper["effects"]["rainfall"]["slant"], 0.35)
        self.assertEqual(upper["effects"]["trackingLines"]["trackingBands"], 7)
        self.assertEqual(upper["effects"]["auroraDrift"]["future"], {"ok": True})
        self.assertEqual(upper["backgroundVignette"]["futureVignette"], [1, None])
        self.assertEqual(upper["futureRoot"], {"safe": [1, True, None]})

        self.assertEqual(lower["activeEffects"], [])
        self.assertEqual(lower["effects"]["auroraDrift"]["ribbonCount"], 1)
        self.assertEqual(lower["effects"]["cinematicLight"]["flareCount"], 1)
        self.assertEqual(lower["effects"]["crt"]["bloomPulseInterval"], 7000)
        self.assertEqual(lower["effects"]["dustMotes"]["moteCount"], 12)
        self.assertEqual(lower["effects"]["filmGrain"]["grainCount"], 32)
        self.assertEqual(lower["effects"]["godRays"]["origin"], "bottom-right")
        self.assertEqual(lower["effects"]["rainfall"]["slant"], -0.2)
        self.assertEqual(lower["effects"]["trackingLines"]["trackingBands"], 0)
        self.assertEqual(lower["backgroundVignette"]["intensity"], 0)

    def test_latest_write_and_malformed_edit_are_repaired_on_disk(self):
        qml = f'''
import Quickshell
import Quickshell.Io
import QtQuick
ShellRoot {{
  property int stage: 0
  property string retainedError: ""
  Loader {{ id: serviceLoader; source: "{qml_url('services/AmbienceSettings.qml')}" }}
  FileView {{
    id: externalWriter
    path: serviceLoader.item ? serviceLoader.item.settingsFile : ""
    atomicWrites: true
    onSaved: malformedProbe.restart()
  }}
  Connections {{
    target: serviceLoader.item
    function onLoaded() {{
      if (stage !== 0) return
      stage = 1
      var first = serviceLoader.item.normalize(serviceLoader.item.data); first.opacity = 0.2
      var second = serviceLoader.item.normalize(first); second.opacity = 0.4
      var third = serviceLoader.item.normalize(second); third.opacity = 0.6
      serviceLoader.item.save(first)
      serviceLoader.item.save(second)
      serviceLoader.item.save(third)
      saveProbe.start()
    }}
  }}
  Timer {{
    id: saveProbe; interval: 25; repeat: true
    onTriggered: {{
      var service = serviceLoader.item
      if (service.persistenceState !== "saved" || service.confirmedSaveRevision !== service.requestedSaveRevision) return
      stop()
      externalWriter.setText("{{broken")
    }}
  }}
  Timer {{
    id: malformedProbe; interval: 120
    onTriggered: {{
      serviceLoader.item.load()
      repairProbe.start()
    }}
  }}
  Timer {{
    id: repairProbe; interval: 25; repeat: true
    onTriggered: {{
      var service = serviceLoader.item
      if (!service.recoveredFromMalformedEdit || !service.diskDiverged) return
      stop()
      retainedError = service.loadError
      stage = 2
      service.save(service.data)
      finalProbe.start()
    }}
  }}
  Timer {{
    id: finalProbe; interval: 25; repeat: true
    onTriggered: {{
      var service = serviceLoader.item
      if (service.persistenceState !== "saved"
          || service.confirmedSaveRevision !== service.requestedSaveRevision
          || service.diskDiverged) return
      stop()
      console.log("BEHAVE " + JSON.stringify({{
        opacity: service.data.opacity,
        requested: service.requestedSaveRevision,
        confirmed: service.confirmedSaveRevision,
        state: service.persistenceState,
        malformed: service.recoveredFromMalformedEdit,
        error: retainedError,
        settingsFile: service.settingsFile
      }}))
      Qt.quit()
    }}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as tmp:
            config_home = Path(tmp)
            output = run_quickshell(qml, config_home=config_home, timeout=15)
            require_no_qml_errors(output)
            row = parse_behave(output)[-1]
            disk = json.loads((config_home / "omarchy/jobo/desktop-ambience/settings.json").read_text())
            self.assertEqual(row["opacity"], 0.6, output[-2000:])
            self.assertEqual(row["requested"], 4, output[-2000:])
            self.assertEqual(row["confirmed"], 4, output[-2000:])
            self.assertEqual(row["state"], "saved", output[-2000:])
            # A successful repair may trigger a valid self-reload before this
            # probe, clearing the transient recoveredFromMalformedEdit flag.
            self.assertTrue(row["error"], output[-2000:])
            self.assertEqual(disk["opacity"], 0.6, output[-2000:])
            self.assertEqual(row["settingsFile"], str(config_home / "omarchy/jobo/desktop-ambience/settings.json"))

    def test_failed_write_retry_cannot_resurrect_superseded_payload(self):
        qml = f'''
import Quickshell
import Quickshell.Io
import QtQuick
ShellRoot {{
  property int stage: 0
  property bool sawFailure: false
  property bool staleRetryAccepted: true
  Loader {{ id: serviceLoader; source: "{qml_url('services/AmbienceSettings.qml')}" }}
  Connections {{
    target: serviceLoader.item
    function onLoaded() {{
      if (stage !== 0) return
      stage = 1
      serviceLoader.item.save(serviceLoader.item.data)
      stateProbe.start()
    }}
  }}
  Process {{
    id: lockDirectory
    command: ["chmod", "500", serviceLoader.item ? serviceLoader.item.settingsDir : ""]
    onExited: {{
      var failedIntent = serviceLoader.item.normalize(serviceLoader.item.data)
      failedIntent.opacity = 0.4
      stage = 2
      serviceLoader.item.save(failedIntent)
    }}
  }}
  Process {{
    id: unlockDirectory
    command: ["chmod", "700", serviceLoader.item ? serviceLoader.item.settingsDir : ""]
    onExited: {{
      var newestIntent = serviceLoader.item.normalize(serviceLoader.item.data)
      newestIntent.opacity = 1
      serviceLoader.item.save(newestIntent)
      staleRetryAccepted = serviceLoader.item.retryPersistence()
      stage = 4
    }}
  }}
  Timer {{
    id: stateProbe; interval: 25; repeat: true
    onTriggered: {{
      var service = serviceLoader.item
      if (stage === 1 && service.persistenceState === "saved") {{
        stage = 10
        lockDirectory.running = true
      }} else if (stage === 2 && service.persistenceState === "failed" && service.retryAvailable) {{
        sawFailure = true
        stage = 3
        unlockDirectory.running = true
      }} else if (stage === 4 && service.persistenceState === "saved"
                 && service.confirmedSaveRevision === service.requestedSaveRevision) {{
        stop()
        console.log("BEHAVE " + JSON.stringify({{
          sawFailure: sawFailure,
          staleRetryAccepted: staleRetryAccepted,
          retryAvailable: service.retryAvailable,
          opacity: service.data.opacity,
          requested: service.requestedSaveRevision,
          confirmed: service.confirmedSaveRevision
        }}))
        Qt.quit()
      }}
    }}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as tmp:
            config_home = Path(tmp)
            output = run_quickshell(qml, config_home=config_home, timeout=15)
            require_no_qml_errors(output)
            row = parse_behave(output)[-1]
            disk = json.loads((config_home / "omarchy/jobo/desktop-ambience/settings.json").read_text())
        self.assertTrue(row["sawFailure"], output[-2000:])
        self.assertFalse(row["staleRetryAccepted"], output[-2000:])
        self.assertFalse(row["retryAvailable"], output[-2000:])
        self.assertEqual(row["opacity"], 1, output[-2000:])
        self.assertEqual(disk["opacity"], 1, output[-2000:])
        self.assertEqual(row["requested"], row["confirmed"], output[-2000:])

    def test_same_payload_save_after_failure_forces_write_and_settles(self):
        qml = f'''
import Quickshell
import Quickshell.Io
import QtQuick
ShellRoot {{
  property int stage: 0
  property bool sawFailure: false
  Loader {{ id: serviceLoader; source: "{qml_url('services/AmbienceSettings.qml')}" }}
  Connections {{
    target: serviceLoader.item
    function onLoaded() {{ if (stage === 0) {{ stage = 1; serviceLoader.item.save(serviceLoader.item.data); probe.start() }} }}
  }}
  Process {{
    id: lockDirectory
    command: ["chmod", "500", serviceLoader.item ? serviceLoader.item.settingsDir : ""]
    onExited: {{
      var intent = serviceLoader.item.normalize(serviceLoader.item.data)
      intent.opacity = 0.37
      stage = 2
      serviceLoader.item.save(intent)
    }}
  }}
  Process {{
    id: unlockDirectory
    command: ["chmod", "700", serviceLoader.item ? serviceLoader.item.settingsDir : ""]
    onExited: {{ stage = 3; serviceLoader.item.save(serviceLoader.item.data) }}
  }}
  Timer {{
    id: probe; interval: 25; repeat: true
    onTriggered: {{
      var service = serviceLoader.item
      if (stage === 1 && service.persistenceState === "saved") {{ stage = 10; lockDirectory.running = true }}
      else if (stage === 2 && service.persistenceState === "failed") {{ sawFailure = true; unlockDirectory.running = true }}
      else if (stage === 3 && service.persistenceState === "saved"
               && service.confirmedSaveRevision === service.requestedSaveRevision) {{
        stop()
        console.log("BEHAVE " + JSON.stringify({{
          sawFailure: sawFailure, state: service.persistenceState,
          retryAvailable: service.retryAvailable, requested: service.requestedSaveRevision,
          confirmed: service.confirmedSaveRevision, opacity: service.data.opacity
        }}))
        Qt.quit()
      }}
    }}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as tmp:
            config_home = Path(tmp)
            output = run_quickshell(qml, config_home=config_home, timeout=15)
            require_no_qml_errors(output)
            row = parse_behave(output)[-1]
            disk = json.loads((config_home / "omarchy/jobo/desktop-ambience/settings.json").read_text())
        self.assertTrue(row["sawFailure"], output[-2000:])
        self.assertEqual(row["state"], "saved", output[-2000:])
        self.assertFalse(row["retryAvailable"], output[-2000:])
        self.assertEqual(row["requested"], row["confirmed"], output[-2000:])
        self.assertEqual(row["opacity"], 0.37, output[-2000:])
        self.assertEqual(disk["opacity"], 0.37, output[-2000:])

    def test_pending_save_resolves_before_loaded_callback_newer_intent(self):
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  property bool queued: false
  Loader {{
    id: serviceLoader
    source: "{qml_url('services/AmbienceSettings.qml')}"
    onLoaded: {{
      queued = true
      var older = item.normalize(item.data)
      older.opacity = 0.2
      item.save(older)
    }}
  }}
  Connections {{
    target: serviceLoader.item
    function onLoaded() {{
      var newest = serviceLoader.item.normalize(serviceLoader.item.data)
      newest.opacity = 0.8
      serviceLoader.item.save(newest)
      probe.start()
    }}
  }}
  Timer {{
    id: probe; interval: 25; repeat: true
    onTriggered: {{
      var service = serviceLoader.item
      if (service.persistenceState !== "saved" || service.confirmedSaveRevision !== service.requestedSaveRevision) return
      stop()
      console.log("BEHAVE " + JSON.stringify({{opacity: service.data.opacity,
        requested: service.requestedSaveRevision, confirmed: service.confirmedSaveRevision}}))
      Qt.quit()
    }}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as tmp:
            config_home = Path(tmp)
            output = run_quickshell(qml, config_home=config_home, timeout=15)
            require_no_qml_errors(output)
            row = parse_behave(output)[-1]
            disk = json.loads((config_home / "omarchy/jobo/desktop-ambience/settings.json").read_text())
        self.assertEqual(row["opacity"], 0.8, output[-2000:])
        self.assertEqual(disk["opacity"], 0.8, output[-2000:])
        self.assertEqual(row["requested"], row["confirmed"], output[-2000:])

    def test_watcher_observes_empty_then_valid_atomic_edits_without_manual_load(self):
        qml = f'''
import Quickshell
import Quickshell.Io
import QtQuick
ShellRoot {{
  property int stage: 0
  property string malformedError: ""
  Loader {{ id: serviceLoader; source: "{qml_url('services/AmbienceSettings.qml')}" }}
  FileView {{
    id: writer
    path: serviceLoader.item ? serviceLoader.item.settingsFile : ""
    atomicWrites: true
    onSaved: if (stage === 2) stage = 3; else if (stage === 5) stage = 6
  }}
  Connections {{
    target: serviceLoader.item
    function onLoaded() {{ if (stage === 0) {{
      stage = 1
      var initial = serviceLoader.item.normalize(serviceLoader.item.data); initial.opacity = 0.6
      serviceLoader.item.save(initial); probe.start()
    }} }}
  }}
  Timer {{
    id: probe; interval: 25; repeat: true
    onTriggered: {{
      var service = serviceLoader.item
      if (stage === 1 && service.persistenceState === "saved") {{ stage = 2; writer.setText("   \\n") }}
      else if (stage === 3 && service.recoveredFromMalformedEdit && service.diskDiverged) {{
        malformedError = service.loadError
        stage = 4
        service.save(service.data)
      }} else if (stage === 4 && service.persistenceState === "saved" && !service.diskDiverged) {{
        var external = service.normalize(service.data); external.opacity = 0.73
        stage = 5; writer.setText(JSON.stringify(external, null, 2) + "\\n")
      }} else if (stage === 6 && service.data.opacity === 0.73 && !service.diskDiverged) {{
        stop()
        console.log("BEHAVE " + JSON.stringify({{opacity: service.data.opacity,
          malformedError: malformedError, recovered: service.recoveredFromMalformedEdit,
          suppression: service.suppressFileReloads}}))
        Qt.quit()
      }}
    }}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as tmp:
            config_home = Path(tmp)
            output = run_quickshell(qml, config_home=config_home, timeout=15)
            require_no_qml_errors(output)
            row = parse_behave(output)[-1]
            disk = json.loads((config_home / "omarchy/jobo/desktop-ambience/settings.json").read_text())
        self.assertEqual(row["opacity"], 0.73, output[-2000:])
        self.assertTrue(row["malformedError"], output[-2000:])
        self.assertFalse(row["recovered"], output[-2000:])
        self.assertEqual(row["suppression"], 0, output[-2000:])
        self.assertEqual(disk["opacity"], 0.73, output[-2000:])

    def test_reserved_object_keys_round_trip_without_prototype_pollution(self):
        source = json.loads('''{
          "activeEffects": ["__proto__", "trackingLines"],
          "effects": {
            "__proto__": {"enabled": true, "amount": 0.2},
            "constructor": {"enabled": true, "nested": {"prototype": "kept"}},
            "prototype": {"value": 7},
            "vhs": {"enabled": true},
            "backgroundVignette": {"enabled": true}
          },
          "__proto__": {"root": "kept"},
          "constructor": {"root": "also-kept"},
          "prototype": [1, 2]
        }''')
        first = normalize_probe(source)[0]
        second = normalize_probe(first)[0]
        # A second pass must not materialize inherited properties as fields.
        self.assertEqual(first, second)
        self.assertEqual(first["activeEffects"], ["trackingLines"])
        self.assertEqual(first["__proto__"], {"root": "kept"})
        self.assertEqual(first["constructor"], {"root": "also-kept"})
        self.assertEqual(first["prototype"], [1, 2])
        self.assertEqual(first["effects"]["__proto__"]["amount"], 0.2)
        self.assertEqual(first["effects"]["constructor"]["nested"]["prototype"], "kept")
        self.assertEqual(first["effects"]["prototype"], {"value": 7})
        self.assertNotIn("vhs", first["effects"])
        self.assertNotIn("backgroundVignette", first["effects"])

    def test_invalid_relative_or_missing_config_base_fails_closed(self):
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  Loader {{ id: serviceLoader; source: "{qml_url('services/AmbienceSettings.qml')}" }}
  Timer {{
    interval: 80; running: serviceLoader.item !== null
    onTriggered: {{
      console.log("BEHAVE " + JSON.stringify({{
        configHome: serviceLoader.item.configHome,
        settingsDir: serviceLoader.item.settingsDir,
        settingsFile: serviceLoader.item.settingsFile,
        directoryReady: serviceLoader.item.directoryReady,
        directoryFailed: serviceLoader.item.directoryFailed,
        state: serviceLoader.item.persistenceState,
        processRunning: serviceLoader.item.ensureDirectoryProcess.running
      }}))
      Qt.quit()
    }}
  }}
}}
'''
        for xdg_home in ("relative/config", ""):
            with self.subTest(xdg_home=xdg_home), tempfile.TemporaryDirectory() as tmp:
                output = run_quickshell(
                    qml,
                    config_home=Path(tmp),
                    env_overrides={"XDG_CONFIG_HOME": xdg_home, "HOME": ""},
                    timeout=10,
                )
                require_no_qml_errors(output)
                row = parse_behave(output)[-1]
                self.assertEqual(row["configHome"], "")
                self.assertEqual(row["settingsDir"], "")
                self.assertEqual(row["settingsFile"], "")
                self.assertFalse(row["directoryReady"])
                self.assertTrue(row["directoryFailed"])
                self.assertEqual(row["state"], "failed")
                self.assertFalse(row["processRunning"])

    def test_directory_creation_failure_is_visible_and_retryable(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_home = Path(tmp)
            (config_home / "omarchy").write_text("blocks directory creation", encoding="utf-8")
            qml = f'''
import Quickshell
import Quickshell.Io
import QtQuick
ShellRoot {{
  property int stage: 0
  property bool failureVisible: false
  property bool retryAccepted: false
  property bool missingUnconfirmed: false
  Loader {{ id: serviceLoader; source: "{qml_url('services/AmbienceSettings.qml')}" }}
  Process {{
    id: removeBlocker
    command: ["rm", "-f", serviceLoader.item ? serviceLoader.item.configHome + "/omarchy" : ""]
    onExited: {{
      retryAccepted = serviceLoader.item.retryPersistence()
      stage = 2
    }}
  }}
  Timer {{
    interval: 25; repeat: true; running: true
    onTriggered: {{
      var service = serviceLoader.item
      if (!service) return
      if (stage === 0 && service.directoryFailed && service.persistenceState === "failed" && service.retryAvailable) {{
        failureVisible = service.persistenceError !== ""
        stage = 1
        removeBlocker.running = true
      }} else if (stage === 2 && service.hasLoaded && service.directoryReady) {{
        missingUnconfirmed = service.lastConfirmedSavePayload === ""
          && service.requestedSaveRevision === 0
          && service.confirmedSaveRevision === 0
          && service.diskDiverged
        stop()
        console.log("BEHAVE " + JSON.stringify({{
          failureVisible: failureVisible,
          retryAccepted: retryAccepted,
          retryAvailable: service.retryAvailable,
          directoryReady: service.directoryReady,
          missingUnconfirmed: missingUnconfirmed,
          state: service.persistenceState,
          requested: service.requestedSaveRevision,
          confirmed: service.confirmedSaveRevision
        }}))
        Qt.quit()
      }}
    }}
  }}
}}
'''
            output = run_quickshell(qml, config_home=config_home, timeout=15)
            require_no_qml_errors(output)
            row = parse_behave(output)[-1]
            settings_file = config_home / "omarchy/jobo/desktop-ambience/settings.json"
        self.assertTrue(row["failureVisible"], output[-2000:])
        self.assertTrue(row["retryAccepted"], output[-2000:])
        self.assertFalse(row["retryAvailable"], output[-2000:])
        self.assertTrue(row["directoryReady"], output[-2000:])
        self.assertTrue(row["missingUnconfirmed"], output[-2000:])
        self.assertEqual(row["state"], "idle", output[-2000:])
        self.assertEqual(row["requested"], row["confirmed"], output[-2000:])
        self.assertFalse(settings_file.exists(), output[-2000:])


if __name__ == "__main__":
    unittest.main()
