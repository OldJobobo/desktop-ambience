import QtQuick
import QtQuick.Shapes

Item {
  id: root

  property var effectSettings: ({})
  property real globalOpacity: 1
  property bool reducedMotion: false
  property var theme: null
  property var barState: null
  property bool runtimeEnabled: true
  property real runtimeIntensity: -1
  property int cycleGeneration: 0
  property int timingGeneration: 0

  readonly property var overlaySettings: effectSettings
  readonly property bool configuredEnabled: overlaySettings.enabled === true
  readonly property real configuredIntensity: Number(overlaySettings.intensity)
  readonly property real speed: Number(overlaySettings.speed)
  readonly property int dropletCount: Math.round(Number(overlaySettings.dropletCount))
  readonly property real dropletSize: Number(overlaySettings.dropletSize)
  readonly property int formationTime: Math.round(Number(overlaySettings.formationTime))
  readonly property real fallSpeed: Number(overlaySettings.fallSpeed)
  readonly property string direction: String(overlaySettings.direction)
  readonly property real accentBlend: Number(overlaySettings.accentBlend)
  readonly property bool bloodMode: overlaySettings.bloodMode === true

  readonly property real effectiveIntensity: (runtimeIntensity >= 0
    ? clamp(runtimeIntensity, 0, 1) : configuredIntensity) * clamp(globalOpacity, 0, 1)
  readonly property bool effectVisible: configuredEnabled && runtimeEnabled && effectiveIntensity > 0.001
  readonly property string barPosition: barState ? String(barState.position || "") : ""
  readonly property real barSize: barState ? Number(barState.size) : 0
  readonly property bool usableBarGeometry: barState && barState.available === true
    && barState.hidden !== true && (barPosition === "top" || barPosition === "bottom")
    && isFinite(barSize) && barSize > 0 && barSize < height
  readonly property string effectiveDirection: direction === "down" ? "down"
    : direction === "up" ? "up"
    : (usableBarGeometry && barPosition === "bottom" ? "up" : "down")
  readonly property bool usingBarGeometry: usableBarGeometry
    && ((effectiveDirection === "down" && barPosition === "top")
      || (effectiveDirection === "up" && barPosition === "bottom"))
  readonly property real sourceEdge: effectiveDirection === "down"
    ? (usingBarGeometry ? barSize : 0)
    : (usingBarGeometry ? height - barSize : height)
  readonly property real travelDistance: effectiveDirection === "down"
    ? Math.max(0, height - sourceEdge) : Math.max(0, sourceEdge)
  readonly property bool animationsRunning: effectVisible && !reducedMotion && width > 0 && height > 0
  readonly property int allocatedDropletCount: dropletRepeater.count
  readonly property bool decorationsEnabled: dropletCount <= 40
  readonly property real firstDropletY: dropletRepeater.count > 0 && dropletRepeater.itemAt(0)
    ? dropletRepeater.itemAt(0).y + barOcclusionViewport.y : sourceEdge
  readonly property real firstDropletBeadProgress: dropletRepeater.count > 0 && dropletRepeater.itemAt(0)
    ? dropletRepeater.itemAt(0).displayBeadProgress : 0
  readonly property bool firstDropletAnimationRunning: dropletRepeater.count > 0 && dropletRepeater.itemAt(0)
    ? dropletRepeater.itemAt(0).animationActive : false
  readonly property real firstDropletShadowOpacity: dropletRepeater.count > 0 && dropletRepeater.itemAt(0)
    ? dropletRepeater.itemAt(0).renderedShadowOpacity : 0
  readonly property real firstDropletShadowOverhang: dropletRepeater.count > 0 && dropletRepeater.itemAt(0)
    ? dropletRepeater.itemAt(0).shadowOverhang : 0
  readonly property real firstDropletShadowScreenOffsetX: dropletRepeater.count > 0 && dropletRepeater.itemAt(0)
    ? dropletRepeater.itemAt(0).shadowScreenOffsetX : 0
  readonly property color themeAccent: themeColor("accent", themeColor("color14", "#88c0d0"))
  readonly property string projectedBarColor: barState ? String(barState.color || "") : ""
  readonly property color barDropletColor: opaqueColor(projectedBarColor !== ""
    ? projectedBarColor : themeColor("background", "#101315"))
  readonly property color bloodBaseColor: "#4a1014"
  readonly property color baseDropletColor: bloodMode ? bloodBaseColor : barDropletColor
  readonly property color waterColor: bloodMode
    ? bloodBaseColor : mixColor(baseDropletColor, themeAccent, accentBlend)
  readonly property color shadowColor: bloodMode
    ? Qt.rgba(waterColor.r * 0.12, waterColor.g * 0.12, waterColor.b * 0.12, 0.64)
    : Qt.rgba(waterColor.r * 0.42, waterColor.g * 0.42, waterColor.b * 0.42, 0.48)
  readonly property color reflectionColor: mixColor(waterColor,
    bloodMode ? "#c78f88" : "#ffffff", bloodMode ? 0.68 : 0.72)

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

  function opaqueColor(value) {
    var color = resolvedColor(value)
    return Qt.rgba(color.r, color.g, color.b, 1)
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
    if (payload.intensity !== undefined) runtimeIntensity = clamp(payload.intensity, 0, 1)
  }

  function close() {
    runtimeEnabled = false
  }

  function scheduleCycleRestart() {
    cycleRestart.restart()
  }

  onWidthChanged: scheduleCycleRestart()
  onHeightChanged: scheduleCycleRestart()
  onEffectiveDirectionChanged: scheduleCycleRestart()
  onSourceEdgeChanged: scheduleCycleRestart()
  onDropletSizeChanged: scheduleCycleRestart()
  onSpeedChanged: timingGeneration += 1
  onFormationTimeChanged: timingGeneration += 1
  onFallSpeedChanged: timingGeneration += 1
  Component.onCompleted: scheduleCycleRestart()

  Timer {
    id: cycleRestart
    interval: 0
    onTriggered: root.cycleGeneration += 1
  }

  Item {
    id: dripLayer
    anchors.fill: parent
    visible: root.effectVisible
    opacity: root.effectiveIntensity
    enabled: false
    clip: true

    Item {
      id: barOcclusionViewport
      x: 0
      y: root.usingBarGeometry && root.barPosition === "top" ? root.sourceEdge : 0
      width: dripLayer.width
      height: root.usingBarGeometry
        ? (root.barPosition === "top" ? dripLayer.height - root.sourceEdge : root.sourceEdge)
        : dripLayer.height
      clip: root.usingBarGeometry
    }

    Repeater {
      id: dropletRepeater
      parent: barOcclusionViewport
      model: root.dropletCount

      Item {
        id: droplet
        required property int index

        readonly property real seed: index + 701
        readonly property real laneWidth: dripLayer.width / Math.max(1, root.dropletCount)
        readonly property real sizeFactor: 0.72 + root.seededNoise(seed + 3) * 0.56
        readonly property real diameter: root.dropletSize * sizeFactor
        readonly property real jitter: (root.seededNoise(seed + 5) - 0.5) * laneWidth * 0.58
        readonly property real speedFactor: 0.76 + root.seededNoise(seed + 7) * 0.52
        readonly property real opacityFactor: 1
        readonly property int formationDuration: Math.max(120,
          Math.round(root.formationTime * (0.82 + root.seededNoise(seed + 13) * 0.36) / root.speed))
        readonly property int cycleDelay: Math.round(root.seededNoise(seed + 17) * root.formationTime * 0.7)
        readonly property real startY: root.effectiveDirection === "down"
          ? root.sourceEdge : root.sourceEdge - height
        readonly property real endY: root.effectiveDirection === "down"
          ? dripLayer.height + height : -height
        readonly property real travelLength: Math.abs(endY - startY)
        readonly property int travelDuration: Math.max(120,
          Math.round(travelLength / (root.fallSpeed * root.speed * speedFactor) * 1000))
        property real travelY: startY
        property real beadProgress: 0
        readonly property real displayBeadProgress: root.reducedMotion ? 1 : beadProgress
        property real neckProgress: 0
        readonly property real formationScale: 0.12 + displayBeadProgress * 0.88
        readonly property real stretchFactor: 1 + neckProgress * 1.05
        readonly property real visualWidth: diameter * formationScale
        readonly property real visualHeight: diameter * formationScale * stretchFactor
        readonly property real visualY: -visualHeight * 0.5
        readonly property real visualYScale: formationScale * stretchFactor / 2.05
        property string phase: "idle"
        readonly property bool animationActive: phase !== "idle"
        readonly property real renderedShadowOpacity: dropShadow.visible
          ? dropShadow.opacity * root.shadowColor.a * dripLayer.opacity : 0
        readonly property real shadowOverhang: dropShadow.signedOffset
        readonly property real shadowScreenOffsetX: root.effectiveDirection === "up"
          ? -dropShadow.signedOffset : dropShadow.signedOffset
        property int observedGeneration: root.cycleGeneration
        property int observedTimingGeneration: root.timingGeneration

        function resetVisualState() {
          travelY = startY
          beadProgress = 0
          neckProgress = 0
        }

        function stopAnimation() {
          cycleDelayTimer.stop()
          resetDelayTimer.stop()
          beadAnimation.stop()
          neckAnimation.stop()
          travelAnimation.stop()
          phase = "idle"
        }

        function beginCycleDelay() {
          phase = "delay"
          cycleDelayTimer.interval = Math.max(1, cycleDelay)
          cycleDelayTimer.restart()
        }

        function startFormation() {
          phase = "formation"
          beadAnimation.from = beadProgress
          beadAnimation.duration = Math.max(1,
            Math.round(formationDuration * 0.72 * (1 - beadProgress)))
          beadAnimation.restart()
        }

        function startStretch() {
          phase = "stretch"
          neckAnimation.from = neckProgress
          neckAnimation.duration = Math.max(1,
            Math.round(formationDuration * 0.28 * (1 - neckProgress)))
          neckAnimation.restart()
        }

        function startTravel() {
          phase = "travel"
          travelAnimation.from = travelY
          travelAnimation.duration = Math.max(1, Math.round(
            Math.abs(endY - travelY) / (root.fallSpeed * root.speed * speedFactor) * 1000))
          travelAnimation.restart()
        }

        function beginResetDelay() {
          phase = "resetDelay"
          resetDelayTimer.interval = 160 + Math.round(root.seededNoise(seed + 19) * 640)
          resetDelayTimer.restart()
        }

        function retimeActivePhase() {
          if (!root.animationsRunning) return
          if (phase === "formation") {
            beadAnimation.stop()
            startFormation()
          } else if (phase === "stretch") {
            neckAnimation.stop()
            startStretch()
          } else if (phase === "travel") {
            travelAnimation.stop()
            startTravel()
          }
        }

        function syncAnimation() {
          stopAnimation()
          resetVisualState()
          if (root.animationsRunning) beginCycleDelay()
        }

        x: root.clamp((index + 0.5) * laneWidth - diameter / 2 + jitter,
          0, Math.max(0, dripLayer.width - width))
        y: (root.reducedMotion ? startY : travelY) - barOcclusionViewport.y
        width: diameter
        height: diameter * 2.4
        opacity: opacityFactor
        rotation: root.effectiveDirection === "up" ? 180 : 0
        transformOrigin: Item.Center

        onObservedGenerationChanged: syncAnimation()
        onObservedTimingGenerationChanged: retimeActivePhase()
        Component.onCompleted: syncAnimation()

        Connections {
          target: root
          function onAnimationsRunningChanged() { droplet.syncAnimation() }
        }

        Timer {
          id: cycleDelayTimer
          repeat: false
          onTriggered: droplet.startFormation()
        }

        NumberAnimation {
          id: beadAnimation
          target: droplet
          property: "beadProgress"
          to: 1
          easing.type: Easing.OutCubic
          onFinished: droplet.startStretch()
        }

        NumberAnimation {
          id: neckAnimation
          target: droplet
          property: "neckProgress"
          to: 1
          easing.type: Easing.InCubic
          onFinished: droplet.startTravel()
        }

        NumberAnimation {
          id: travelAnimation
          target: droplet
          property: "travelY"
          to: droplet.endY
          easing.type: Easing.InQuad
          onFinished: droplet.beginResetDelay()
        }

        Timer {
          id: resetDelayTimer
          repeat: false
          onTriggered: {
            droplet.resetVisualState()
            if (root.animationsRunning) droplet.beginCycleDelay()
            else droplet.phase = "idle"
          }
        }

        Shape {
          id: dropShadow
          readonly property real offset: Math.max(1, Math.min(root.bloodMode ? 2.8 : 2.2,
            droplet.diameter * (root.bloodMode ? 0.15 : 0.12)))
          // The whole delegate rotates 180 degrees for upward travel, so keeping
          // the local offset positive reverses its final screen-space direction.
          readonly property real signedOffset: offset

          z: 1
          visible: root.decorationsEnabled
          x: signedOffset
          y: droplet.visualY + signedOffset
          width: droplet.diameter
          height: droplet.diameter * 2.05
          opacity: dropShape.opacity
          antialiasing: true
          transform: Scale {
            origin.x: dropShadow.width / 2
            origin.y: 0
            xScale: droplet.formationScale
            yScale: droplet.visualYScale
          }

          ShapePath {
            strokeWidth: 0
            fillColor: root.shadowColor
            startX: dropShadow.width / 2
            startY: 0

            PathCubic {
              control1X: dropShadow.width * 0.56
              control1Y: dropShadow.height * 0.18
              control2X: dropShadow.width
              control2Y: dropShadow.height * 0.42
              x: dropShadow.width
              y: dropShadow.height * 0.68
            }
            PathCubic {
              control1X: dropShadow.width
              control1Y: dropShadow.height * 0.88
              control2X: dropShadow.width * 0.78
              control2Y: dropShadow.height
              x: dropShadow.width / 2
              y: dropShadow.height
            }
            PathCubic {
              control1X: dropShadow.width * 0.22
              control1Y: dropShadow.height
              control2X: 0
              control2Y: dropShadow.height * 0.88
              x: 0
              y: dropShadow.height * 0.68
            }
            PathCubic {
              control1X: 0
              control1Y: dropShadow.height * 0.42
              control2X: dropShadow.width * 0.44
              control2Y: dropShadow.height * 0.18
              x: dropShadow.width / 2
              y: 0
            }
          }
        }

        Shape {
          id: dropReflection
          z: 3
          visible: root.decorationsEnabled
          x: (droplet.width - droplet.visualWidth) / 2 + droplet.visualWidth * 0.19
          y: droplet.visualY + droplet.visualHeight * 0.48
          width: Math.max(2.4, droplet.visualWidth * 0.3)
          height: Math.max(3.8, Math.min(droplet.visualWidth * 0.5, droplet.visualHeight * 0.25))
          rotation: 38
          opacity: dropShape.opacity
            * root.clamp((droplet.displayBeadProgress - 0.28) / 0.72, 0, 1)
            * (root.bloodMode ? 0.42 : 0.3)
          antialiasing: true

          ShapePath {
            strokeWidth: 0
            fillColor: root.reflectionColor
            startX: dropReflection.width * 0.22
            startY: dropReflection.height * 0.08

            PathCubic {
              control1X: dropReflection.width * 0.05
              control1Y: dropReflection.height * 0.22
              control2X: dropReflection.width * 0.08
              control2Y: dropReflection.height * 0.55
              x: dropReflection.width * 0.34
              y: dropReflection.height * 0.75
            }
            PathCubic {
              control1X: dropReflection.width * 0.48
              control1Y: dropReflection.height * 0.86
              control2X: dropReflection.width * 0.68
              control2Y: dropReflection.height * 0.94
              x: dropReflection.width * 0.86
              y: dropReflection.height * 0.97
            }
            PathCubic {
              control1X: dropReflection.width * 0.72
              control1Y: dropReflection.height * 0.86
              control2X: dropReflection.width * 0.58
              control2Y: dropReflection.height * 0.76
              x: dropReflection.width * 0.48
              y: dropReflection.height * 0.62
            }
            PathCubic {
              control1X: dropReflection.width * 0.31
              control1Y: dropReflection.height * 0.43
              control2X: dropReflection.width * 0.33
              control2Y: dropReflection.height * 0.25
              x: dropReflection.width * 0.46
              y: dropReflection.height * 0.13
            }
            PathCubic {
              control1X: dropReflection.width * 0.58
              control1Y: dropReflection.height * 0.01
              control2X: dropReflection.width * 0.34
              control2Y: -dropReflection.height * 0.04
              x: dropReflection.width * 0.22
              y: dropReflection.height * 0.08
            }
          }
        }

        Shape {
          id: dropShape
          z: 2

          anchors.horizontalCenter: parent.horizontalCenter
          y: droplet.visualY
          width: droplet.diameter
          height: droplet.diameter * 2.05
          opacity: root.reducedMotion ? 1 : Math.min(1, droplet.beadProgress * 1.8)
          antialiasing: true
          transform: Scale {
            origin.x: dropShape.width / 2
            origin.y: 0
            xScale: droplet.formationScale
            yScale: droplet.visualYScale
          }

          ShapePath {
            strokeWidth: 0
            fillColor: root.waterColor
            startX: dropShape.width / 2
            startY: 0

            PathCubic {
              control1X: dropShape.width * 0.56
              control1Y: dropShape.height * 0.18
              control2X: dropShape.width
              control2Y: dropShape.height * 0.42
              x: dropShape.width
              y: dropShape.height * 0.68
            }
            PathCubic {
              control1X: dropShape.width
              control1Y: dropShape.height * 0.88
              control2X: dropShape.width * 0.78
              control2Y: dropShape.height
              x: dropShape.width / 2
              y: dropShape.height
            }
            PathCubic {
              control1X: dropShape.width * 0.22
              control1Y: dropShape.height
              control2X: 0
              control2Y: dropShape.height * 0.88
              x: 0
              y: dropShape.height * 0.68
            }
            PathCubic {
              control1X: 0
              control1Y: dropShape.height * 0.42
              control2X: dropShape.width * 0.44
              control2Y: dropShape.height * 0.18
              x: dropShape.width / 2
              y: 0
            }
          }
        }
      }
    }
  }
}
