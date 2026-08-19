import Quickshell
import Quickshell.Io
import QtQuick
import qs.Commons

// Shared theme seam for every renderer. Native structural roles stay bound to
// Omarchy's Color singleton; only extended Base16 roles come from colors.toml.
QtObject {
  id: root

  property string stateHome: resolveBasePath("XDG_STATE_HOME", "/.local/state")
  property string colorsPath: stateHome !== ""
    ? stateHome + "/omarchy/current/theme/colors.toml" : ""
  property int maximumRetries: 4
  property int retryDelayMs: 120

  property var extendedPalette: ({})
  property var lastValidExtendedPalette: ({})
  property int retryCount: 0
  property int nativeRevision: 0
  property int paletteRevision: 0
  property string readState: "loading"
  property string readError: ""

  readonly property color background: Color.background
  readonly property color foreground: Color.foreground
  readonly property color accent: Color.accent
  readonly property bool extendedReady: Object.keys(lastValidExtendedPalette).length > 0
  // Native roles are typed color bindings supplied by Omarchy's Color singleton.
  readonly property bool nativeReady: true
  readonly property bool ready: nativeReady && readState === "ready"
  readonly property bool retryPending: retryTimer.running
  readonly property bool pathReady: isAbsolutePath(colorsPath)

  function isAbsolutePath(value) {
    var path = String(value || "").trim()
    return path.length > 1 && path.charAt(0) === "/"
  }

  function resolveBasePath(environmentName, homeSuffix) {
    var explicitPath = String(Quickshell.env(environmentName) || "").trim()
    if (explicitPath !== "") return isAbsolutePath(explicitPath) ? explicitPath : ""
    var home = String(Quickshell.env("HOME") || "").trim()
    return isAbsolutePath(home) ? home + homeSuffix : ""
  }

  function parseExtendedPalette(raw) {
    var next = {}
    var lines = String(raw || "").split(/\n/)
    for (var i = 0; i < lines.length; i++) {
      var match = lines[i].match(/^\s*([A-Za-z0-9_-]+)\s*=\s*["']?([^"'\s]+)["']?/)
      if (!match || !/^color(?:[0-9]|1[0-5])$/.test(match[1])) continue
      var value = String(match[2] || "").trim()
      if (value !== "") next[match[1]] = value
    }
    return next
  }

  function applyPaletteText(raw) {
    var next = parseExtendedPalette(raw)
    if (Object.keys(next).length === 0) {
      handleReadFailure("theme palette contains no Base16 colors")
      return false
    }
    extendedPalette = next
    lastValidExtendedPalette = next
    retryCount = 0
    readState = "ready"
    readError = ""
    paletteRevision += 1
    retryTimer.stop()
    return true
  }

  function handleReadFailure(error) {
    // Never clear the last valid palette while Omarchy atomically replaces the
    // current-theme path.
    extendedPalette = lastValidExtendedPalette
    readError = String(error || "could not read extended theme palette")
    if (retryCount < Math.max(0, maximumRetries)) {
      retryCount += 1
      readState = "retrying"
      retryTimer.restart()
    } else {
      readState = "failed"
      retryTimer.stop()
    }
  }

  function scheduleReload(resetRetries) {
    if (resetRetries === true) retryCount = 0
    if (!pathReady) {
      retryTimer.stop()
      reloadDebounce.stop()
      readState = "failed"
      readError = "Theme palette requires an absolute XDG_STATE_HOME or HOME"
      return
    }
    readState = "loading"
    reloadDebounce.restart()
  }

  function colorFor(name, fallbackColor) {
    var role = String(name || "")
    if (role === "background" || role === "bg") return background
    if (role === "foreground" || role === "fg") return foreground
    if (role === "accent") return accent
    var palette = extendedPalette && typeof extendedPalette === "object" ? extendedPalette : ({})
    return palette[role] !== undefined ? palette[role] : fallbackColor
  }

  function status() {
    return {
      ready: ready,
      nativeReady: nativeReady,
      extendedReady: extendedReady,
      readState: readState,
      retryCount: retryCount,
      retryPending: retryPending,
      readError: readError,
      nativeRevision: nativeRevision,
      paletteRevision: paletteRevision,
      colorsPath: colorsPath
    }
  }

  property Connections nativeThemeConnections: Connections {
    target: Color
    ignoreUnknownSignals: true
    function changed() {
      root.nativeRevision += 1
      root.scheduleReload(true)
    }
    function onBackgroundChanged() { changed() }
    function onForegroundChanged() { changed() }
    function onAccentChanged() { changed() }
    function onShellValuesChanged() { changed() }
  }

  property Timer reloadDebounce: Timer {
    interval: 40
    repeat: false
    onTriggered: paletteFile.reload()
  }

  property Timer retryTimer: Timer {
    interval: Math.max(1, root.retryDelayMs)
    repeat: false
    onTriggered: paletteFile.reload()
  }

  Component.onCompleted: scheduleReload(true)

  property FileView paletteFile: FileView {
    id: paletteFile
    path: root.pathReady ? root.colorsPath : ""
    watchChanges: true
    printErrors: false
    onLoaded: root.applyPaletteText(text())
    onFileChanged: if (root.pathReady) root.scheduleReload(true)
    onLoadFailed: if (root.pathReady) root.handleReadFailure("could not read " + root.colorsPath)
  }
}
