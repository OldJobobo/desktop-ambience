import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import QtQuick
import "components"
import "effects"
import "services"

// Persistent host. One settings owner and one theme adapter feed every output;
// the interim dual-surface lifecycle remains until Phase 3.
Item {
  id: root
  objectName: "joboDesktopAmbienceRoot"

  property string omarchyPath: ""
  property var manifest: null

  readonly property bool ambienceEnabled: ambienceSettings.enabled
  readonly property string presentation: ambienceSettings.presentation
  readonly property var activeEffects: ambienceSettings.activeEffects
  readonly property var backgroundVignette: ambienceSettings.backgroundVignette
  readonly property bool vignetteEnabled: backgroundVignette.enabled === true
  readonly property real vignetteIntensity: Number(backgroundVignette.intensity)
  readonly property bool vignetteBehindEffects: backgroundVignette.ignoreBackgroundAnimationLayer === true

  // Panel lifecycle seam reserved for the on-demand Phase 4 settings window.
  property bool opened: false
  function open(payloadJson) { opened = true }
  function close() { opened = false }

  property var productionStacks: []
  readonly property bool hostReady: true
  readonly property bool foregroundOverlay: presentation === "foreground"
  readonly property bool visualSurfaceEnabled: ambienceEnabled || vignetteEnabled
  readonly property string mappingMode: !visualSurfaceEnabled
    ? "none" : (foregroundOverlay ? "overlay" : "bottom")

  function normalizedOrder() {
    return orderProbe.normalizeActiveEffects(activeEffects)
  }

  function registerProductionStack(stack) {
    if (productionStacks.indexOf(stack) < 0) productionStacks.push(stack)
  }

  function unregisterProductionStack(stack) {
    var index = productionStacks.indexOf(stack)
    if (index >= 0) productionStacks.splice(index, 1)
  }

  function loadedEffectCount() {
    var count = 0
    for (var i = 0; i < productionStacks.length; i++) {
      var stack = productionStacks[i]
      if (stack) count += Number(stack.activeProductionEffectCount || 0)
    }
    return count
  }

  function zMap() {
    var result = {}
    var order = normalizedOrder()
    for (var i = 0; i < order.length; i++) result[order[i]] = orderProbe.zForEffect(order[i])
    return result
  }

  AmbienceSettings { id: ambienceSettings }
  ThemeAdapter { id: themeAdapter }
  FullscreenGuard { id: fullscreenGuard }

  AmbienceStack {
    id: orderProbe
    visible: false
    width: 0
    height: 0
    settings: ambienceSettings
    theme: themeAdapter
    activeEffects: root.activeEffects
    paintEnabled: false
    productionEffectsEnabled: false
  }

  Variants {
    model: Quickshell.screens

    PanelWindow {
      id: bottomWindow
      objectName: "joboDesktopAmbienceBottomSurface"
      required property var modelData

      screen: modelData
      visible: root.mappingMode === "bottom"
      color: "transparent"
      WlrLayershell.namespace: "jobo-desktop-ambience-bottom"
      WlrLayershell.layer: WlrLayer.Bottom
      WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
      exclusionMode: ExclusionMode.Ignore
      mask: Region {}

      anchors {
        top: true
        bottom: true
        left: true
        right: true
      }

      AmbienceStack {
        anchors.fill: parent
        targetScreen: bottomWindow.modelData
        settings: ambienceSettings
        theme: themeAdapter
        activeEffects: root.activeEffects
        foregroundOverlay: root.foregroundOverlay
        paintEnabled: root.ambienceEnabled && root.mappingMode === "bottom"
        Component.onCompleted: root.registerProductionStack(this)
        Component.onDestruction: root.unregisterProductionStack(this)
      }

      VignetteEffect {
        anchors.fill: parent
        z: root.vignetteBehindEffects ? -10000 : 10000
        targetScreen: bottomWindow.modelData
        settings: root.backgroundVignette
        paintEnabled: root.mappingMode === "bottom"
      }
    }
  }

  Variants {
    model: Quickshell.screens

    PanelWindow {
      id: overlayWindow
      objectName: "joboDesktopAmbienceOverlaySurface"
      required property var modelData
      readonly property bool fullscreenSuppressed: fullscreenGuard.activeOnScreen(modelData)

      screen: modelData
      // Foreground presentation is visual-only and may paint above shell UI.
      visible: root.mappingMode === "overlay"
      color: "transparent"
      WlrLayershell.namespace: "jobo-desktop-ambience-overlay"
      WlrLayershell.layer: WlrLayer.Overlay
      WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
      exclusionMode: ExclusionMode.Ignore
      mask: Region {}

      anchors {
        top: true
        bottom: true
        left: true
        right: true
      }

      AmbienceStack {
        anchors.fill: parent
        targetScreen: overlayWindow.modelData
        settings: ambienceSettings
        theme: themeAdapter
        activeEffects: root.activeEffects
        foregroundOverlay: root.foregroundOverlay
        paintEnabled: root.ambienceEnabled && root.mappingMode === "overlay"
          && !overlayWindow.fullscreenSuppressed
        Component.onCompleted: root.registerProductionStack(this)
        Component.onDestruction: root.unregisterProductionStack(this)
      }

      VignetteEffect {
        anchors.fill: parent
        z: root.vignetteBehindEffects ? -10000 : 10000
        targetScreen: overlayWindow.modelData
        settings: root.backgroundVignette
        paintEnabled: root.mappingMode === "overlay" && !overlayWindow.fullscreenSuppressed
      }
    }
  }

  IpcHandler {
    target: "jobo-desktop-ambience"

    function status(): string {
      return JSON.stringify({
        enabled: root.ambienceEnabled,
        presentation: root.presentation,
        activeEffects: root.normalizedOrder(),
        vignetteEnabled: root.vignetteEnabled,
        vignetteIntensity: root.vignetteIntensity,
        loadedEffectCount: root.loadedEffectCount(),
        mappingMode: root.mappingMode,
        mappedSurfaceCount: root.mappingMode === "none" ? 0 : Quickshell.screens.length,
        z: root.zMap(),
        bottomRenderable: root.mappingMode === "bottom",
        overlayRenderable: root.mappingMode === "overlay",
        persistence: {
          ready: ambienceSettings.persistenceReady,
          state: ambienceSettings.persistenceState,
          error: ambienceSettings.persistenceError,
          loadError: ambienceSettings.loadError,
          diskDiverged: ambienceSettings.diskDiverged,
          recoveredFromMalformedEdit: ambienceSettings.recoveredFromMalformedEdit,
          retryAvailable: ambienceSettings.retryAvailable,
          requestedRevision: ambienceSettings.requestedSaveRevision,
          confirmedRevision: ambienceSettings.confirmedSaveRevision
        },
        theme: themeAdapter.status()
      })
    }
  }
}
