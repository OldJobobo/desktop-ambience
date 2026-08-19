import tempfile
import unittest
from pathlib import Path

from qml_harness import HAVE_SESSION, parse_behave, qml_url, require_no_qml_errors, run_quickshell


@unittest.skipUnless(HAVE_SESSION, "needs a quickshell binary and a Wayland session")
class ThemeAdapterBehaviorTests(unittest.TestCase):
    def test_native_roles_extended_fallback_and_bounded_last_valid_retry(self):
        with tempfile.TemporaryDirectory() as state_dir, tempfile.TemporaryDirectory() as config_dir:
            state_home = Path(state_dir)
            palette = state_home / "omarchy/current/theme/colors.toml"
            palette.parent.mkdir(parents=True)
            palette.write_text('color11 = "#aabbcc"\ncolor15 = "#f0f1f2"\n', encoding="utf-8")
            missing = state_home / "missing/colors.toml"
            missing.parent.mkdir(parents=True)

            qml = f'''
import Quickshell
import Quickshell.Io
import QtQuick
import qs.Commons

ShellRoot {{
  Loader {{
    id: adapterLoader
    source: "{qml_url('services/ThemeAdapter.qml')}"
    onLoaded: probe.restart()
  }}
  FileView {{
    id: recoveryWriter
    path: "{missing}"
    atomicWrites: true
    onSaved: recoveryProbe.restart()
  }}

  Timer {{
    id: probe
    interval: 120
    repeat: true
    property int attempts: 0
    onTriggered: {{
      attempts += 1
      var adapter = adapterLoader.item
      if (!adapter || adapter.readState !== "ready") {{
        if (attempts > 20) {{ console.log("BEHAVE_ERR initial palette did not load"); Qt.quit() }}
        return
      }}
      stop()
      var initial = {{
        nativeBackground: String(adapter.background),
        colorBackground: String(Color.background),
        nativeForeground: String(adapter.foreground),
        colorForeground: String(Color.foreground),
        nativeAccent: String(adapter.accent),
        colorAccent: String(Color.accent),
        extended: String(adapter.colorFor("color11", "#000000")),
        fallback: String(adapter.colorFor("color12", "#112233"))
      }}
      host.initial = initial
      adapter.maximumRetries = 2
      adapter.retryDelayMs = 25
      adapter.colorsPath = "{missing}"
      adapter.scheduleReload(true)
      failedProbe.restart()
    }}
  }}

  QtObject {{
    id: host
    property var initial: ({{}})
    property int failedRetryCount: 0
    property string retained: ""
  }}

  Timer {{
    id: failedProbe
    interval: 50
    repeat: true
    property int attempts: 0
    onTriggered: {{
      attempts += 1
      var adapter = adapterLoader.item
      if (adapter.readState !== "failed") {{
        if (attempts > 20) {{ console.log("BEHAVE_ERR retry did not stop"); Qt.quit() }}
        return
      }}
      stop()
      host.failedRetryCount = adapter.retryCount
      host.retained = String(adapter.colorFor("color11", "#000000"))
      recoveryWriter.setText('color11 = "#334455"\\ncolor12 = "#778899"\\n')
    }}
  }}

  Timer {{
    id: recoveryProbe
    interval: 40
    repeat: true
    property int attempts: 0
    onTriggered: {{
      attempts += 1
      var adapter = adapterLoader.item
      if (adapter.readState !== "ready" || String(adapter.colorFor("color11", "#000000")).toLowerCase() !== "#334455") {{
        if (attempts > 30) {{ console.log("BEHAVE_ERR watched palette did not recover"); Qt.quit() }}
        return
      }}
      stop()
      console.log("BEHAVE " + JSON.stringify({{
        initial: host.initial,
        readState: adapter.readState,
        retryCountAtFailure: host.failedRetryCount,
        retryCount: adapter.retryCount,
        retryPending: adapter.retryPending,
        retainedAtFailure: host.retained,
        rebound: String(adapter.colorFor("color11", "#000000")),
        ready: adapter.ready,
        extendedReady: adapter.extendedReady
      }}))
      Qt.quit()
    }}
  }}
}}
'''
            output = run_quickshell(
                qml,
                timeout=10,
                config_home=Path(config_dir),
                env_overrides={"XDG_STATE_HOME": str(state_home)},
            )
        require_no_qml_errors(output)
        row = parse_behave(output)[-1]
        initial = row["initial"]
        self.assertEqual(initial["nativeBackground"], initial["colorBackground"])
        self.assertEqual(initial["nativeForeground"], initial["colorForeground"])
        self.assertEqual(initial["nativeAccent"], initial["colorAccent"])
        self.assertEqual(initial["extended"].lower(), "#aabbcc")
        self.assertEqual(initial["fallback"].lower(), "#112233")
        self.assertEqual(row["readState"], "ready")
        self.assertEqual(row["retryCountAtFailure"], 2)
        self.assertEqual(row["retryCount"], 0)
        self.assertFalse(row["retryPending"])
        self.assertEqual(row["retainedAtFailure"].lower(), "#aabbcc")
        self.assertEqual(row["rebound"].lower(), "#334455")
        self.assertTrue(row["ready"])
        self.assertTrue(row["extendedReady"])


    def test_invalid_relative_or_missing_state_base_fails_closed(self):
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  Loader {{ id: adapterLoader; source: "{qml_url('services/ThemeAdapter.qml')}" }}
  Timer {{
    interval: 100; running: adapterLoader.item !== null
    onTriggered: {{
      console.log("BEHAVE " + JSON.stringify({{
        stateHome: adapterLoader.item.stateHome,
        colorsPath: adapterLoader.item.colorsPath,
        pathReady: adapterLoader.item.pathReady,
        ready: adapterLoader.item.ready,
        readState: adapterLoader.item.readState,
        readError: adapterLoader.item.readError
      }}))
      Qt.quit()
    }}
  }}
}}
'''
        for xdg_home in ("relative/state", ""):
            with self.subTest(xdg_home=xdg_home), tempfile.TemporaryDirectory() as config_dir:
                output = run_quickshell(
                    qml,
                    config_home=Path(config_dir),
                    env_overrides={"XDG_STATE_HOME": xdg_home, "HOME": ""},
                    timeout=10,
                )
                require_no_qml_errors(output)
                row = parse_behave(output)[-1]
                self.assertEqual(row["stateHome"], "")
                self.assertEqual(row["colorsPath"], "")
                self.assertFalse(row["pathReady"])
                self.assertFalse(row["ready"])
                self.assertEqual(row["readState"], "failed")
                self.assertTrue(row["readError"])


def test_theme_adapter_native_change_and_watcher_contract():
    text = (Path(__file__).resolve().parents[1] / "services/ThemeAdapter.qml").read_text(encoding="utf-8")
    assert "readonly property color background: Color.background" in text
    assert "readonly property color foreground: Color.foreground" in text
    assert "readonly property color accent: Color.accent" in text
    assert "function onBackgroundChanged()" in text
    assert "function onForegroundChanged()" in text
    assert "function onAccentChanged()" in text
    assert text.count("property FileView") == 1
    assert "maximumRetries" in text
    assert "lastValidExtendedPalette" in text


if __name__ == "__main__":
    unittest.main()
