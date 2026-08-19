import Quickshell.Hyprland
import QtQuick

Item {
  id: root

  // Injectable for deterministic per-output behavior tests; production uses
  // Quickshell's Hyprland singleton.
  property var backend: Hyprland
  property int revision: 0

  visible: false
  width: 0
  height: 0

  function workspaceHasFullscreen(workspace) {
    if (!workspace) return false
    if (workspace.hasFullscreen === true) return true
    var ipc = workspace.lastIpcObject || {}
    return ipc.hasfullscreen === true
      || ipc.hasFullscreen === true
      || Number(ipc.fullscreen || 0) > 0
  }

  function activeWorkspaceForScreen(screen) {
    root.revision
    var service = root.backend
    var monitor = service && service.monitorFor ? service.monitorFor(screen) : null
    if (monitor && monitor.activeWorkspace) return monitor.activeWorkspace
    return !screen && service ? (service.focusedWorkspace || null) : null
  }

  function activeOnScreen(screen) {
    return workspaceHasFullscreen(activeWorkspaceForScreen(screen))
  }

  function refresh() {
    var service = root.backend
    if (service && service.refreshWorkspaces) service.refreshWorkspaces()
    if (service && service.refreshToplevels) service.refreshToplevels()
    root.revision += 1
  }

  Timer {
    id: refreshTimer
    interval: 40
    repeat: false
    onTriggered: root.refresh()
  }

  Connections {
    target: root.backend
    ignoreUnknownSignals: true

    function onRawEvent(event) {
      var name = String(event && event.name || "")
      if (name === "fullscreen" || name.indexOf("workspace") >= 0
          || name.indexOf("window") >= 0 || name === "focusedmon")
        refreshTimer.restart()
    }

    function onFocusedWorkspaceChanged() {
      root.revision += 1
    }
  }

  Connections {
    target: root.backend && root.backend.workspaces ? root.backend.workspaces : null
    ignoreUnknownSignals: true

    function onValuesChanged() {
      root.revision += 1
    }
  }
}
