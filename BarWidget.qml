import QtQuick
import qs.Ui
import "services/LauncherIcons.js" as LauncherIcons

// Lightweight launcher only. The persistent panel entry point continues to own
// settings, surfaces, services, and IPC.
BarWidget {
  id: root
  moduleName: "jobo.desktop-ambience"
  readonly property string iconId: LauncherIcons.normalize(root.setting("icon", LauncherIcons.DEFAULT_ID))
  readonly property string iconGlyph: LauncherIcons.glyphFor(iconId)

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  function openSettings() {
    if (root.bar) root.bar.run("omarchy-shell shell toggle jobo.desktop-ambience '{}'")
  }

  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: root.iconGlyph
    tooltipText: "Desktop Ambience"
    horizontalMargin: 7.5

    onPressed: function(button) {
      if (button === Qt.LeftButton) root.openSettings()
    }
  }
}
