import Quickshell
import QtQuick
import qs.Commons
import qs.Ui

// Phase 3 owns the singleton window lifecycle. Phase 4 replaces this minimal
// shell with the extracted settings controls.
Item {
  id: root

  property var settings: null
  property var shell: null
  property string pluginId: "jobo.desktop-ambience"
  property bool closingFromHost: false
  property bool closeReportingReady: false
  readonly property bool opened: window.visible

  function open(payloadJson) {
    window.visible = true
    Qt.callLater(function() { focusScope.forceActiveFocus() })
  }

  function close() {
    closingFromHost = true
    window.visible = false
    closingFromHost = false
  }

  function requestClose() {
    if (shell && typeof shell.hide === "function") shell.hide(pluginId)
    else window.visible = false
  }

  Component.onCompleted: Qt.callLater(function() { closeReportingReady = true })

  FloatingWindow {
    id: window
    visible: false
    title: "Desktop Ambience"
    color: Color.background
    implicitWidth: 480
    implicitHeight: 280
    minimumSize: Qt.size(360, 220)

    onVisibleChanged: {
      if (!visible && root.closeReportingReady && !root.closingFromHost
          && root.shell && typeof root.shell.hide === "function")
        root.shell.hide(root.pluginId)
    }

    FocusScope {
      id: focusScope
      anchors.fill: parent
      focus: true

      Keys.onEscapePressed: root.requestClose()

      Column {
        anchors.centerIn: parent
        width: Math.min(360, parent.width - 48)
        spacing: 12

        Text {
          width: parent.width
          text: "Desktop Ambience"
          color: Color.foreground
          font.family: Style.font.family
          font.pixelSize: Style.font.title
          font.bold: true
          horizontalAlignment: Text.AlignHCenter
        }

        Text {
          width: parent.width
          text: "The settings surface is ready. Effect controls arrive in the next extraction phase."
          color: Color.foreground
          opacity: 0.7
          font.family: Style.font.family
          font.pixelSize: Style.font.body
          horizontalAlignment: Text.AlignHCenter
          wrapMode: Text.WordWrap
        }
      }
    }
  }
}
