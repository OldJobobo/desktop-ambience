import QtQuick
import QtQuick.Effects

Item {
  id: root

  property var effectSettings: ({})
  property real globalOpacity: 1
  property bool reducedMotion: false
  property var theme: null
  property bool runtimeEnabled: true
  property real runtimeIntensity: -1

  readonly property var overlaySettings: effectSettings
  readonly property bool configuredEnabled: overlaySettings.enabled === true
  readonly property real configuredIntensity: Number(overlaySettings.intensity)
  readonly property real effectiveIntensity: (runtimeIntensity >= 0
    ? clamp(runtimeIntensity, 0, 1) : configuredIntensity) * clamp(globalOpacity, 0, 1)
  readonly property bool effectVisible: configuredEnabled && runtimeEnabled && effectiveIntensity > 0.001
  readonly property real speed: Number(overlaySettings.speed)
  readonly property int lightCount: Math.round(Number(overlaySettings.lightCount))
  readonly property real lightSize: Number(overlaySettings.lightSize)
  readonly property real blurSoftness: Number(overlaySettings.blurSoftness)
  readonly property real driftAmount: Number(overlaySettings.driftAmount)
  readonly property real twinkleAmount: Number(overlaySettings.twinkleAmount)
  readonly property string primaryColorRole: String(overlaySettings.primaryColorRole)
  readonly property string secondaryColorRole: String(overlaySettings.secondaryColorRole)

  // These properties are intentionally public so behavior and performance
  // probes can verify the bounded grouped-blur contract without inspecting the
  // renderer's private item tree.
  readonly property string effectivePrimaryColorRole: primaryColorRole
  readonly property string effectiveSecondaryColorRole: secondaryColorRole
  readonly property color effectivePrimaryColor: themeColor(primaryColorRole, "#88c0d0")
  readonly property color effectiveSecondaryColor: themeColor(secondaryColorRole, "#b48ead")
  readonly property real maximumDrift: 24 + driftAmount * 104
  readonly property real maximumDiscRadius: lightSize * 1.32 * 0.5
  readonly property real maximumBlurPadding: 28 + blurSoftness * 92
  readonly property int overscan: Math.round(clamp(
    maximumDrift + maximumDiscRadius + maximumBlurPadding + 8, 96, 448))
  readonly property int boundedDelegateCount: farRepeater.count + middleRepeater.count + nearRepeater.count
  readonly property int activeBlurLayerCount: effectVisible && blurSoftness > 0.001 ? 3 : 0
  readonly property bool driftAnimationsRunning: effectVisible && !reducedMotion && driftAmount > 0.001
  readonly property bool twinkleAnimationsRunning: effectVisible && !reducedMotion && twinkleAmount > 0.001
  readonly property bool animationRunning: driftAnimationsRunning || twinkleAnimationsRunning

  function clamp(value, minimum, maximum) {
    var numeric = Number(value)
    if (isNaN(numeric)) return minimum
    return Math.max(minimum, Math.min(maximum, numeric))
  }

  function seededNoise(seed) {
    var value = Math.sin(seed * 12.9898) * 43758.5453
    return value - Math.floor(value)
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

  function colorForLight(index) {
    var alternating = index % 2 === 0 ? 0.18 : 0.82
    var variation = (seededNoise(index + 173) - 0.5) * 0.24
    return mixColor(effectivePrimaryColor, effectiveSecondaryColor,
      clamp(alternating + variation, 0.08, 0.92))
  }

  function phaseProgress(phase, reverse) {
    var progress = 0.5 - 0.5 * Math.cos(Number(phase) * Math.PI)
    return reverse ? 1 - progress : progress
  }

  function bandCount(band) {
    return Math.max(0, Math.floor((lightCount + 2 - band) / 3))
  }

  function delegateObject(lightIndex) {
    var normalized = Math.round(Number(lightIndex))
    if (normalized < 0 || normalized >= lightCount) return null
    var band = normalized % 3
    var localIndex = Math.floor(normalized / 3)
    return band === 0 ? farRepeater.itemAt(localIndex)
      : band === 1 ? middleRepeater.itemAt(localIndex)
      : nearRepeater.itemAt(localIndex)
  }

  function lightSnapshot(lightIndex) {
    var light = delegateObject(lightIndex)
    if (!light) return null
    return {
      index: light.lightIndex,
      depthBand: light.depthBand,
      staticX: light.staticX,
      staticY: light.staticY,
      diameter: light.diameter,
      baseOpacity: light.baseOpacity,
      reverseX: light.reverseX,
      reverseY: light.reverseY,
      xA: light.xA,
      xB: light.xB,
      yA: light.yA,
      yB: light.yB,
      twinkleFloor: light.twinkleFloor,
      twinklePeak: light.twinklePeak,
      initialXPhase: light.initialXPhase,
      initialYPhase: light.initialYPhase,
      initialTwinklePhase: light.initialTwinklePhase,
      initialXProgress: light.initialXProgress,
      initialYProgress: light.initialYProgress,
      initialTwinkleProgress: light.initialTwinkleProgress,
      startupX: light.startupX,
      startupY: light.startupY,
      startupOpacity: light.startupOpacity,
      cycleEndX: light.cycleEndX,
      cycleEndY: light.cycleEndY,
      cycleEndOpacity: light.cycleEndOpacity,
      currentX: light.x,
      currentY: light.y,
      currentOpacity: light.opacity
    }
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

  Item {
    id: viewport
    anchors.fill: parent
    visible: root.effectVisible
    opacity: root.effectiveIntensity
    enabled: false
    clip: true

    Item {
      id: farLayer
      x: -root.overscan
      y: -root.overscan
      width: viewport.width + root.overscan * 2
      height: viewport.height + root.overscan * 2
      layer.enabled: root.effectVisible && root.blurSoftness > 0.001
      layer.smooth: true
      layer.effect: MultiEffect {
        blurEnabled: true
        blurMax: 80
        blur: root.blurSoftness
        autoPaddingEnabled: false
      }

      Repeater {
        id: farRepeater
        model: root.bandCount(0)
        delegate: LightDisc {
          depthBand: 0
          depthScale: 0.58
          depthOpacity: 0.42
          depthMotion: 0.36
          depthSpeed: 0.56
        }
      }
    }

    Item {
      id: middleLayer
      x: -root.overscan
      y: -root.overscan
      width: viewport.width + root.overscan * 2
      height: viewport.height + root.overscan * 2
      layer.enabled: root.effectVisible && root.blurSoftness > 0.001
      layer.smooth: true
      layer.effect: MultiEffect {
        blurEnabled: true
        blurMax: 68
        blur: root.blurSoftness * 0.86
        autoPaddingEnabled: false
      }

      Repeater {
        id: middleRepeater
        model: root.bandCount(1)
        delegate: LightDisc {
          depthBand: 1
          depthScale: 0.88
          depthOpacity: 0.62
          depthMotion: 0.66
          depthSpeed: 0.76
        }
      }
    }

    Item {
      id: nearLayer
      x: -root.overscan
      y: -root.overscan
      width: viewport.width + root.overscan * 2
      height: viewport.height + root.overscan * 2
      layer.enabled: root.effectVisible && root.blurSoftness > 0.001
      layer.smooth: true
      layer.effect: MultiEffect {
        blurEnabled: true
        blurMax: 56
        blur: root.blurSoftness * 0.7
        autoPaddingEnabled: false
      }

      Repeater {
        id: nearRepeater
        model: root.bandCount(2)
        delegate: LightDisc {
          depthBand: 2
          depthScale: 1.16
          depthOpacity: 0.82
          depthMotion: 1
          depthSpeed: 1
        }
      }
    }
  }

  component LightDisc: Item {
    id: light

    required property int index
    required property int depthBand
    required property real depthScale
    required property real depthOpacity
    required property real depthMotion
    required property real depthSpeed

    readonly property int lightIndex: index * 3 + depthBand
    readonly property real seed: lightIndex + 601
    readonly property real diameter: root.lightSize * depthScale
      * (0.78 + root.seededNoise(seed + 3) * 0.44)
    readonly property real baseOpacity: depthOpacity * (0.54 + root.seededNoise(seed + 5) * 0.32)
    readonly property real staticX: root.overscan + root.seededNoise(seed + 7) * root.width - diameter * 0.5
    readonly property real staticY: root.overscan + root.seededNoise(seed + 11) * root.height - diameter * 0.5
    readonly property real routeX: root.maximumDrift * depthMotion
      * (0.42 + root.seededNoise(seed + 13) * 0.58)
    readonly property real routeY: root.maximumDrift * depthMotion
      * (0.38 + root.seededNoise(seed + 17) * 0.62)
    readonly property bool reverseX: root.seededNoise(seed + 19) > 0.5
    readonly property bool reverseY: root.seededNoise(seed + 23) > 0.5
    readonly property real xA: staticX - routeX * (0.35 + root.seededNoise(seed + 29) * 0.3)
    readonly property real xB: staticX + routeX * (0.45 + root.seededNoise(seed + 31) * 0.35)
    readonly property real yA: staticY - routeY * (0.35 + root.seededNoise(seed + 37) * 0.3)
    readonly property real yB: staticY + routeY * (0.45 + root.seededNoise(seed + 41) * 0.35)
    readonly property color lightColor: root.colorForLight(lightIndex)
    readonly property real twinkleFloor: baseOpacity * (1 - root.twinkleAmount * 0.42)
    readonly property real twinklePeak: Math.min(1, baseOpacity * (1 + root.twinkleAmount * 0.48))
    readonly property real initialXPhase: root.seededNoise(seed + 43) * 2
    readonly property real initialYPhase: root.seededNoise(seed + 47) * 2
    readonly property real initialTwinklePhase: root.seededNoise(seed + 53) * 2
    readonly property real initialXProgress: root.phaseProgress(initialXPhase, reverseX)
    readonly property real initialYProgress: root.phaseProgress(initialYPhase, reverseY)
    readonly property real initialTwinkleProgress: root.phaseProgress(initialTwinklePhase, false)
    readonly property real startupX: xA + (xB - xA) * initialXProgress
    readonly property real startupY: yA + (yB - yA) * initialYProgress
    readonly property real startupOpacity: twinkleFloor
      + (twinklePeak - twinkleFloor) * initialTwinkleProgress
    readonly property real cycleEndX: xA
      + (xB - xA) * root.phaseProgress(initialXPhase + 2, reverseX)
    readonly property real cycleEndY: yA
      + (yB - yA) * root.phaseProgress(initialYPhase + 2, reverseY)
    readonly property real cycleEndOpacity: twinkleFloor
      + (twinklePeak - twinkleFloor) * root.phaseProgress(initialTwinklePhase + 2, false)

    property real motionXPhase: initialXPhase
    property real motionYPhase: initialYPhase
    property real twinklePhase: initialTwinklePhase

    objectName: "bokehLight" + lightIndex
    x: root.driftAnimationsRunning
      ? xA + (xB - xA) * root.phaseProgress(motionXPhase, reverseX) : staticX
    y: root.driftAnimationsRunning
      ? yA + (yB - yA) * root.phaseProgress(motionYPhase, reverseY) : staticY
    width: diameter
    height: diameter
    opacity: root.twinkleAnimationsRunning
      ? twinkleFloor + (twinklePeak - twinkleFloor) * root.phaseProgress(twinklePhase, false)
      : baseOpacity

    NumberAnimation on motionXPhase {
      loops: Animation.Infinite
      running: root.driftAnimationsRunning
      from: light.initialXPhase
      to: light.initialXPhase + 2
      duration: Math.max(18400, (36000 + root.seededNoise(light.seed + 59) * 27000)
        / (root.speed * light.depthSpeed))
      easing.type: Easing.Linear
    }

    NumberAnimation on motionYPhase {
      loops: Animation.Infinite
      running: root.driftAnimationsRunning
      from: light.initialYPhase
      to: light.initialYPhase + 2
      duration: Math.max(20000, (44000 + root.seededNoise(light.seed + 61) * 31000)
        / (root.speed * (0.71 + light.depthSpeed * 0.43)))
      easing.type: Easing.Linear
    }

    NumberAnimation on twinklePhase {
      loops: Animation.Infinite
      running: root.twinkleAnimationsRunning
      from: light.initialTwinklePhase
      to: light.initialTwinklePhase + 2
      duration: Math.max(17500, (32000 + root.seededNoise(light.seed + 67) * 27000)
        / (root.speed * (0.77 + light.depthSpeed * 0.33)))
      easing.type: Easing.Linear
    }

    Rectangle {
      anchors.fill: parent
      radius: width / 2
      color: Qt.rgba(light.lightColor.r, light.lightColor.g, light.lightColor.b, 0.34)
      border.width: Math.max(1, light.width * 0.018)
      border.color: Qt.rgba(light.lightColor.r, light.lightColor.g, light.lightColor.b, 0.22)
    }

    Rectangle {
      anchors.centerIn: parent
      width: parent.width * 0.58
      height: width
      radius: width / 2
      color: Qt.rgba(light.lightColor.r, light.lightColor.g, light.lightColor.b, 0.32)
    }

    Rectangle {
      x: parent.width * (0.22 + root.seededNoise(light.seed + 73) * 0.08)
      y: parent.height * (0.18 + root.seededNoise(light.seed + 79) * 0.08)
      width: parent.width * (0.13 + root.seededNoise(light.seed + 83) * 0.08)
      height: width
      radius: width / 2
      color: Qt.rgba(1, 1, 1, 0.2)
    }
  }
}
