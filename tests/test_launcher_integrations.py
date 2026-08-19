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
    assert manifest["version"] == "0.4.0-rc.1"
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
    assert 'tooltipText: "Desktop Ambience · "' in widget
    assert "LauncherIcons.glyphFor" in widget
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
        assert parsed["desktop-ambience"]["icon"] == "󰗘"


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
        command: fakeBar.command, iconId: widget.item.iconId, iconGlyph: widget.item.iconGlyph,
        width: widget.item.implicitWidth, height: widget.item.implicitHeight}}))
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
        self.assertEqual(row["iconId"], "animation")
        self.assertEqual(row["iconGlyph"], "󰗘")
        self.assertGreater(row["width"], 0)
        self.assertGreater(row["height"], 0)

    def test_settings_icon_picker_persists_inline_state_and_updates_widget(self):
        qml = f'''\nimport Quickshell\nimport QtQuick\nShellRoot {{\n  QtObject {{\n    id: fakeShell\n    property var shellConfig: ({{bar: {{layout: {{\n      left: [], center: [], right: [{{id: "jobo.desktop-ambience", other: 7}}]\n    }}}}}})\n    function mutateShellConfig(mutate) {{\n      var copy = JSON.parse(JSON.stringify(shellConfig))\n      mutate(copy)\n      shellConfig = copy\n    }}\n    function hide(pluginId) {{}}\n  }}\n  QtObject {{\n    id: fakeBar\n    property bool vertical: false\n    property int barSize: 28\n    property color barForeground: "white"\n    property color urgent: "red"\n    property string fontFamily: "monospace"\n    property bool foregroundAnimationEnabled: false\n    function run(value) {{}}\n    function showTooltip(item, text) {{}}\n    function hideTooltip(item) {{}}\n    function registerClickTarget(item) {{}}\n    function unregisterClickTarget(item) {{}}\n  }}\n  Loader {{ id: settingsView; source: "{qml_url('components/SettingsWindow.qml')}" }}\n  Loader {{ id: widget; source: "{qml_url('BarWidget.qml')}" }}\n  Timer {{\n    interval: 40; running: true\n    onTriggered: {{\n      settingsView.item.shell = fakeShell\n      widget.item.bar = fakeBar\n      var choices = settingsView.item.launcherIcons\n      var allChanged = true\n      for (var i = 0; i < choices.length; i++)\n        if (!settingsView.item.setBarIcon(choices[i].id)) allChanged = false\n      var entry = fakeShell.shellConfig.bar.layout.right[0]\n      widget.item.settings = {{icon: entry.icon, other: entry.other}}\n      console.log("BEHAVE " + JSON.stringify({{\n        count: choices.length,\n        ids: choices.map(function(choice) {{ return choice.id }}),\n        allChanged: allChanged,\n        selected: settingsView.item.barIconId,\n        persisted: entry.icon,\n        preserved: entry.other,\n        noNestedSettings: entry.settings === undefined,\n        widgetIcon: widget.item.iconId,\n        widgetGlyph: widget.item.iconGlyph\n      }}))\n      Qt.quit()\n    }}\n  }}\n}}\n'''
        with tempfile.TemporaryDirectory() as config_home:
            output = run_quickshell(qml, config_home=Path(config_home), timeout=10)
        require_no_qml_errors(output)
        row = parse_behave(output)[-1]
        self.assertEqual(row["count"], 8, output[-2000:])
        self.assertEqual(row["ids"][0], "animation")
        self.assertEqual(
            row["ids"],
            ["animation", "tune", "blur", "magicStaff", "palette", "monitorEye", "vintageFilter", "autoFix"],
        )
        self.assertTrue(row["allChanged"], output[-2000:])
        self.assertEqual(row["selected"], "autoFix")
        self.assertEqual(row["persisted"], "autoFix")
        self.assertEqual(row["preserved"], 7)
        self.assertTrue(row["noNestedSettings"])
        self.assertEqual(row["widgetIcon"], "autoFix")
        self.assertEqual(row["widgetGlyph"], "󰁨")
