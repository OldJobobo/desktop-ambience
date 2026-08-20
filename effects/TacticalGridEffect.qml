import QtQuick

Item {
  id: root

  property var effectSettings: ({})
  property real globalOpacity: 1
  property bool reducedMotion: false
  property var theme: null
  property var targetScreen: null
  property var cursorTracker: null
  property bool runtimeEnabled: true
  property real runtimeIntensity: -1
  property real pulsePhase: 0

  readonly property var overlaySettings: effectSettings
  readonly property bool configuredEnabled: overlaySettings.enabled === true
  readonly property real configuredIntensity: Number(overlaySettings.intensity)
  readonly property real effectiveIntensity: (runtimeIntensity >= 0
    ? clamp(runtimeIntensity, 0, 1) : configuredIntensity) * clamp(globalOpacity, 0, 1)
  readonly property bool effectVisible: configuredEnabled && runtimeEnabled && effectiveIntensity > 0.001
  readonly property real speed: Number(overlaySettings.speed)
  readonly property int gridSpacing: Math.round(Number(overlaySettings.gridSpacing))
  readonly property real gridLineWidth: Number(overlaySettings.gridLineWidth)
  readonly property real gridOpacity: Number(overlaySettings.gridOpacity)
  readonly property real guideOpacity: Number(overlaySettings.guideOpacity)
  readonly property bool parallaxEnabled: overlaySettings.parallaxEnabled === true
  readonly property real mouseInfluence: Number(overlaySettings.mouseInfluence)
  readonly property bool mouseGuides: overlaySettings.mouseGuides === true
  readonly property string reticleStyle: String(overlaySettings.reticleStyle)
  readonly property int reticleSize: Math.round(Number(overlaySettings.reticleSize))
  readonly property bool reticlePulse: overlaySettings.reticlePulse === true
  readonly property string colorRole: String(overlaySettings.colorRole)

  readonly property bool hasCursorSample: cursorTracker && cursorTracker.hasCursorSample === true
  readonly property real rawCursorX: cursorTracker ? Number(cursorTracker.cursorX) : -1
  readonly property real rawCursorY: cursorTracker ? Number(cursorTracker.cursorY) : -1
  readonly property real cursorX: cursorTracker
    ? Number(cursorTracker.displayCursorX !== undefined ? cursorTracker.displayCursorX : rawCursorX) : -1
  readonly property real cursorY: cursorTracker
    ? Number(cursorTracker.displayCursorY !== undefined ? cursorTracker.displayCursorY : rawCursorY) : -1
  readonly property real screenOriginX: screenOrigin(targetScreen, "x")
  readonly property real screenOriginY: screenOrigin(targetScreen, "y")
  readonly property real rawCursorLocalX: rawCursorX - screenOriginX
  readonly property real rawCursorLocalY: rawCursorY - screenOriginY
  readonly property real cursorLocalX: cursorX - screenOriginX
  readonly property real cursorLocalY: cursorY - screenOriginY
  readonly property bool cursorInsideOutput: hasCursorSample
    && rawCursorLocalX >= 0 && rawCursorLocalY >= 0
    && rawCursorLocalX < width && rawCursorLocalY < height
  readonly property real normalizedCursorX: width > 0 ? clamp((cursorLocalX / width) * 2 - 1, -1, 1) : 0
  readonly property real normalizedCursorY: height > 0 ? clamp((cursorLocalY / height) * 2 - 1, -1, 1) : 0
  readonly property real parallaxOffsetX: parallaxEnabled && !reducedMotion && cursorInsideOutput
    ? -normalizedCursorX * gridSpacing * mouseInfluence * 0.6 : 0
  readonly property real parallaxOffsetY: parallaxEnabled && !reducedMotion && cursorInsideOutput
    ? -normalizedCursorY * gridSpacing * mouseInfluence * 0.6 : 0
  readonly property real reticleScale: reticlePulse && !reducedMotion
    ? 1 + Math.sin(pulsePhase * Math.PI * 2) * 0.045 : 1
  readonly property real reticlePulseOpacity: reticlePulse && !reducedMotion
    ? 0.88 + (Math.sin(pulsePhase * Math.PI * 2) + 1) * 0.06 : 1
  readonly property color effectColor: themeColor(colorRole, "#88c0d0")
  readonly property real renderedGridX: gridLayer.x
  readonly property real renderedGridY: gridLayer.y

  function clamp(value, minimum, maximum) {
    var numeric = Number(value)
    if (isNaN(numeric)) return minimum
    return Math.max(minimum, Math.min(maximum, numeric))
  }

  function screenOrigin(screen, axis) {
    var value = screen && screen[axis] !== undefined ? Number(screen[axis]) : 0
    return isNaN(value) ? 0 : value
  }

  function themeColor(name, fallbackColor) {
    return theme && theme.colorFor ? theme.colorFor(name, fallbackColor) : fallbackColor
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
    running: root.effectVisible && root.cursorInsideOutput && root.guideOpacity > 0.001
      && root.reticlePulse && !root.reducedMotion
    onTriggered: root.pulsePhase = (root.pulsePhase + frameTime * root.speed * 0.65) % 1
  }

  Item {
    id: tacticalLayer
    anchors.fill: parent
    visible: root.effectVisible
    opacity: root.effectiveIntensity
    enabled: false
    clip: true

    Item {
      id: gridLayer
      width: parent.width
      height: parent.height
      x: root.parallaxOffsetX
      y: root.parallaxOffsetY
      opacity: root.gridOpacity

      Behavior on x {
        enabled: !root.reducedMotion
        NumberAnimation {
          duration: Math.max(45, Math.round(150 / Math.max(0.15, root.speed)))
          easing.type: Easing.OutCubic
        }
      }

      Behavior on y {
        enabled: !root.reducedMotion
        NumberAnimation {
          duration: Math.max(45, Math.round(150 / Math.max(0.15, root.speed)))
          easing.type: Easing.OutCubic
        }
      }

      Repeater {
        model: Math.max(0, Math.ceil(tacticalLayer.width / Math.max(1, root.gridSpacing)) + 3)

        Rectangle {
          required property int index
          x: (index - 1) * root.gridSpacing
          y: -root.gridSpacing
          width: root.gridLineWidth
          height: tacticalLayer.height + root.gridSpacing * 2
          color: root.effectColor
          opacity: index % 4 === 1 ? 0.92 : 0.56
        }
      }

      Repeater {
        model: Math.max(0, Math.ceil(tacticalLayer.height / Math.max(1, root.gridSpacing)) + 3)

        Rectangle {
          required property int index
          x: -root.gridSpacing
          y: (index - 1) * root.gridSpacing
          width: tacticalLayer.width + root.gridSpacing * 2
          height: root.gridLineWidth
          color: root.effectColor
          opacity: index % 4 === 1 ? 0.92 : 0.56
        }
      }
    }

    Item {
      id: targetingLayer
      anchors.fill: parent
      visible: root.cursorInsideOutput
      opacity: root.guideOpacity

      Rectangle {
        visible: root.mouseGuides
        x: 0
        y: Math.round(root.cursorLocalY - height / 2)
        width: targetingLayer.width
        height: Math.max(1, root.gridLineWidth)
        color: root.effectColor
        opacity: 0.72
      }

      Rectangle {
        visible: root.mouseGuides
        x: Math.round(root.cursorLocalX - width / 2)
        y: 0
        width: Math.max(1, root.gridLineWidth)
        height: targetingLayer.height
        color: root.effectColor
        opacity: 0.72
      }

      Item {
        id: reticleHost
        x: root.cursorLocalX - width / 2
        y: root.cursorLocalY - height / 2
        width: root.reticleSize
        height: root.reticleSize
        scale: root.reticleScale
        opacity: root.reticlePulseOpacity
        transformOrigin: Item.Center

        Loader {
          anchors.fill: parent
          sourceComponent: root.reticleStyle === "crosshair" ? crosshairReticle
            : root.reticleStyle === "ring" ? ringReticle
            : root.reticleStyle === "diamond" ? diamondReticle
            : bracketReticle
        }
      }
    }
  }

  Component {
    id: crosshairReticle
    Item {
      readonly property real stroke: Math.max(1, root.gridLineWidth * 1.35)
      readonly property real gap: Math.max(3, width * 0.14)
      Rectangle { x: 0; y: parent.height / 2 - parent.stroke / 2; width: parent.width / 2 - parent.gap; height: parent.stroke; color: root.effectColor }
      Rectangle { x: parent.width / 2 + parent.gap; y: parent.height / 2 - parent.stroke / 2; width: parent.width / 2 - parent.gap; height: parent.stroke; color: root.effectColor }
      Rectangle { x: parent.width / 2 - parent.stroke / 2; y: 0; width: parent.stroke; height: parent.height / 2 - parent.gap; color: root.effectColor }
      Rectangle { x: parent.width / 2 - parent.stroke / 2; y: parent.height / 2 + parent.gap; width: parent.stroke; height: parent.height / 2 - parent.gap; color: root.effectColor }
      Rectangle { anchors.centerIn: parent; width: parent.stroke * 1.5; height: width; radius: width / 2; color: root.effectColor }
    }
  }

  Component {
    id: bracketReticle
    Item {
      readonly property real stroke: Math.max(1, root.gridLineWidth * 1.35)
      readonly property real arm: Math.max(5, width * 0.24)
      Rectangle { x: 0; y: 0; width: parent.arm; height: parent.stroke; color: root.effectColor }
      Rectangle { x: 0; y: 0; width: parent.stroke; height: parent.arm; color: root.effectColor }
      Rectangle { x: parent.width - parent.arm; y: 0; width: parent.arm; height: parent.stroke; color: root.effectColor }
      Rectangle { x: parent.width - parent.stroke; y: 0; width: parent.stroke; height: parent.arm; color: root.effectColor }
      Rectangle { x: 0; y: parent.height - parent.stroke; width: parent.arm; height: parent.stroke; color: root.effectColor }
      Rectangle { x: 0; y: parent.height - parent.arm; width: parent.stroke; height: parent.arm; color: root.effectColor }
      Rectangle { x: parent.width - parent.arm; y: parent.height - parent.stroke; width: parent.arm; height: parent.stroke; color: root.effectColor }
      Rectangle { x: parent.width - parent.stroke; y: parent.height - parent.arm; width: parent.stroke; height: parent.arm; color: root.effectColor }
    }
  }

  Component {
    id: ringReticle
    Item {
      Rectangle {
        anchors.centerIn: parent
        width: parent.width
        height: parent.height
        radius: width / 2
        color: "transparent"
        border.color: root.effectColor
        border.width: Math.max(1, root.gridLineWidth * 1.35)
      }
      Rectangle { anchors.centerIn: parent; width: Math.max(2, root.gridLineWidth * 2); height: width; radius: width / 2; color: root.effectColor }
    }
  }

  Component {
    id: diamondReticle
    Item {
      Rectangle {
        anchors.centerIn: parent
        width: parent.width * 0.68
        height: width
        rotation: 45
        color: "transparent"
        border.color: root.effectColor
        border.width: Math.max(1, root.gridLineWidth * 1.35)
      }
      Rectangle { anchors.centerIn: parent; width: Math.max(2, root.gridLineWidth * 2); height: width; radius: width / 2; color: root.effectColor }
    }
  }
}
