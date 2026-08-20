import QtQuick

Item {
  id: root

  property string styleName: "snow"
  property bool effectVisible: false
  property real effectiveIntensity: 0
  property bool reducedMotion: false
  property real speed: 1
  property int dropCount: 0
  property real slant: 0
  property real flakeSize: 6
  property real flutterAmount: 0.58
  property string flakeDetail: "mixed"
  property bool vignette: false
  property color snowColor: "#e8f2f8"
  property color snowShadowColor: "#71808c"
  property real clockTime: 0
  property real accumulatedFrameTime: 0
  property int simulationRevision: 0
  property int clockUpdateCount: 0
  signal styleDestroyed(string name)

  readonly property int targetUpdatesPerSecond: 30
  readonly property real maximumFrameDelta: 0.05
  readonly property bool autonomousMotionRunning: effectVisible && !reducedMotion
  readonly property bool visualLayerEnabled: snowLayer.enabled
  readonly property real visualTime: autonomousMotionRunning ? clockTime : 0
  readonly property int flakeCount: flakeRepeater.count
  readonly property int crystalFlakeCount: countCrystals()
  readonly property int detailPrimitiveCount: flakeCount + crystalFlakeCount * 3
  readonly property int boundedParticleCount: flakeCount
  readonly property int animationObjectCount: 0
  readonly property int runningAnimationCount: 0
  readonly property int clockObjectCount: 1
  readonly property int runningClockCount: autonomousMotionRunning ? 1 : 0

  function seededNoise(seed) {
    var value = Math.sin(seed * 12.9898) * 43758.5453
    return value - Math.floor(value)
  }

  function positiveModulo(value, modulus) {
    if (modulus <= 0) return 0
    return ((value % modulus) + modulus) % modulus
  }

  function isCrystalIndex(index) {
    if (flakeDetail === "crystal") return true
    if (flakeDetail !== "mixed") return false
    return seededNoise(Number(index) + 1901) > 0.72
  }

  function countCrystals() {
    if (flakeDetail === "crystal") return Math.max(0, dropCount)
    if (flakeDetail !== "mixed") return 0
    var count = 0
    for (var index = 0; index < Math.max(0, dropCount); index++)
      if (isCrystalIndex(index)) count += 1
    return count
  }

  function flakeObject(index) {
    return flakeRepeater.itemAt(Math.round(Number(index)))
  }

  function flakeSnapshot(index) {
    var flake = flakeObject(index)
    if (!flake) return null
    return {
      index: flake.index,
      depthBand: flake.depthBand,
      depthScale: flake.depthScale,
      initialProgress: flake.initialProgress,
      initialY: flake.initialY,
      currentProgress: flake.currentProgress,
      currentX: flake.currentX,
      currentY: flake.currentY,
      baseX: flake.baseX,
      diameter: flake.diameter,
      flakeOpacity: flake.flakeOpacity,
      fallSpeed: flake.fallSpeed,
      flutterPhase: flake.flutterPhase,
      flutterRadius: flake.flutterRadius,
      flutterOffset: flake.flutterOffset,
      rotationSpeed: flake.rotationSpeed,
      rotation: flake.rotation,
      isCrystal: flake.isCrystal,
      visible: flake.visible,
      enabled: flake.enabled
    }
  }

  function acceptFrame(frameTime) {
    if (!autonomousMotionRunning) return
    var interval = 1 / targetUpdatesPerSecond
    accumulatedFrameTime = Math.min(maximumFrameDelta,
      accumulatedFrameTime + Math.max(0, Math.min(maximumFrameDelta, Number(frameTime))))
    if (accumulatedFrameTime < interval - 0.001) return
    clockTime += accumulatedFrameTime
    accumulatedFrameTime = 0
    simulationRevision += 1
    clockUpdateCount += 1
  }

  onAutonomousMotionRunningChanged: {
    accumulatedFrameTime = 0
    simulationRevision += 1
  }

  Component.onDestruction: styleDestroyed(styleName)

  FrameAnimation {
    running: root.autonomousMotionRunning
    onTriggered: root.acceptFrame(frameTime)
  }

  Item {
    id: snowWindow
    anchors.fill: parent
    visible: root.effectVisible

    Item {
      id: snowLayer
      anchors.fill: parent
      enabled: false
      opacity: root.effectiveIntensity

      Repeater {
        id: flakeRepeater
        model: Math.max(0, root.dropCount)

        Item {
          id: flake
          required property int index

          readonly property real seed: index + 701
          readonly property int depthBand: index % 3
          readonly property real depthScale: depthBand === 0 ? 0.68 : (depthBand === 1 ? 0.9 : 1.18)
          readonly property real diameter: root.flakeSize * depthScale
            * (0.76 + root.seededNoise(seed + 3) * 0.48)
          readonly property real flakeOpacity: (depthBand === 0 ? 0.38 : (depthBand === 1 ? 0.58 : 0.78))
            * (0.78 + root.seededNoise(seed + 5) * 0.22)
          readonly property real initialProgress: root.seededNoise(seed + 7)
          readonly property real travelHeight: snowWindow.height + diameter * 2
          readonly property real initialY: -diameter + initialProgress * travelHeight
          readonly property real baseX: root.seededNoise(seed + 11) * Math.max(1, snowWindow.width)
          readonly property real fallSpeed: (12 + depthBand * 7 + root.seededNoise(seed + 13) * 9)
            * root.speed
          readonly property real flutterPhase: root.seededNoise(seed + 17) * Math.PI * 2
          readonly property real flutterRate: 0.34 + root.seededNoise(seed + 19) * 0.42
          readonly property real flutterRadius: root.flutterAmount
            * (8 + depthBand * 6 + root.seededNoise(seed + 23) * 16)
          readonly property real rotationStart: root.seededNoise(seed + 29) * 360
          readonly property real rotationSpeed: (root.seededNoise(seed + 31) > 0.5 ? 1 : -1)
            * (4 + root.seededNoise(seed + 37) * 13) * (0.65 + depthScale * 0.35)
          readonly property bool isCrystal: root.isCrystalIndex(index)
          readonly property real currentProgress: root.positiveModulo(
            initialProgress + root.visualTime * fallSpeed / Math.max(1, travelHeight), 1)
          readonly property real currentY: -diameter + currentProgress * travelHeight
          readonly property real flutterOffset: Math.sin(flutterPhase + root.visualTime * flutterRate)
            * flutterRadius
          readonly property real windOffset: root.slant * (currentY + diameter) * 0.82
          readonly property real overscan: diameter + flutterRadius + 8
          readonly property real wrappedCenterX: root.positiveModulo(
            baseX + windOffset + flutterOffset + overscan,
            Math.max(1, snowWindow.width + overscan * 2)) - overscan
          readonly property real currentX: wrappedCenterX - diameter * 0.5

          x: currentX
          y: currentY
          width: diameter
          height: diameter
          opacity: flakeOpacity
          rotation: rotationStart + root.visualTime * rotationSpeed
          transformOrigin: Item.Center
          objectName: "snowFlake" + index

          Rectangle {
            anchors.centerIn: parent
            width: flake.isCrystal ? Math.max(1, parent.width * 0.3) : parent.width
            height: width
            radius: width / 2
            color: flake.isCrystal
              ? Qt.rgba(root.snowColor.r, root.snowColor.g, root.snowColor.b, 0.9)
              : Qt.rgba(root.snowColor.r, root.snowColor.g, root.snowColor.b, 0.82)
            border.width: flake.isCrystal ? 0 : Math.max(0.5, parent.width * 0.05)
            border.color: Qt.rgba(root.snowShadowColor.r, root.snowShadowColor.g,
              root.snowShadowColor.b, 0.34)
          }

          Repeater {
            model: flake.isCrystal ? 3 : 0
            Rectangle {
              required property int index
              anchors.centerIn: parent
              width: Math.max(0.7, flake.width * 0.11)
              height: flake.height
              radius: width / 2
              rotation: index * 60
              color: Qt.rgba(root.snowColor.r, root.snowColor.g, root.snowColor.b, 0.78)
            }
          }
        }
      }

      Item {
        anchors.fill: parent
        visible: root.vignette
        opacity: 0.4

        Rectangle {
          x: 0
          y: 0
          width: parent.width
          height: Math.round(parent.height * 0.18)
          gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0; color: "#28000000" }
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
            GradientStop { position: 1; color: "#3c000000" }
          }
        }
      }
    }
  }
}
