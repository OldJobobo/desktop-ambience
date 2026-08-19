import Quickshell.Io
import QtQuick

// One panel-owned cursor sampler feeds every per-output Dust Motes renderer.
// Keeping this process here prevents polling cost from multiplying by output.
Item {
  id: root

  property bool active: false
  property int pollIntervalMs: 120
  property real cursorX: -1
  property real cursorY: -1
  property real cursorVelocityX: 0
  property real cursorVelocityY: 0
  property real cursorKick: 0
  property int launchCount: 0
  property int failureCount: 0
  property string lastError: ""

  readonly property bool running: cursorProcess.running
  readonly property bool healthy: failureCount === 0 || lastError === ""

  width: 0
  height: 0
  visible: false

  function poll() {
    if (!active || cursorProcess.running) return
    cursorProcess.output = ""
    cursorProcess.command = ["hyprctl", "cursorpos", "-j"]
    launchCount += 1
    cursorProcess.running = true
  }

  function applyPayload(raw) {
    try {
      var parsed = JSON.parse(raw || "{}")
      var nextX = Number(parsed.x)
      var nextY = Number(parsed.y)
      if (isNaN(nextX) || isNaN(nextY)) throw new Error("cursor payload has no coordinates")

      if (cursorX >= 0 && cursorY >= 0) {
        var dx = nextX - cursorX
        var dy = nextY - cursorY
        var distance = Math.sqrt(dx * dx + dy * dy)
        if (distance > 0.5) {
          cursorVelocityX = Math.max(-90, Math.min(90, dx))
          cursorVelocityY = Math.max(-90, Math.min(90, dy))
          cursorKick = Math.max(cursorKick, Math.min(1, 0.35 + distance / 180))
          cursorDecayTimer.restart()
        }
      }

      cursorX = nextX
      cursorY = nextY
      lastError = ""
    } catch (error) {
      failureCount += 1
      lastError = String(error)
    }
  }

  function status() {
    return {
      active: active,
      running: running,
      healthy: healthy,
      launchCount: launchCount,
      failureCount: failureCount,
      error: lastError
    }
  }

  onActiveChanged: {
    if (active) poll()
    else cursorDecayTimer.restart()
  }

  Timer {
    interval: root.pollIntervalMs
    repeat: true
    running: root.active
    onTriggered: root.poll()
  }

  Timer {
    id: cursorDecayTimer
    interval: root.active ? 520 : 1
    repeat: false
    onTriggered: {
      root.cursorVelocityX = 0
      root.cursorVelocityY = 0
      root.cursorKick = 0
    }
  }

  Behavior on cursorVelocityX {
    NumberAnimation { duration: 360; easing.type: Easing.OutCubic }
  }

  Behavior on cursorVelocityY {
    NumberAnimation { duration: 360; easing.type: Easing.OutCubic }
  }

  Behavior on cursorKick {
    NumberAnimation { duration: 420; easing.type: Easing.OutCubic }
  }

  Process {
    id: cursorProcess

    property string output: ""

    stdout: SplitParser {
      onRead: function(data) {
        cursorProcess.output += data
      }
    }

    onExited: function(exitCode) {
      if (exitCode === 0) root.applyPayload(cursorProcess.output)
      else {
        root.failureCount += 1
        root.lastError = "hyprctl cursorpos exited with status " + exitCode
      }
    }
  }
}
