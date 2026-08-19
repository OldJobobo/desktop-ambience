import QtQuick

Item {
  id: root

  property var effectSettings: ({})
  property real globalOpacity: 1
  property bool reducedMotion: false
  property var theme: null
  property bool runtimeEnabled: true
  property real runtimeIntensity: -1
  property int grainTick: 0
  property real grainAccumulator: 0

  readonly property var overlaySettings: effectSettings
  readonly property bool configuredEnabled: overlaySettings.enabled === true
  readonly property bool effectVisible: configuredEnabled && runtimeEnabled && effectiveIntensity > 0.001
  readonly property real configuredIntensity: Number(overlaySettings.intensity)
  readonly property real effectiveIntensity: (runtimeIntensity >= 0 ? clamp(runtimeIntensity, 0, 1) : configuredIntensity) * clamp(globalOpacity, 0, 1)
  readonly property real speed: Number(overlaySettings.speed)
  readonly property int grainCount: Math.round(Number(overlaySettings.grainCount))
  readonly property real grainSize: Number(overlaySettings.grainSize)
  readonly property real accentBlend: Number(overlaySettings.accentBlend)
  readonly property color themeForeground: themeColor("foreground", "#d8dee9")
  readonly property color themeAccent: themeColor("accent", "#88c0d0")
  readonly property color grainColor: mixColor(themeForeground, themeAccent, accentBlend)

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

  function seededNoise(seed) {
    var value = Math.sin(seed * 12.9898 + grainTick * 78.233) * 43758.5453
    return value - Math.floor(value)
  }

  function parsePayload(payloadJson) {
    try {
      return payloadJson ? JSON.parse(payloadJson) : {}
    } catch (error) {
      return {}
    }
  }

  function open(payloadJson) {
    var payload = parsePayload(payloadJson)
    runtimeEnabled = true
    if (payload.intensity !== undefined) runtimeIntensity = clamp(payload.intensity, 0, 1)
  }

  function close() {
    runtimeEnabled = false
  }

  FrameAnimation {
    id: grainFrameClock

    running: root.effectVisible && !root.reducedMotion
    onTriggered: {
      root.grainAccumulator += frameTime * 1000
      var interval = Math.max(28, Math.round(88 / root.speed))
      while (root.grainAccumulator >= interval) {
        root.grainTick += 1
        root.grainAccumulator -= interval
      }
    }
  }

  Item {
    id: grainWindow

    anchors.fill: parent
    visible: root.effectVisible


    Item {
      anchors.fill: parent
      enabled: false
      opacity: root.effectiveIntensity

      Repeater {
        model: root.grainCount

        Rectangle {
          required property int index

          readonly property real sizeNoise: root.seededNoise(index + 31)
          x: Math.round(root.seededNoise(index + 3) * Math.max(1, grainWindow.width))
          y: Math.round(root.seededNoise(index + 7) * Math.max(1, grainWindow.height))
          width: Math.max(1, Math.round(root.grainSize + sizeNoise * root.grainSize))
          height: width
          radius: width > 1 ? width / 2 : 0
          color: root.grainColor
          opacity: 0.12 + root.seededNoise(index + 13) * 0.58
        }
      }
    }
  }


}
