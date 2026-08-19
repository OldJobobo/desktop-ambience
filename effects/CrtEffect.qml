import QtQuick
import QtQuick.Effects
import QtQuick.Shapes

Item {
  id: root

  property var effectSettings: ({})
  property real globalOpacity: 1
  property bool reducedMotion: false
  property bool runtimeEnabled: true
  property real runtimeIntensity: -1
  property bool foregroundOverlay: false
  property int noiseTick: 0
  property real bloomPulse: 0
  property int bloomPulseCycle: 0
  property int bloomPulseDelay: 14000

  readonly property var overlaySettings: effectSettings
  readonly property bool configuredEnabled: overlaySettings.enabled === true
  readonly property bool effectVisible: configuredEnabled && runtimeEnabled && effectiveIntensity > 0.001
  readonly property real configuredIntensity: Number(overlaySettings.intensity)
  readonly property real effectiveIntensity: (runtimeIntensity >= 0 ? clamp(runtimeIntensity, 0, 1) : configuredIntensity) * clamp(globalOpacity, 0, 1)
  readonly property real speed: Number(overlaySettings.speed)
  readonly property int scanlineSpacing: Math.round(Number(overlaySettings.scanlineSpacing))
  readonly property int staticBandHeight: Math.round(Number(overlaySettings.staticBandHeight))
  readonly property real staticAmount: Number(overlaySettings.staticAmount)
  readonly property real glowAmount: Number(overlaySettings.glowAmount)
  readonly property bool bloomPulseEnabled: overlaySettings.bloomPulse === true
  readonly property real bloomPulseAmount: Number(overlaySettings.bloomPulseAmount)
  readonly property int bloomPulseInterval: Math.round(Number(overlaySettings.bloomPulseInterval))
  readonly property real bloomPulseOpacity: bloomPulseEnabled ? bloomPulse * bloomPulseAmount : 0
  readonly property bool distortion: overlaySettings.distortion === true
  readonly property real distortionAmount: Number(overlaySettings.distortionAmount)
  readonly property bool vignette: overlaySettings.vignette === true

  function clamp(value, minimum, maximum) {
    var numeric = Number(value)
    if (isNaN(numeric)) return minimum
    return Math.max(minimum, Math.min(maximum, numeric))
  }


  function parsePayload(payloadJson) {
    try {
      return payloadJson ? JSON.parse(payloadJson) : {}
    } catch (error) {
      return {}
    }
  }

  function seededNoise(seed) {
    var value = Math.sin(seed * 12.9898 + root.noiseTick * 78.233) * 43758.5453
    return value - Math.floor(value)
  }

  function stableNoise(seed) {
    var value = Math.sin(seed * 12.9898) * 43758.5453
    return value - Math.floor(value)
  }

  function bloomPulseDelayForCycle(cycle) {
    return Math.round(bloomPulseInterval * (0.72 + stableNoise(cycle + 503) * 0.82))
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

  Timer {
    interval: Math.max(70, 180 / root.speed)
    repeat: true
    running: root.effectVisible && !root.reducedMotion && root.staticAmount > 0
    onTriggered: root.noiseTick += 1
  }

  SequentialAnimation {
    id: bloomPulseAnimation

    loops: Animation.Infinite
    running: root.effectVisible && !root.reducedMotion && root.bloomPulseEnabled && root.bloomPulseAmount > 0.001
    onRunningChanged: if (!running) root.bloomPulse = 0

    PauseAnimation {
      duration: root.bloomPulseDelay
    }
    NumberAnimation {
      target: root
      property: "bloomPulse"
      from: 0
      to: 0.42
      duration: Math.max(1900, 3600 / root.speed)
      easing.type: Easing.InSine
    }
    NumberAnimation {
      target: root
      property: "bloomPulse"
      from: 0.42
      to: 1
      duration: Math.max(480, 940 / root.speed)
      easing.type: Easing.InOutSine
    }
    NumberAnimation {
      target: root
      property: "bloomPulse"
      from: 1
      to: 0
      duration: Math.max(2600, 5000 / root.speed)
      easing.type: Easing.OutSine
    }
    ScriptAction {
      script: {
        root.bloomPulse = 0
        root.bloomPulseCycle += 1
        root.bloomPulseDelay = root.bloomPulseDelayForCycle(root.bloomPulseCycle)
      }
    }
  }

  Item {
    id: crtWindow

    anchors.fill: parent
    visible: root.effectVisible


    Item {
      id: effect

      anchors.fill: parent
      enabled: false
      opacity: root.effectiveIntensity

      Rectangle {
        anchors.fill: parent
        color: "#c8f4ff"
        opacity: root.glowAmount * 0.035 + root.bloomPulseOpacity * 0.052
      }

      Item {
        id: bloomPulseWash

        anchors.fill: parent
        visible: root.bloomPulseOpacity > 0.001
        opacity: root.bloomPulseOpacity
        layer.enabled: visible
        layer.smooth: true
        layer.effect: MultiEffect {
          blurEnabled: true
          blurMax: 72
          blur: 0.82
          autoPaddingEnabled: true
        }

        Rectangle {
          anchors.fill: parent
          color: "#78f7ff"
          opacity: 0.105
        }

        Rectangle {
          x: Math.round(parent.width * 0.04)
          y: 0
          width: Math.round(parent.width * 0.92)
          height: parent.height
          gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop {
              position: 0
              color: "#00000000"
            }
            GradientStop {
              position: 0.5
              color: "#6878f7ff"
            }
            GradientStop {
              position: 1
              color: "#00000000"
            }
          }
        }

        Rectangle {
          x: 0
          y: Math.round(parent.height * 0.22)
          width: parent.width
          height: Math.round(parent.height * 0.56)
          gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop {
              position: 0
              color: "#00000000"
            }
            GradientStop {
              position: 0.46
              color: "#4f78f7ff"
            }
            GradientStop {
              position: 0.62
              color: "#1effd56a"
            }
            GradientStop {
              position: 1
              color: "#00000000"
            }
          }
        }
      }

      Item {
        id: scanlineCrawl

        anchors.fill: parent
        y: -root.scanlineSpacing

        NumberAnimation on y {
          from: -root.scanlineSpacing
          to: 0
          duration: Math.max(420, 1500 / root.speed)
          loops: Animation.Infinite
          running: root.effectVisible && !root.reducedMotion
        }

        Repeater {
          model: Math.max(0, Math.ceil(crtWindow.height / root.scanlineSpacing) + 3)

          Rectangle {
            x: 0
            y: index * root.scanlineSpacing
            width: crtWindow.width
            height: 1
            color: index % 2 === 0 ? "#dff8ff" : "#020406"
            opacity: index % 2 === 0 ? 0.13 : 0.16
          }
        }
      }

      Item {
        id: staticBand

        x: 0
        y: -height
        width: crtWindow.width
        height: root.staticBandHeight
        opacity: root.staticAmount

        SequentialAnimation on y {
          loops: Animation.Infinite
          running: root.effectVisible && !root.reducedMotion

          PauseAnimation {
            duration: Math.max(1000, 5200 / root.speed)
          }

          NumberAnimation {
            from: -staticBand.height
            to: crtWindow.height + staticBand.height
            duration: Math.max(2600, 9000 / root.speed)
            easing.type: Easing.InOutSine
          }
        }

        Rectangle {
          anchors.fill: parent
          color: "transparent"
          gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop {
              position: 0
              color: "#00000000"
            }
            GradientStop {
              position: 0.18
              color: "#10000000"
            }
            GradientStop {
              position: 0.42
              color: "#18ffffff"
            }
            GradientStop {
              position: 0.58
              color: "#20ffffff"
            }
            GradientStop {
              position: 0.82
              color: "#16000000"
            }
            GradientStop {
              position: 1
              color: "#00000000"
            }
          }
        }

        Repeater {
          model: 34

          Rectangle {
            readonly property real seed: index + 71

            x: Math.round(root.seededNoise(seed) * staticBand.width)
            y: Math.round(root.seededNoise(seed + 13) * staticBand.height)
            width: Math.round(36 + root.seededNoise(seed + 23) * 220)
            height: root.seededNoise(seed + 31) > 0.78 ? 2 : 1
            color: root.seededNoise(seed + 43) > 0.48 ? "#ffffff" : "#080b0f"
            opacity: 0.05 + root.seededNoise(seed + 53) * 0.18
          }
        }

        Rectangle {
          x: 0
          y: Math.round(parent.height * 0.5)
          width: parent.width
          height: 2
          color: "#ffffff"
          opacity: 0.14
        }
      }

      Repeater {
        model: Math.round(22 + root.staticAmount * 68)

        Rectangle {
          readonly property real seed: index + 211

          x: Math.round(root.seededNoise(seed + 1) * crtWindow.width)
          y: Math.round(root.seededNoise(seed + 2) * crtWindow.height)
          width: root.seededNoise(seed + 3) > 0.86 ? 10 : 2
          height: 1
          color: root.seededNoise(seed + 5) > 0.55 ? "#ffffff" : "#030507"
          opacity: root.staticAmount * root.seededNoise(seed + 7) * 0.22
        }
      }

      Repeater {
        model: 3

        Rectangle {
          readonly property bool cyanLayer: index === 0
          readonly property bool warmLayer: index === 1

          x: cyanLayer ? -1 : warmLayer ? 1 : 0
          y: 0
          width: crtWindow.width + 2
          height: crtWindow.height
          color: cyanLayer ? "#70f8ff" : warmLayer ? "#ffd66a" : "#ffffff"
          opacity: root.glowAmount * (cyanLayer || warmLayer ? 0.018 : 0.012) + root.bloomPulseOpacity * (cyanLayer ? 0.13 : warmLayer ? 0.032 : 0.022)
        }
      }

      Item {
        id: curvedGlassDistortion

        anchors.fill: parent
        visible: root.foregroundOverlay && root.distortion && root.distortionAmount > 0.001
        opacity: root.distortionAmount

        Rectangle {
          x: 0
          y: 0
          width: Math.round(parent.width * 0.16)
          height: parent.height
          gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop {
              position: 0
              color: "#26000000"
            }
            GradientStop {
              position: 0.42
              color: "#10000000"
            }
            GradientStop {
              position: 1
              color: "#00000000"
            }
          }
        }

        Rectangle {
          x: parent.width - width
          y: 0
          width: Math.round(parent.width * 0.16)
          height: parent.height
          gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop {
              position: 0
              color: "#00000000"
            }
            GradientStop {
              position: 0.58
              color: "#10000000"
            }
            GradientStop {
              position: 1
              color: "#26000000"
            }
          }
        }

        Repeater {
          model: 6

          Item {
            id: bowLine

            readonly property real seed: index + 1
            readonly property real baseY: crtWindow.height * (0.12 + index * 0.152)
            readonly property real bow: (index % 2 === 0 ? 1 : -1) * crtWindow.height * (0.006 + index * 0.0015)
            property real phase: 0

            anchors.fill: parent
            opacity: 0.2 + index * 0.025

            NumberAnimation on phase {
              from: -1
              to: 1
              duration: Math.max(2600, (6200 + index * 900) / root.speed)
              loops: Animation.Infinite
              easing.type: Easing.InOutSine
              running: root.effectVisible && !root.reducedMotion && curvedGlassDistortion.visible
            }

            Shape {
              anchors.fill: parent
              preferredRendererType: Shape.CurveRenderer

              ShapePath {
                fillColor: "transparent"
                strokeColor: index % 2 === 0 ? "#55d7fbff" : "#2a000000"
                strokeWidth: index % 2 === 0 ? 1 : 2
                capStyle: ShapePath.RoundCap
                startX: -16
                startY: bowLine.baseY + bowLine.phase * 2

                PathCubic {
                  control1X: crtWindow.width * 0.25
                  control1Y: bowLine.baseY + bowLine.bow + bowLine.phase * 5
                  control2X: crtWindow.width * 0.75
                  control2Y: bowLine.baseY + bowLine.bow - bowLine.phase * 5
                  x: crtWindow.width + 16
                  y: bowLine.baseY - bowLine.phase * 2
                }
              }
            }
          }
        }

        Rectangle {
          x: Math.round(parent.width * 0.5 - width * 0.5)
          y: 0
          width: Math.round(parent.width * 0.58)
          height: parent.height
          color: "#e8fbff"
          opacity: 0.018
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
          height: Math.round(parent.height * 0.18)
          gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop {
              position: 0
              color: "#42000000"
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
          height: Math.round(parent.height * 0.24)
          gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop {
              position: 0
              color: "#00000000"
            }
            GradientStop {
              position: 1
              color: "#52000000"
            }
          }
        }

        Rectangle {
          x: 0
          y: 0
          width: Math.round(parent.width * 0.12)
          height: parent.height
          gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop {
              position: 0
              color: "#42000000"
            }
            GradientStop {
              position: 1
              color: "#00000000"
            }
          }
        }

        Rectangle {
          x: parent.width - width
          y: 0
          width: Math.round(parent.width * 0.12)
          height: parent.height
          gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop {
              position: 0
              color: "#00000000"
            }
            GradientStop {
              position: 1
              color: "#42000000"
            }
          }
        }
      }
    }
  }


}
