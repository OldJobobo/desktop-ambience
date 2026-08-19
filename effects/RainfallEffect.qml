import QtQuick

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
  readonly property bool effectVisible: configuredEnabled && runtimeEnabled && effectiveIntensity > 0.001
  readonly property real configuredIntensity: Number(overlaySettings.intensity)
  readonly property real effectiveIntensity: (runtimeIntensity >= 0 ? clamp(runtimeIntensity, 0, 1) : configuredIntensity) * clamp(globalOpacity, 0, 1)
  readonly property real speed: Number(overlaySettings.speed)
  readonly property int dropCount: Math.round(Number(overlaySettings.dropCount))
  readonly property real slant: Number(overlaySettings.slant)
  readonly property real mistAmount: Number(overlaySettings.mistAmount)
  readonly property real splashAmount: Number(overlaySettings.splashAmount)
  readonly property real accentBlend: Number(overlaySettings.accentBlend)
  readonly property bool vignette: overlaySettings.vignette === true
  readonly property color themeBackground: themeColor("background", "#101315")
  readonly property color themeForeground: themeColor("foreground", "#d8dee9")
  readonly property color themeAccent: themeColor("accent", themeColor("color14", "#88c0d0"))
  readonly property color themeBright: themeColor("color15", themeForeground)
  readonly property color coolRainBase: mixColor("#abc8d6", themeBright, 0.2)
  readonly property color rainColor: mixColor(coolRainBase, themeAccent, accentBlend * 0.35)
  readonly property color shadowRainColor: mixColor(themeBackground, rainColor, 0.58)
  readonly property real windDrift: slant * 0.18
  readonly property real dropRotation: 2 + slant * 16

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

  function seededNoise(seed) {
    var value = Math.sin(seed * 12.9898) * 43758.5453
    return value - Math.floor(value)
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

  Item {
    id: rainWindow

    anchors.fill: parent
    visible: root.effectVisible


    Item {
      id: effect

      anchors.fill: parent
      enabled: false
      opacity: root.effectiveIntensity

      Repeater {
        model: root.mistAmount > 0 ? 5 : 0

        Rectangle {
          readonly property real seed: index + 41
          readonly property int bandHeight: Math.round(rainWindow.height * (0.1 + root.seededNoise(seed) * 0.08))

          x: 0
          y: Math.round(rainWindow.height * (0.38 + index * 0.11))
          width: rainWindow.width
          height: bandHeight
          opacity: root.mistAmount * (0.08 + root.seededNoise(seed + 7) * 0.11)
          gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop {
              position: 0
              color: "#00000000"
            }
            GradientStop {
              position: 0.46
              color: Qt.rgba(root.shadowRainColor.r, root.shadowRainColor.g, root.shadowRainColor.b, 0.34)
            }
            GradientStop {
              position: 1
              color: "#00000000"
            }
          }

          SequentialAnimation on x {
            loops: Animation.Infinite
            running: root.effectVisible && !root.reducedMotion

            NumberAnimation {
              from: -Math.round(rainWindow.width * 0.04)
              to: Math.round(rainWindow.width * 0.04)
              duration: Math.max(6000, (11000 + index * 1300) / root.speed)
              easing.type: Easing.InOutSine
            }

            NumberAnimation {
              from: Math.round(rainWindow.width * 0.04)
              to: -Math.round(rainWindow.width * 0.04)
              duration: Math.max(6000, (12000 + index * 1200) / root.speed)
              easing.type: Easing.InOutSine
            }
          }
        }
      }

      Repeater {
        model: root.dropCount

        Item {
          id: drop

          readonly property real seed: index + 101
          readonly property int dropLength: Math.round(26 + root.seededNoise(seed + 3) * 56)
          readonly property int dropWidth: root.seededNoise(seed + 5) > 0.86 ? 2 : 1
          readonly property int baseX: Math.round(root.seededNoise(seed + 7) * (rainWindow.width + 420)) - 210
          readonly property real dropSpeed: 0.72 + root.seededNoise(seed + 13) * 0.72
          readonly property real dropOpacity: 0.22 + root.seededNoise(seed + 17) * 0.32
          readonly property int cycleDelay: Math.round(root.seededNoise(seed + 19) * 900)
          readonly property int fallDuration: Math.max(1500, (2600 + root.seededNoise(seed + 23) * 1200) / (root.speed * dropSpeed))
          readonly property real initialProgress: root.seededNoise(seed + 11)
          readonly property real initialY: -dropLength + initialProgress * (rainWindow.height + dropLength * 2)
          readonly property int startupDuration: Math.max(80, Math.round(fallDuration * (1 - initialProgress)))
          property bool startupComplete: false

          x: Math.round(baseX + y * root.windDrift)
          y: initialY
          width: dropWidth
          height: dropLength
          opacity: dropOpacity
          rotation: root.dropRotation
          transformOrigin: Item.Center

          SequentialAnimation {
            loops: Animation.Infinite
            running: root.effectVisible && !root.reducedMotion

            NumberAnimation {
              target: drop
              property: "y"
              from: drop.startupComplete ? -drop.dropLength : drop.initialY
              to: rainWindow.height + drop.dropLength
              duration: drop.startupComplete ? drop.fallDuration : drop.startupDuration
              easing.type: Easing.Linear
            }

            ScriptAction { script: drop.startupComplete = true }
            PauseAnimation { duration: drop.cycleDelay }
          }

          Rectangle {
            anchors.fill: parent
            radius: Math.max(0.5, width / 2)
            color: Qt.rgba(root.rainColor.r, root.rainColor.g, root.rainColor.b, 0.44)
          }

          Rectangle {
            x: Math.max(0, parent.width - 1)
            y: Math.round(parent.height * 0.1)
            width: 1
            height: Math.round(parent.height * 0.56)
            radius: 0.5
            color: "#d7edf5"
            opacity: 0.08
          }

          Rectangle {
            anchors.fill: parent
            radius: Math.max(0.5, width / 2)
            gradient: Gradient {
              orientation: Gradient.Vertical
              GradientStop {
                position: 0
                color: "#00000000"
              }
              GradientStop {
                position: 0.24
                color: Qt.rgba(root.rainColor.r, root.rainColor.g, root.rainColor.b, 0.1)
              }
              GradientStop {
                position: 0.78
                color: Qt.rgba(root.rainColor.r, root.rainColor.g, root.rainColor.b, 0.46)
              }
              GradientStop {
                position: 1
                color: "#00000000"
              }
            }
          }
        }
      }

      Repeater {
        model: Math.max(24, Math.round(rainWindow.width / 34))

        Item {
          id: rainSheet

          readonly property real seed: index + 2201
          readonly property int sheetLength: Math.round(68 + root.seededNoise(seed + 3) * 104)
          readonly property int baseX: Math.round(index * 34 + root.seededNoise(seed + 5) * 46) - 80
          readonly property real sheetSpeed: 0.72 + root.seededNoise(seed + 7) * 0.5
          readonly property int fallDuration: Math.max(1900, (3600 + root.seededNoise(seed + 17) * 1500) / (root.speed * sheetSpeed))
          readonly property real initialProgress: root.seededNoise(seed + 19)
          readonly property real initialY: -sheetLength + initialProgress * (rainWindow.height + sheetLength * 2)
          readonly property int startupDuration: Math.max(80, Math.round(fallDuration * (1 - initialProgress)))
          property bool startupComplete: false

          x: Math.round(baseX + y * root.windDrift * 0.55)
          y: initialY
          width: root.seededNoise(seed + 11) > 0.82 ? 2 : 1
          height: sheetLength
          opacity: 0.1 + root.seededNoise(seed + 13) * 0.1
          rotation: root.dropRotation
          transformOrigin: Item.Center

          SequentialAnimation {
            loops: Animation.Infinite
            running: root.effectVisible && !root.reducedMotion
            NumberAnimation {
              target: rainSheet
              property: "y"
              from: rainSheet.startupComplete ? -rainSheet.sheetLength : rainSheet.initialY
              to: rainWindow.height + rainSheet.sheetLength
              duration: rainSheet.startupComplete ? rainSheet.fallDuration : rainSheet.startupDuration
              easing.type: Easing.Linear
            }
            ScriptAction { script: rainSheet.startupComplete = true }
          }

          Rectangle {
            anchors.fill: parent
            radius: Math.max(0.5, width / 2)
            color: Qt.rgba(root.rainColor.r, root.rainColor.g, root.rainColor.b, 0.36)
          }
        }
      }

      Repeater {
        model: Math.max(12, Math.round(root.dropCount * 0.18))

        Item {
          id: foregroundDrop

          readonly property real seed: index + 1301
          readonly property int dropLength: Math.round(42 + root.seededNoise(seed + 3) * 72)
          readonly property int baseX: Math.round(root.seededNoise(seed + 7) * (rainWindow.width + 520)) - 260
          readonly property real dropSpeed: 1.08 + root.seededNoise(seed + 13) * 0.82
          readonly property int cycleDelay: Math.round(root.seededNoise(seed + 19) * 650)
          readonly property int fallDuration: Math.max(1300, (2200 + root.seededNoise(seed + 23) * 900) / (root.speed * dropSpeed))
          readonly property real initialProgress: root.seededNoise(seed + 11)
          readonly property real initialY: -dropLength + initialProgress * (rainWindow.height + dropLength * 2)
          readonly property int startupDuration: Math.max(80, Math.round(fallDuration * (1 - initialProgress)))
          property bool startupComplete: false

          x: Math.round(baseX + y * root.windDrift)
          y: initialY
          width: 2
          height: dropLength
          opacity: 0.46
          rotation: root.dropRotation
          transformOrigin: Item.Center

          SequentialAnimation {
            loops: Animation.Infinite
            running: root.effectVisible && !root.reducedMotion

            NumberAnimation {
              target: foregroundDrop
              property: "y"
              from: foregroundDrop.startupComplete ? -foregroundDrop.dropLength : foregroundDrop.initialY
              to: rainWindow.height + foregroundDrop.dropLength
              duration: foregroundDrop.startupComplete ? foregroundDrop.fallDuration : foregroundDrop.startupDuration
              easing.type: Easing.Linear
            }

            ScriptAction { script: foregroundDrop.startupComplete = true }
            PauseAnimation { duration: foregroundDrop.cycleDelay }
          }

          Rectangle {
            anchors.fill: parent
            radius: 1
            color: Qt.rgba(root.rainColor.r, root.rainColor.g, root.rainColor.b, 0.48)
          }

          Rectangle {
            x: parent.width - 1
            y: Math.round(parent.height * 0.08)
            width: 1
            height: Math.round(parent.height * 0.58)
            radius: 0.5
            color: "#d7edf5"
            opacity: 0.1
          }

          Rectangle {
            anchors.fill: parent
            radius: 1
            gradient: Gradient {
              orientation: Gradient.Vertical
              GradientStop {
                position: 0
                color: "#00000000"
              }
              GradientStop {
                position: 0.18
                color: Qt.rgba(root.rainColor.r, root.rainColor.g, root.rainColor.b, 0.14)
              }
              GradientStop {
                position: 0.82
                color: Qt.rgba(root.rainColor.r, root.rainColor.g, root.rainColor.b, 0.64)
              }
              GradientStop {
                position: 1
                color: "#00000000"
              }
            }
          }
        }
      }

      Repeater {
        model: Math.round(root.dropCount * root.splashAmount * 0.18)

        Item {
          id: splash

          readonly property real seed: index + 503
          readonly property int splashWidth: Math.round(10 + root.seededNoise(seed + 3) * 28)
          readonly property int baseY: Math.round(rainWindow.height * (0.76 + root.seededNoise(seed + 5) * 0.2))

          x: Math.round(root.seededNoise(seed + 7) * rainWindow.width)
          y: baseY
          width: splashWidth
          height: 6
          opacity: 0
          scale: 0.7

          SequentialAnimation on opacity {
            loops: Animation.Infinite
            running: root.effectVisible && !root.reducedMotion

            PauseAnimation {
              duration: Math.round(450 + root.seededNoise(splash.seed + 11) * 1900)
            }

            NumberAnimation {
              from: 0
              to: 0.22
              duration: Math.max(90, 150 / root.speed)
              easing.type: Easing.OutCubic
            }

            NumberAnimation {
              from: 0.22
              to: 0
              duration: Math.max(220, 520 / root.speed)
              easing.type: Easing.OutCubic
            }
          }

          SequentialAnimation on scale {
            loops: Animation.Infinite
            running: root.effectVisible && !root.reducedMotion

            PauseAnimation {
              duration: Math.round(450 + root.seededNoise(splash.seed + 11) * 1900)
            }

            NumberAnimation {
              from: 0.7
              to: 1.35
              duration: Math.max(310, 670 / root.speed)
              easing.type: Easing.OutCubic
            }
          }

          Rectangle {
            x: 0
            y: 2
            width: parent.width
            height: 1
            radius: 1
            color: Qt.rgba(root.rainColor.r, root.rainColor.g, root.rainColor.b, 0.46)
          }

          Rectangle {
            x: Math.round(parent.width * 0.18)
            y: 4
            width: Math.round(parent.width * 0.58)
            height: 1
            radius: 1
            color: Qt.rgba(root.shadowRainColor.r, root.shadowRainColor.g, root.shadowRainColor.b, 0.36)
          }
        }
      }

      Item {
        anchors.fill: parent
        visible: root.vignette
        opacity: 0.48

        Rectangle {
          x: 0
          y: 0
          width: parent.width
          height: Math.round(parent.height * 0.18)
          gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop {
              position: 0
              color: "#30000000"
            }
            GradientStop {
              position: 1
              color: "#00000000"
            }
          }
        }

        Rectangle {
          x: 0
          y: parent.height - height
          width: parent.width
          height: Math.round(parent.height * 0.28)
          gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop {
              position: 0
              color: "#00000000"
            }
            GradientStop {
              position: 1
              color: "#46000000"
            }
          }
        }
      }
    }
  }


}
