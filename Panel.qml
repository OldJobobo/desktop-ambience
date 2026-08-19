import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import QtQuick
import "components"
import "effects"

// Persistent Phase 1 host. Phase 2 replaces these in-memory defaults with the
// standalone settings owner; the renderer and surface lifecycle stay here.
Item {
  id: root
  objectName: "joboDesktopAmbienceRoot"

  property string omarchyPath: ""
  property var shell: null
  property var manifest: null

  property bool ambienceEnabled: true
  property string presentation: "background"
  property var activeEffects: ["trackingLines"]
  property bool vignetteEnabled: false
  property real vignetteIntensity: 0.85

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

  FullscreenGuard { id: fullscreenGuard }

  AmbienceStack {
    id: orderProbe
    visible: false
    width: 0
    height: 0
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
        shell: root.shell
        targetScreen: bottomWindow.modelData
        activeEffects: root.activeEffects
        foregroundOverlay: root.foregroundOverlay
        paintEnabled: root.ambienceEnabled && root.mappingMode === "bottom"
        Component.onCompleted: root.registerProductionStack(this)
        Component.onDestruction: root.unregisterProductionStack(this)
      }

      VignetteEffect {
        anchors.fill: parent
        z: 10000
        targetScreen: bottomWindow.modelData
        vignetteEnabled: root.vignetteEnabled
        vignetteIntensity: root.vignetteIntensity
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
        shell: root.shell
        targetScreen: overlayWindow.modelData
        activeEffects: root.activeEffects
        foregroundOverlay: root.foregroundOverlay
        paintEnabled: root.ambienceEnabled && root.mappingMode === "overlay"
          && !overlayWindow.fullscreenSuppressed
        Component.onCompleted: root.registerProductionStack(this)
        Component.onDestruction: root.unregisterProductionStack(this)
      }

      VignetteEffect {
        anchors.fill: parent
        z: 10000
        targetScreen: overlayWindow.modelData
        vignetteEnabled: root.vignetteEnabled
        vignetteIntensity: root.vignetteIntensity
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
        overlayRenderable: root.mappingMode === "overlay"
      })
    }
  }
}
