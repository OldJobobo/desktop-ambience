import QtQuick

Item {
  id: root

  property string animationMode: "sharedClock"
  property bool running: false
  property int flakeCount: 320
  property real sharedTime: 0
  property real accumulatedFrameTime: 0
  property int sharedUpdateCount: 0
  readonly property int targetUpdatesPerSecond: 30
  readonly property int primitiveCount: flakeRepeater.count

  function seededNoise(seed) {
    var value = Math.sin(seed * 12.9898) * 43758.5453
    return value - Math.floor(value)
  }

  function positiveModulo(value, modulus) {
    return ((value % modulus) + modulus) % modulus
  }

  FrameAnimation {
    running: root.running && root.animationMode === "sharedClock"
    onTriggered: {
      var interval = 1 / root.targetUpdatesPerSecond
      root.accumulatedFrameTime = Math.min(0.05,
        root.accumulatedFrameTime + Math.max(0, Math.min(0.05, frameTime)))
      if (root.accumulatedFrameTime < interval - 0.001) return
      root.sharedTime += root.accumulatedFrameTime
      root.accumulatedFrameTime = 0
      root.sharedUpdateCount += 1
    }
  }

  Repeater {
    id: flakeRepeater
    model: root.flakeCount

    Item {
      id: flake
      required property int index
      readonly property real seed: index + 701
      readonly property real initialProgress: root.seededNoise(seed + 7)
      readonly property real initialFlutter: root.seededNoise(seed + 17) * Math.PI * 2
      readonly property real initialRotation: root.seededNoise(seed + 29) * 360
      readonly property real fallSpeed: 14 + root.seededNoise(seed + 13) * 24
      readonly property real flutterRate: 0.34 + root.seededNoise(seed + 19) * 0.42
      readonly property real rotationSpeed: (root.seededNoise(seed + 31) > 0.5 ? 1 : -1)
        * (4 + root.seededNoise(seed + 37) * 13)
      property real fallPhase: initialProgress
      property real flutterPhase: initialFlutter
      property real rotationPhase: initialRotation
      readonly property real acceptedFall: root.animationMode === "sharedClock"
        ? root.positiveModulo(initialProgress + root.sharedTime * fallSpeed / Math.max(1, root.height + 16), 1)
        : root.positiveModulo(fallPhase, 1)
      readonly property real acceptedFlutter: root.animationMode === "sharedClock"
        ? initialFlutter + root.sharedTime * flutterRate : flutterPhase
      readonly property real acceptedRotation: root.animationMode === "sharedClock"
        ? initialRotation + root.sharedTime * rotationSpeed : rotationPhase

      x: root.seededNoise(seed + 11) * root.width + Math.sin(acceptedFlutter) * 24
      y: -8 + acceptedFall * (root.height + 16)
      width: 8
      height: 8
      rotation: acceptedRotation
      opacity: 0.68

      NumberAnimation on fallPhase {
        running: root.running && root.animationMode === "perFlake"
        loops: Animation.Infinite
        from: flake.initialProgress
        to: flake.initialProgress + 1
        duration: Math.max(1000, (root.height + 16) / flake.fallSpeed * 1000)
        easing.type: Easing.Linear
      }
      NumberAnimation on flutterPhase {
        running: root.running && root.animationMode === "perFlake"
        loops: Animation.Infinite
        from: flake.initialFlutter
        to: flake.initialFlutter + Math.PI * 2
        duration: Math.max(1000, Math.PI * 2 / flake.flutterRate * 1000)
        easing.type: Easing.Linear
      }
      NumberAnimation on rotationPhase {
        running: root.running && root.animationMode === "perFlake"
        loops: Animation.Infinite
        from: flake.initialRotation
        to: flake.initialRotation + (flake.rotationSpeed > 0 ? 360 : -360)
        duration: Math.max(1000, 360 / Math.abs(flake.rotationSpeed) * 1000)
        easing.type: Easing.Linear
      }

      Rectangle {
        anchors.fill: parent
        radius: width / 2
        color: "#e8f2f8"
      }
    }
  }
}
