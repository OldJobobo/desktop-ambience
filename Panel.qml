import QtQuick
import "components"
import "services"

// Persistent plugin root. Rendering and persistence are intentionally inert
// until the extraction phases described in PLAN.md bring in the owned source.
Item {
  id: root

  property var shell: null
  readonly property bool opened: settingsWindow.opened

  function open(payloadJson) {
    settingsWindow.open(payloadJson)
  }

  function close() {
    settingsWindow.close()
  }

  AmbienceSettings {
    id: ambienceSettings
  }

  ThemeAdapter {
    id: themeAdapter
  }

  AmbienceStack {
    id: ambienceStack
    settings: ambienceSettings
    theme: themeAdapter
  }

  SettingsWindow {
    id: settingsWindow
    settings: ambienceSettings
  }
}
