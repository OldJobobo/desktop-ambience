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
  property real startupOpacity: 1
  property real motionClock: 0
  property int allocatedRayCount: 0

  readonly property var overlaySettings: effectSettings
  readonly property bool configuredEnabled: overlaySettings.enabled === true
  readonly property bool effectVisible: configuredEnabled && runtimeEnabled && effectiveIntensity > 0.001
  readonly property real configuredIntensity: Number(overlaySettings.intensity)
  readonly property real effectiveIntensity: (runtimeIntensity >= 0 ? clamp(runtimeIntensity, 0, 1) : configuredIntensity) * clamp(globalOpacity, 0, 1)
  readonly property real speed: Number(overlaySettings.speed)
  readonly property int rayCount: Math.round(Number(overlaySettings.rayCount))
  readonly property real raySpread: Number(overlaySettings.raySpread)
  readonly property real blurSoftness: Number(overlaySettings.blurSoftness)
  readonly property real accentBlend: Number(overlaySettings.accentBlend)
  readonly property bool shimmer: overlaySettings.shimmer === true
  readonly property bool vignette: overlaySettings.vignette === true
  readonly property string origin: String(overlaySettings.origin)
  readonly property bool originLeft: origin === "top-left" || origin === "bottom-left"
  readonly property bool originTop: origin === "top-left" || origin === "top-right"
  readonly property color themeBackground: themeColor("background", "#101315")
  readonly property color themeForeground: themeColor("foreground", "#d8dee9")
  readonly property color themeAccent: themeColor("accent", themeColor("color14", "#88c0d0"))
  readonly property color themeWarm: themeColor("color11", "#ebcb8b")
  readonly property color themeBright: themeColor("color15", themeForeground)
  readonly property color rayGold: mixColor(themeWarm, themeBright, 0.42)
  readonly property color rayAccent: mixColor(rayGold, themeAccent, accentBlend * 0.48)
  readonly property color rayCool: mixColor(themeColor("color12", themeAccent), themeBright, 0.24)
  readonly property color rayCore: mixColor(themeBright, "#fff8de", 0.48)
  readonly property color dustColor: mixColor(themeBackground, rayAccent, 0.5)
  readonly property real rayLowOpacity: 0.16
  readonly property real rayHighOpacity: 0.46

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

  function colorForRay(index) {
    var paletteColors = [rayAccent, rayGold, rayCool, rayCore]
    return paletteColors[index % paletteColors.length]
  }

  function seededNoise(seed) {
    var value = Math.sin(seed * 12.9898) * 43758.5453
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

    if (payload.intensity !== undefined) {
      runtimeIntensity = clamp(payload.intensity, 0, 1)
    }
  }

  function close() {
    runtimeEnabled = false
  }

  function wave(clock, seed, cyclesPerSecond) {
    return 0.5 - 0.5 * Math.cos((clock * cyclesPerSecond + seededNoise(seed)) * Math.PI * 2)
  }

  function restartStartupReveal() {
    startupReveal.stop()
    startupOpacity = reducedMotion ? 1 : 0.06
    if (effectVisible && !reducedMotion) startupReveal.restart()
  }

  onEffectVisibleChanged: restartStartupReveal()
  onReducedMotionChanged: restartStartupReveal()
  onRayCountChanged: allocatedRayCount = Math.max(allocatedRayCount, rayCount)
  Component.onCompleted: {
    allocatedRayCount = Math.max(0, rayCount)
    restartStartupReveal()
  }

  FrameAnimation {
    running: root.effectVisible && !root.reducedMotion
    onTriggered: root.motionClock = (root.motionClock + frameTime * root.speed) % 3600
  }

  SequentialAnimation {
    id: startupReveal

    NumberAnimation {
      target: root
      property: "startupOpacity"
      from: 0.06
      to: 0.12
      duration: 1400
      easing.type: Easing.InOutSine
    }

    NumberAnimation {
      target: root
      property: "startupOpacity"
      from: 0.12
      to: 1
      duration: 900
      easing.type: Easing.OutCubic
    }
  }

  Item {
    id: raysWindow

    anchors.fill: parent
    visible: root.effectVisible


    Item {
      id: effect

      anchors.fill: parent
      enabled: false
      opacity: root.effectiveIntensity * root.startupOpacity
      readonly property real ambientPulse: root.shimmer
        ? 0.58 + root.wave(root.motionClock, 97, 1 / 24) * 0.42
        : 0.7

      Rectangle {
        anchors.fill: parent
        opacity: 0.14 * effect.ambientPulse
        gradient: Gradient {
          orientation: Gradient.Vertical
          GradientStop { position: 0; color: root.originTop ? Qt.rgba(root.rayAccent.r, root.rayAccent.g, root.rayAccent.b, 0.28) : "#00000000" }
          GradientStop { position: 0.26; color: Qt.rgba(root.dustColor.r, root.dustColor.g, root.dustColor.b, 0.08) }
          GradientStop { position: 0.62; color: Qt.rgba(root.rayGold.r, root.rayGold.g, root.rayGold.b, 0.035) }
          GradientStop { position: 1; color: root.originTop ? "#00000000" : Qt.rgba(root.rayAccent.r, root.rayAccent.g, root.rayAccent.b, 0.28) }
        }
      }

      Item {
        id: sourceBloom

        readonly property int sourceX: Math.round(raysWindow.width * (root.originLeft ? 0.15 : 0.85))
        readonly property int sourceY: Math.round(raysWindow.height * (root.originTop ? -0.03 : 1.03))
        readonly property int bloomSize: Math.round(Math.max(raysWindow.width, raysWindow.height) * 0.42)

        x: sourceX - bloomSize / 2
        y: sourceY - bloomSize / 2
        width: bloomSize
        height: bloomSize
        opacity: 0.72 * effect.ambientPulse
        layer.enabled: true
        layer.smooth: true
        layer.effect: MultiEffect {
          blurEnabled: true
          blurMax: 96
          blur: 1
          autoPaddingEnabled: true
        }

        Rectangle {
          anchors.centerIn: parent
          width: parent.width
          height: parent.height
          radius: width / 2
          color: Qt.rgba(root.rayAccent.r, root.rayAccent.g, root.rayAccent.b, 0.13)
        }

        Rectangle {
          anchors.centerIn: parent
          width: Math.round(parent.width * 0.46)
          height: width
          radius: width / 2
          color: Qt.rgba(root.rayCore.r, root.rayCore.g, root.rayCore.b, 0.18)
        }
      }

      Repeater {
        model: root.allocatedRayCount

        Item {
          id: ray

          readonly property real seed: index + 211
          readonly property real targetLane: root.rayCount === 1 ? 0.5 : index / Math.max(1, root.rayCount - 1)
          property real fanLane: targetLane
          property bool populationReady: false
          property real populationOpacity: populationReady && index < root.rayCount ? 1 : 0
          readonly property int blurPad: Math.round(120 + root.blurSoftness * 180)
          readonly property int rayWidth: Math.max(180, Math.round(raysWindow.width * (0.105 + root.seededNoise(seed + 3) * 0.07)))
          readonly property int rayLength: Math.max(1100, Math.round(Math.max(raysWindow.width, raysWindow.height) * (1.62 + root.seededNoise(seed + 5) * 0.34)))
          readonly property real direction: root.originTop ? (root.originLeft ? -1 : 1) : (root.originLeft ? 1 : -1)
          readonly property real angle: direction * (16 + fanLane * 42 * root.raySpread) + (root.seededNoise(seed + 7) - 0.5) * 3.5
          readonly property int sourceX: Math.round(raysWindow.width * (root.originLeft ? 0.15 : 0.85))
          readonly property int sourceY: Math.round(raysWindow.height * (root.originTop ? -0.03 : 1.03))
          readonly property int sourceJitterX: Math.round((root.seededNoise(seed + 9) - 0.5) * raysWindow.width * 0.035)
          readonly property int sourceJitterY: Math.round((root.seededNoise(seed + 10) - 0.5) * raysWindow.height * 0.018)
          readonly property int driftX: Math.round(raysWindow.width * (0.01 + root.seededNoise(seed + 11) * 0.024) * (root.originLeft ? 1 : -1))
          readonly property int driftY: Math.round(raysWindow.height * (0.014 + root.seededNoise(seed + 13) * 0.028) * (root.originTop ? 1 : -1))
          readonly property int xA: sourceX + sourceJitterX - Math.round(width * 0.5)
          readonly property int xB: xA + driftX
          readonly property int yA: root.originTop
            ? sourceY + sourceJitterY - blurPad
            : sourceY + sourceJitterY - height + blurPad
          readonly property int yB: yA + driftY
          readonly property real driftSpeed: 0.52 + root.seededNoise(seed + 19) * 0.72
          readonly property real baseOpacity: root.rayLowOpacity + root.seededNoise(seed + 23) * 0.18
          readonly property color rayColor: root.colorForRay(index)
          readonly property color companionColor: root.colorForRay(index + 1)

          x: xA + (xB - xA) * root.wave(root.motionClock, seed + 31, driftSpeed / 30)
          y: yA + (yB - yA) * root.wave(root.motionClock, seed + 41, (0.78 + driftSpeed * 0.46) / 34)
          width: rayWidth + blurPad * 2
          height: rayLength + blurPad * 2
          opacity: populationOpacity * (root.shimmer
            ? baseOpacity * 0.7 + (Math.min(root.rayHighOpacity, baseOpacity * 1.42) - baseOpacity * 0.7)
              * root.wave(root.motionClock, seed + 47, 1 / 22)
            : baseOpacity)
          rotation: angle
          transformOrigin: root.originTop ? Item.Top : Item.Bottom
          layer.enabled: true
          layer.smooth: true
          layer.effect: MultiEffect {
            blurEnabled: true
            blurMax: 96
            blur: 0.72 + root.blurSoftness * 0.28
            autoPaddingEnabled: true
          }

          Timer {
            interval: 240
            running: true
            onTriggered: ray.populationReady = true
          }

          Behavior on fanLane {
            NumberAnimation { duration: 360; easing.type: Easing.InOutSine }
          }

          Behavior on populationOpacity {
            NumberAnimation { duration: 360; easing.type: Easing.InOutSine }
          }

          Rectangle {
            x: ray.blurPad
            y: ray.blurPad
            width: ray.rayWidth
            height: ray.rayLength
            radius: Math.max(1, width / 2)
            gradient: Gradient {
              orientation: Gradient.Horizontal
              GradientStop { position: 0; color: "#00000000" }
              GradientStop { position: 0.18; color: Qt.rgba(ray.rayColor.r, ray.rayColor.g, ray.rayColor.b, 0.045) }
              GradientStop { position: 0.45; color: Qt.rgba(root.rayCore.r, root.rayCore.g, root.rayCore.b, 0.28) }
              GradientStop { position: 0.58; color: Qt.rgba(ray.companionColor.r, ray.companionColor.g, ray.companionColor.b, 0.11) }
              GradientStop { position: 0.84; color: Qt.rgba(ray.rayColor.r, ray.rayColor.g, ray.rayColor.b, 0.035) }
              GradientStop { position: 1; color: "#00000000" }
            }
          }

          Rectangle {
            x: ray.blurPad + Math.round(ray.rayWidth * 0.36)
            y: ray.blurPad
            width: Math.max(2, Math.round(ray.rayWidth * 0.18))
            height: Math.round(ray.rayLength * 0.72)
            radius: Math.max(1, width / 2)
            opacity: 0.42
            gradient: Gradient {
              orientation: Gradient.Vertical
              GradientStop { position: 0; color: Qt.rgba(root.rayCore.r, root.rayCore.g, root.rayCore.b, 0.38) }
              GradientStop { position: 0.42; color: Qt.rgba(root.rayGold.r, root.rayGold.g, root.rayGold.b, 0.12) }
              GradientStop { position: 1; color: "#00000000" }
            }
          }
        }
      }

      Repeater {
        model: Math.max(3, Math.round(root.allocatedRayCount * 0.7))

        Rectangle {
          id: mote

          readonly property real seed: index + 701
          readonly property int moteSize: Math.round(3 + root.seededNoise(seed + 1) * 7)
          readonly property int xA: Math.round(root.seededNoise(seed + 3) * raysWindow.width)
          readonly property int xB: xA + Math.round((root.seededNoise(seed + 5) - 0.5) * raysWindow.width * 0.12)
          readonly property int yA: Math.round(root.seededNoise(seed + 7) * raysWindow.height)
          readonly property int yB: yA + Math.round((root.originTop ? 1 : -1) * raysWindow.height * (0.035 + root.seededNoise(seed + 11) * 0.055))
          readonly property real moteOpacity: 0.1 + root.seededNoise(seed + 13) * 0.16
          readonly property int activeMoteCount: Math.max(3, Math.round(root.rayCount * 0.7))
          property bool populationReady: false
          property real populationOpacity: populationReady && index < activeMoteCount ? 1 : 0

          x: xA + (xB - xA) * root.wave(root.motionClock, seed + 17, 1 / 26)
          y: yA + (yB - yA) * root.wave(root.motionClock, seed + 19, 1 / 28)
          width: moteSize
          height: moteSize
          radius: width / 2
          color: Qt.rgba(root.rayCore.r, root.rayCore.g, root.rayCore.b, 0.8)
          opacity: populationOpacity * (root.shimmer
            ? moteOpacity * (0.25 + root.wave(root.motionClock, seed + 23, 1 / 20) * 0.75)
            : moteOpacity)
          visible: root.shimmer
          layer.enabled: true
          layer.smooth: true
          layer.effect: MultiEffect {
            blurEnabled: true
            blurMax: 12
            blur: 0.8
            autoPaddingEnabled: true
          }

          Timer {
            interval: 240
            running: true
            onTriggered: mote.populationReady = true
          }

          Behavior on populationOpacity {
            NumberAnimation { duration: 360; easing.type: Easing.InOutSine }
          }
        }
      }

      Item {
        anchors.fill: parent
        visible: root.vignette
        opacity: 0.52

        Rectangle {
          x: 0
          y: 0
          width: parent.width
          height: Math.round(parent.height * 0.2)
          gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0; color: "#26000000" }
            GradientStop { position: 1; color: "#00000000" }
          }
        }

        Rectangle {
          x: 0
          y: parent.height - height
          width: parent.width
          height: Math.round(parent.height * 0.28)
          gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0; color: "#00000000" }
            GradientStop { position: 1; color: "#42000000" }
          }
        }
      }
    }
  }


}
