import QtQuick

Item {
  id: root

  property var effectSettings: ({})
  property real globalOpacity: 1
  property bool reducedMotion: false
  property var theme: null
  property bool runtimeEnabled: true
  property real runtimeIntensity: -1
  property int styleGeneration: 0
  property int destroyedStyleCount: 0
  property string lastDestroyedStyle: ""

  readonly property var overlaySettings: effectSettings
  readonly property bool configuredEnabled: overlaySettings.enabled === true
  readonly property real configuredIntensity: Number(overlaySettings.intensity)
  readonly property real effectiveIntensity: (runtimeIntensity >= 0
    ? clamp(runtimeIntensity, 0, 1) : configuredIntensity) * clamp(globalOpacity, 0, 1)
  readonly property bool effectVisible: configuredEnabled && runtimeEnabled && effectiveIntensity > 0.001
  readonly property real speed: Number(overlaySettings.speed)
  readonly property string configuredStyle: String(overlaySettings.precipitationStyle)
  readonly property string selectedStyle: configuredStyle === "snow" ? "snow" : "rain"
  readonly property int dropCount: Math.round(Number(overlaySettings.dropCount))
  readonly property real slant: Number(overlaySettings.slant)
  readonly property real mistAmount: Number(overlaySettings.mistAmount)
  readonly property real splashAmount: Number(overlaySettings.splashAmount)
  readonly property real accentBlend: Number(overlaySettings.accentBlend)
  readonly property bool vignette: overlaySettings.vignette === true
  readonly property real flakeSize: Number(overlaySettings.flakeSize)
  readonly property real flutterAmount: Number(overlaySettings.flutterAmount)
  readonly property string flakeDetail: String(overlaySettings.flakeDetail)

  readonly property color themeBackground: themeColor("background", "#101315")
  readonly property color themeForeground: themeColor("foreground", "#d8dee9")
  readonly property color themeAccent: themeColor("accent", themeColor("color14", "#88c0d0"))
  readonly property color themeBright: themeColor("color15", themeForeground)
  readonly property color coolRainBase: mixColor("#abc8d6", themeBright, 0.2)
  readonly property color rainColor: mixColor(coolRainBase, themeAccent, accentBlend * 0.35)
  readonly property color shadowRainColor: mixColor(themeBackground, rainColor, 0.58)
  readonly property color snowColor: mixColor(themeBright, themeAccent, accentBlend * 0.22)
  readonly property color snowShadowColor: mixColor(themeBackground, snowColor, 0.72)
  readonly property real windDrift: slant * 0.18
  readonly property real dropRotation: 2 + slant * 16

  readonly property var loadedStyleObject: styleLoader.item
  readonly property int loadedStyleCount: styleLoader.item === null ? 0 : 1
  readonly property string loadedStyleName: styleLoader.item ? String(styleLoader.item.styleName) : ""
  readonly property bool autonomousMotionRunning: styleLoader.item
    ? styleLoader.item.autonomousMotionRunning === true : false
  readonly property bool visualLayerEnabled: styleLoader.item
    ? styleLoader.item.visualLayerEnabled === true : false
  readonly property int mistBandCount: selectedStyle === "rain" && styleLoader.item
    ? Number(styleLoader.item.mistBandCount || 0) : 0
  readonly property int primaryDropCount: selectedStyle === "rain" && styleLoader.item
    ? Number(styleLoader.item.primaryDropCount || 0) : 0
  readonly property int sheetDropCount: selectedStyle === "rain" && styleLoader.item
    ? Number(styleLoader.item.sheetDropCount || 0) : 0
  readonly property int foregroundDropCount: selectedStyle === "rain" && styleLoader.item
    ? Number(styleLoader.item.foregroundDropCount || 0) : 0
  readonly property int splashCount: selectedStyle === "rain" && styleLoader.item
    ? Number(styleLoader.item.splashCount || 0) : 0
  readonly property int boundedParticleCount: styleLoader.item
    ? Number(styleLoader.item.boundedParticleCount || 0) : 0
  readonly property int snowFlakeCount: selectedStyle === "snow" && styleLoader.item
    ? Number(styleLoader.item.flakeCount || 0) : 0
  readonly property int snowCrystalCount: selectedStyle === "snow" && styleLoader.item
    ? Number(styleLoader.item.crystalFlakeCount || 0) : 0
  readonly property int snowPrimitiveCount: selectedStyle === "snow" && styleLoader.item
    ? Number(styleLoader.item.detailPrimitiveCount || 0) : 0
  readonly property int snowClockUpdateCount: selectedStyle === "snow" && styleLoader.item
    ? Number(styleLoader.item.clockUpdateCount || 0) : 0
  readonly property int animationObjectCount: styleLoader.item
    ? Number(styleLoader.item.animationObjectCount || 0) : 0
  readonly property int runningAnimationCount: styleLoader.item
    ? Number(styleLoader.item.runningAnimationCount || 0) : 0
  readonly property int clockObjectCount: styleLoader.item
    ? Number(styleLoader.item.clockObjectCount || 0) : 0
  readonly property int runningClockCount: styleLoader.item
    ? Number(styleLoader.item.runningClockCount || 0) : 0

  function clamp(value, minimum, maximum) {
    var numeric = Number(value)
    if (isNaN(numeric)) return minimum
    return Math.max(minimum, Math.min(maximum, numeric))
  }

  function themeColor(name, fallbackColor) {
    return theme && theme.colorFor ? theme.colorFor(name, fallbackColor) : fallbackColor
  }

  function resolvedColor(value) {
    return value && value.r !== undefined ? value : Qt.color(value)
  }

  function mixColor(a, b, amount) {
    var first = resolvedColor(a)
    var second = resolvedColor(b)
    var mix = clamp(amount, 0, 1)
    return Qt.rgba(
      first.r + (second.r - first.r) * mix,
      first.g + (second.g - first.g) * mix,
      first.b + (second.b - first.b) * mix,
      first.a + (second.a - first.a) * mix
    )
  }

  function parsePayload(payloadJson) {
    try {
      return payloadJson ? JSON.parse(payloadJson) : {}
    } catch (error) {
      return {}
    }
  }

  function primaryDropObject(index) {
    return selectedStyle === "rain" && styleLoader.item
      ? styleLoader.item.primaryDropObject(index) : null
  }

  function primaryDropSnapshot(index) {
    return selectedStyle === "rain" && styleLoader.item
      ? styleLoader.item.primaryDropSnapshot(index) : null
  }

  function snowFlakeObject(index) {
    return selectedStyle === "snow" && styleLoader.item
      ? styleLoader.item.flakeObject(index) : null
  }

  function snowFlakeSnapshot(index) {
    return selectedStyle === "snow" && styleLoader.item
      ? styleLoader.item.flakeSnapshot(index) : null
  }

  function notifyStyleDestroyed(styleName) {
    destroyedStyleCount += 1
    lastDestroyedStyle = String(styleName || "")
  }

  function open(payloadJson) {
    var payload = parsePayload(payloadJson)
    runtimeEnabled = true
    if (payload.intensity !== undefined) runtimeIntensity = clamp(payload.intensity, 0, 1)
  }

  function close() {
    runtimeEnabled = false
  }

  Loader {
    id: styleLoader
    anchors.fill: parent
    sourceComponent: root.selectedStyle === "snow" ? snowStyleComponent : rainStyleComponent
    onLoaded: root.styleGeneration += 1
  }

  Component {
    id: rainStyleComponent
    RainPrecipitationStyle {
      styleName: "rain"
      effectVisible: root.effectVisible
      effectiveIntensity: root.effectiveIntensity
      reducedMotion: root.reducedMotion
      speed: root.speed
      dropCount: root.dropCount
      slant: root.slant
      mistAmount: root.mistAmount
      splashAmount: root.splashAmount
      vignette: root.vignette
      rainColor: root.rainColor
      shadowRainColor: root.shadowRainColor
      onStyleDestroyed: function(name) { root.notifyStyleDestroyed(name) }
    }
  }

  Component {
    id: snowStyleComponent
    SnowPrecipitationStyle {
      styleName: "snow"
      effectVisible: root.effectVisible
      effectiveIntensity: root.effectiveIntensity
      reducedMotion: root.reducedMotion
      speed: root.speed
      dropCount: root.dropCount
      slant: root.slant
      flakeSize: root.flakeSize
      flutterAmount: root.flutterAmount
      flakeDetail: root.flakeDetail
      vignette: root.vignette
      snowColor: root.snowColor
      snowShadowColor: root.snowShadowColor
      onStyleDestroyed: function(name) { root.notifyStyleDestroyed(name) }
    }
  }
}
