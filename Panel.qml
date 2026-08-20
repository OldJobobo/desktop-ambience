import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import QtQuick
import qs.Ui
import "components"
import "effects"
import "services"

// Persistent host. One settings owner and one theme adapter feed one
// dynamically layered, click-through ambience surface per output.
Item {
  id: root
  objectName: "joboDesktopAmbienceRoot"

  property string omarchyPath: ""
  property var manifest: null
  property var shell: null

  readonly property var settingsService: ambienceSettings
  readonly property var themeService: themeAdapter
  readonly property var fullscreenService: fullscreenGuard
  readonly property bool ambienceEnabled: ambienceSettings.enabled
  readonly property string presentation: ambienceSettings.presentation
  readonly property var activeEffects: ambienceSettings.activeEffects
  readonly property var backgroundVignette: ambienceSettings.backgroundVignette
  readonly property bool vignetteEnabled: backgroundVignette.enabled === true
  readonly property real vignetteIntensity: Number(backgroundVignette.intensity)
  readonly property bool vignetteBehindEffects: backgroundVignette.ignoreBackgroundAnimationLayer === true
  readonly property bool opened: settingsWindow.opened
  readonly property string pluginVersion: String(root.manifest && root.manifest.version || "")
  readonly property bool hostReady: true
  readonly property bool foregroundOverlay: presentation === "foreground"
  readonly property bool visualSurfaceEnabled: ambienceEnabled || vignetteEnabled
  readonly property var dustMotesSettings: ambienceSettings.effects
    && ambienceSettings.effects.dustMotes ? ambienceSettings.effects.dustMotes : ({})
  readonly property bool dustMotesRequested: ambienceEnabled
    && normalizedOrder().indexOf("dustMotes") >= 0
    && dustMotesSettings.enabled === true
    && dustMotesSettings.mouseReactive === true
    && Number(dustMotesSettings.intensity) * Number(ambienceSettings.opacity) > 0.001
    && !ambienceSettings.reduceMotion
  readonly property var tacticalGridSettings: ambienceSettings.effects
    && ambienceSettings.effects.tacticalGrid ? ambienceSettings.effects.tacticalGrid : ({})
  readonly property bool tacticalGridRequested: ambienceEnabled
    && normalizedOrder().indexOf("tacticalGrid") >= 0
    && tacticalGridSettings.enabled === true
    && Number(tacticalGridSettings.intensity) * Number(ambienceSettings.opacity) > 0.001
    && (Number(tacticalGridSettings.guideOpacity) > 0.001
      || (Number(tacticalGridSettings.gridOpacity) > 0.001
        && tacticalGridSettings.parallaxEnabled === true
        && Number(tacticalGridSettings.mouseInfluence) > 0.001
        && !ambienceSettings.reduceMotion))
  readonly property bool cursorTrackingRequested: dustMotesRequested || tacticalGridRequested
  readonly property string mappingMode: !visualSurfaceEnabled
    ? "none" : (foregroundOverlay ? "overlay" : "bottom")

  property var productionSurfaces: []
  property int paintAllowedSurfaceCount: 0

  function open(payloadJson) {
    settingsWindow.open(payloadJson)
  }

  function close() {
    settingsWindow.close()
  }

  function normalizedOrder() {
    return orderProbe.normalizeActiveEffects(activeEffects)
  }

  function recountPaintAllowedSurfaces() {
    var count = 0
    for (var i = 0; i < productionSurfaces.length; i++)
      if (productionSurfaces[i] && productionSurfaces[i].paintAllowed) count += 1
    paintAllowedSurfaceCount = count
  }

  function registerProductionSurface(surface) {
    if (!surface || productionSurfaces.indexOf(surface) >= 0) return
    var next = productionSurfaces.slice()
    next.push(surface)
    productionSurfaces = next
    recountPaintAllowedSurfaces()
  }

  function unregisterProductionSurface(surface) {
    var index = productionSurfaces.indexOf(surface)
    if (index < 0) return
    var next = productionSurfaces.slice()
    next.splice(index, 1)
    productionSurfaces = next
    recountPaintAllowedSurfaces()
  }

  function surfaceAt(index) {
    return index >= 0 && index < productionSurfaces.length ? productionSurfaces[index] : null
  }

  function loadedEffectCount() {
    var count = 0
    for (var i = 0; i < productionSurfaces.length; i++) {
      var surface = productionSurfaces[i]
      var stack = surface ? surface.stackObject : null
      if (stack) count += Number(stack.activeProductionEffectCount || 0)
    }
    return count
  }

  function mappedSurfaceCount() {
    var count = 0
    for (var i = 0; i < productionSurfaces.length; i++)
      if (productionSurfaces[i] && productionSurfaces[i].visible) count += 1
    return count
  }

  function surfaceStatus() {
    var result = []
    for (var i = 0; i < productionSurfaces.length; i++) {
      var surface = productionSurfaces[i]
      if (!surface) continue
      var stack = surface.stackObject
      var tacticalGrid = stack ? stack.productionEffectObject("tacticalGrid") : null
      result.push({
        output: surface.outputName,
        mapped: surface.visible,
        mode: surface.layerName,
        fullscreenSuppressed: surface.fullscreenSuppressed,
        paintAllowed: surface.paintAllowed,
        loadedEffectCount: stack ? Number(stack.activeProductionEffectCount || 0) : 0,
        tacticalGrid: tacticalGrid ? {
          width: tacticalGrid.width,
          height: tacticalGrid.height,
          hasCursorSample: tacticalGrid.hasCursorSample,
          cursorInsideOutput: tacticalGrid.cursorInsideOutput,
          rawCursorX: tacticalGrid.rawCursorX,
          rawCursorY: tacticalGrid.rawCursorY,
          rawCursorLocalX: tacticalGrid.rawCursorLocalX,
          rawCursorLocalY: tacticalGrid.rawCursorLocalY,
          screenOriginX: tacticalGrid.screenOriginX,
          screenOriginY: tacticalGrid.screenOriginY
        } : null
      })
    }
    return result
  }

  function zMap() {
    var result = {}
    var order = normalizedOrder()
    for (var i = 0; i < order.length; i++) result[order[i]] = orderProbe.zForEffect(order[i])
    return result
  }

  function statusObject() {
    return {
      version: root.pluginVersion,
      enabled: root.ambienceEnabled,
      presentation: root.presentation,
      mode: root.mappingMode,
      activeEffects: root.normalizedOrder(),
      activeOrder: root.normalizedOrder(),
      vignetteEnabled: root.vignetteEnabled,
      vignetteIntensity: root.vignetteIntensity,
      loadedEffectCount: root.loadedEffectCount(),
      surfaceCount: root.productionSurfaces.length,
      expectedSurfaceCount: Quickshell.screens.length,
      mappedSurfaceCount: root.mappedSurfaceCount(),
      surfaces: root.surfaceStatus(),
      settingsOpened: root.opened,
      z: root.zMap(),
      persistence: {
        healthy: ambienceSettings.persistenceReady
          && ambienceSettings.persistenceState !== "failed"
          && !ambienceSettings.diskDiverged,
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
      theme: themeAdapter.status(),
      cursorTracker: sharedCursorTracker.status()
    }
  }

  function statusJson() {
    return JSON.stringify(statusObject())
  }

  AmbienceSettings { id: ambienceSettings }
  ThemeAdapter { id: themeAdapter }
  FullscreenGuard { id: fullscreenGuard }
  CursorTracker {
    id: sharedCursorTracker
    active: root.cursorTrackingRequested && root.paintAllowedSurfaceCount > 0
    pollIntervalMs: root.tacticalGridRequested ? 60 : 120
  }

  SettingsWindow {
    id: settingsWindow
    settings: ambienceSettings
    shell: root.shell
    pluginId: "jobo.desktop-ambience"
    pluginVersion: root.pluginVersion
  }

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
      id: ambienceSurface
      objectName: "joboDesktopAmbienceSurface"
      required property var modelData
      readonly property string outputName: String(modelData && modelData.name || "")
      readonly property string layerName: root.foregroundOverlay ? "overlay" : "bottom"
      readonly property bool fullscreenSuppressed: root.foregroundOverlay
        && fullscreenGuard.activeOnScreen(modelData)
      readonly property bool paintAllowed: visible && !fullscreenSuppressed
      readonly property var stackObject: productionStack
      readonly property int effectiveLayer: WlrLayershell.layer

      screen: modelData
      visible: root.visualSurfaceEnabled && !remapGuard.remapping
      color: "transparent"
      updatesEnabled: true
      WlrLayershell.namespace: "jobo-desktop-ambience"
      WlrLayershell.layer: root.foregroundOverlay ? WlrLayer.Overlay : WlrLayer.Bottom
      WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
      exclusionMode: ExclusionMode.Ignore
      mask: Region {}

      anchors {
        top: true
        bottom: true
        left: true
        right: true
      }

      ScreenMoveRemap {
        id: remapGuard
        window: ambienceSurface
      }

      AmbienceStack {
        id: productionStack
        anchors.fill: parent
        targetScreen: ambienceSurface.modelData
        settings: ambienceSettings
        theme: themeAdapter
        cursorTracker: sharedCursorTracker
        activeEffects: root.activeEffects
        foregroundOverlay: root.foregroundOverlay
        paintEnabled: ambienceSurface.paintAllowed
        productionEffectsEnabled: root.ambienceEnabled
      }

      VignetteEffect {
        anchors.fill: parent
        z: root.vignetteBehindEffects ? -10000 : 10000
        targetScreen: ambienceSurface.modelData
        settings: root.backgroundVignette
        paintEnabled: ambienceSurface.paintAllowed
      }

      onPaintAllowedChanged: root.recountPaintAllowedSurfaces()
      Component.onCompleted: root.registerProductionSurface(this)
      Component.onDestruction: root.unregisterProductionSurface(this)
    }
  }

  IpcHandler {
    target: "jobo-desktop-ambience"

    function status(): string {
      return root.statusJson()
    }
  }
}
