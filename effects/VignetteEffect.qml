import QtQuick

// Dedicated vignette renderer. Surface ownership and normalized persistence
// belong to the host; this renderer never participates in ordered effects.
Item {
  id: root

  property var targetScreen: null
  property var settings: ({})
  property bool paintEnabled: true

  readonly property bool vignetteEnabled: settings.enabled === true
  readonly property real vignetteIntensity: Number(settings.intensity)
  readonly property bool ignoreBackgroundAnimationLayer: settings.ignoreBackgroundAnimationLayer === true
  readonly property real clampedIntensity: vignetteIntensity
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
