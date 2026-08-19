import QtQuick
import qs.Ui

// Lightweight launcher only. The persistent panel entry point continues to own
// settings, surfaces, services, and IPC.
BarWidget {
  id: root
  moduleName: "jobo.desktop-ambience"

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  function openSettings() {
    if (root.bar) root.bar.run("omarchy-shell shell toggle jobo.desktop-ambience '{}'")
  }

  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: "󰖔"
    tooltipText: "Desktop Ambience"
    horizontalMargin: 7.5

    onPressed: function(button) {
      if (button === Qt.LeftButton) root.openSettings()
    }
  }
}
