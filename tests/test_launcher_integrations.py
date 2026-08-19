from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from qml_harness import HAVE_SESSION, parse_behave, qml_url, require_no_qml_errors, run_quickshell


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/menu-entry.sh"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def run_menu_script(home: Path, action: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["HOME"] = str(home)
    return subprocess.run(
        [str(SCRIPT), action],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=check,
    )


def test_manifest_contributes_panel_and_single_bar_widget():
    manifest = json.loads(read("manifest.json"))
    assert manifest["version"] == "0.2.0"
    assert manifest["kinds"] == ["panel", "bar-widget"]
    assert manifest["entryPoints"] == {"panel": "Panel.qml", "barWidget": "BarWidget.qml"}
    assert manifest["barWidget"] == {
        "displayName": "Desktop Ambience",
        "description": "Open the ambience composition and effect settings",
        "category": "Compositor",
        "defaultSection": "right",
        "allowMultiple": False,
    }


def test_bar_widget_is_a_launcher_without_duplicate_runtime_ownership():
    widget = read("BarWidget.qml")
    assert 'moduleName: "jobo.desktop-ambience"' in widget
    assert 'tooltipText: "Desktop Ambience"' in widget
    assert "function openSettings()" in widget
    assert "omarchy-shell shell toggle jobo.desktop-ambience '{}'" in widget
    assert "AmbienceSettings" not in widget
    assert "ThemeAdapter" not in widget
    assert "PanelWindow" not in widget
    assert "IpcHandler" not in widget
    assert "FileView" not in widget


def test_menu_entry_install_is_idempotent_preserves_existing_content_and_removes_cleanly():
    with tempfile.TemporaryDirectory() as directory:
        home = Path(directory)
        menu = home / ".config/omarchy/extensions/omarchy-menu.jsonc"
        menu.parent.mkdir(parents=True)
        original = '{\n  "personal.notes": {"label":"Notes","action":"true"}\n}\n'
        menu.write_text(original, encoding="utf-8")

        first = run_menu_script(home, "install")
        second = run_menu_script(home, "install")
        installed = menu.read_text(encoding="utf-8")
        status = run_menu_script(home, "status")

        assert "Installed Desktop Ambience" in first.stdout
        assert "Installed Desktop Ambience" in second.stdout
        assert status.stdout.strip() == "installed"
        assert installed.count("jobo-desktop-ambience-menu-start") == 1
        assert installed.count('"desktop-ambience"') == 1
        assert '"personal.notes"' in installed
        assert "omarchy-shell shell summon jobo.desktop-ambience '{}'" in installed

        removed = run_menu_script(home, "remove")
        cleaned = menu.read_text(encoding="utf-8")
        assert "Removed Desktop Ambience" in removed.stdout
        assert "jobo-desktop-ambience-menu" not in cleaned
        assert '"personal.notes"' in cleaned
        assert run_menu_script(home, "status", check=False).returncode == 1


def test_menu_entry_install_handles_a_new_empty_extension_file():
    with tempfile.TemporaryDirectory() as directory:
        home = Path(directory)
        run_menu_script(home, "install")
        menu = home / ".config/omarchy/extensions/omarchy-menu.jsonc"
        installed = menu.read_text(encoding="utf-8")
        without_comments = "\n".join(
            line for line in installed.splitlines() if not line.lstrip().startswith("//")
        )
        parsed = json.loads(without_comments)
        assert parsed["desktop-ambience"]["label"] == "Desktop Ambience"


@unittest.skipUnless(HAVE_SESSION, "needs a quickshell binary and a Wayland session")
class BarWidgetBehaviorTests(unittest.TestCase):
    def test_bar_launcher_routes_to_the_persistent_panel(self):
        qml = f'''
import Quickshell
import QtQuick
ShellRoot {{
  QtObject {{
    id: fakeBar
    property bool vertical: false
    property int barSize: 28
    property color barForeground: "white"
    property color urgent: "red"
    property string fontFamily: "monospace"
    property bool foregroundAnimationEnabled: false
    property string command: ""
    function run(value) {{ command = value }}
    function showTooltip(item, text) {{}}
    function hideTooltip(item) {{}}
    function registerClickTarget(item) {{}}
    function unregisterClickTarget(item) {{}}
  }}
  Loader {{
    id: widget
    source: "{qml_url('BarWidget.qml')}"
    onLoaded: {{ item.bar = fakeBar; probe.start() }}
  }}
  Timer {{
    id: probe; interval: 40
    onTriggered: {{
      widget.item.openSettings()
      console.log("BEHAVE " + JSON.stringify({{moduleName: widget.item.moduleName,
        command: fakeBar.command, width: widget.item.implicitWidth, height: widget.item.implicitHeight}}))
      Qt.quit()
    }}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as config_home:
            output = run_quickshell(qml, config_home=Path(config_home), timeout=10)
        require_no_qml_errors(output)
        row = parse_behave(output)[-1]
        self.assertEqual(row["moduleName"], "jobo.desktop-ambience", output[-2000:])
        self.assertEqual(
            row["command"],
            "omarchy-shell shell toggle jobo.desktop-ambience '{}'",
            output[-2000:],
        )
        self.assertGreater(row["width"], 0)
        self.assertGreater(row["height"], 0)
