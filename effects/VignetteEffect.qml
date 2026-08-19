import QtQuick

// Dedicated vignette renderer extracted from the original persistent overlay.
// Surface ownership and settings persistence belong to the host and Phase 2.
Item {
  id: root

  property var targetScreen: null
  property bool vignetteEnabled: false
  property real vignetteIntensity: 0.85
  property bool paintEnabled: true

  readonly property real clampedIntensity: Math.max(0, Math.min(1, Number(vignetteIntensity) || 0))
  readonly property real outputScale: targetScreen && targetScreen.devicePixelRatio !== undefined
    ? Math.max(1, Number(targetScreen.devicePixelRatio) || 1) : 1

  visible: paintEnabled && vignetteEnabled && clampedIntensity > 0.001
  enabled: false
  opacity: clampedIntensity

  Image {
    anchors.fill: parent
    source: Qt.resolvedUrl("../assets/vignette.svg")
    // Preserve the source renderer's one-time, output-scaled SVG rasterization.
    sourceSize.width: Math.max(1, Math.round((Number(root.width) || 1) * root.outputScale))
    sourceSize.height: Math.max(1, Math.round((Number(root.height) || 1) * root.outputScale))
    fillMode: Image.Stretch
    smooth: true
    asynchronous: true
    cache: true
  }
}
