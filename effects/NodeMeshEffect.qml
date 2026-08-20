import QtQuick
import QtQuick.Shapes

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

  property var nodes: []
  property var edges: []
  property var pathGroups: [[], [], [], [], [], [], [], []]
  property bool componentReady: false
  property bool rebuildPending: false
  property real accumulatedFrameTime: 0
  property int simulationRevision: 0
  property int simulationUpdateCount: 0
  property int rebuildGeneration: 0
  property int paintRequestCount: 0
  property int styleRevision: 0

  readonly property var overlaySettings: effectSettings
  readonly property bool configuredEnabled: overlaySettings.enabled === true
  readonly property real configuredIntensity: Number(overlaySettings.intensity)
  readonly property real effectiveIntensity: (runtimeIntensity >= 0
    ? clamp(runtimeIntensity, 0, 1) : configuredIntensity) * clamp(globalOpacity, 0, 1)
  readonly property bool effectVisible: configuredEnabled && runtimeEnabled && effectiveIntensity > 0.001
  readonly property real speed: Number(overlaySettings.speed)
  readonly property int nodeCount: Math.round(Number(overlaySettings.nodeCount))
  readonly property real nodeSize: Number(overlaySettings.nodeSize)
  readonly property int connectionDistance: Math.round(Number(overlaySettings.connectionDistance))
  readonly property real lineWidth: Number(overlaySettings.lineWidth)
  readonly property real lineOpacity: Number(overlaySettings.lineOpacity)
  readonly property real driftAmount: Number(overlaySettings.driftAmount)
  readonly property string pointerMode: String(overlaySettings.pointerMode)
  readonly property real mouseInfluence: Number(overlaySettings.mouseInfluence)
  readonly property string nodeColorRole: String(overlaySettings.nodeColorRole)
  readonly property string lineColorRole: String(overlaySettings.lineColorRole)

  readonly property bool hasValidCursorSample: cursorTracker
    && cursorTracker.hasCursorSample === true
    && isFiniteNumber(rawCursorX) && isFiniteNumber(rawCursorY)
  readonly property real rawCursorX: cursorTracker ? Number(cursorTracker.cursorX) : -1
  readonly property real rawCursorY: cursorTracker ? Number(cursorTracker.cursorY) : -1
  readonly property real displayCursorX: cursorTracker
    ? Number(cursorTracker.displayCursorX !== undefined ? cursorTracker.displayCursorX : rawCursorX) : -1
  readonly property real displayCursorY: cursorTracker
    ? Number(cursorTracker.displayCursorY !== undefined ? cursorTracker.displayCursorY : rawCursorY) : -1
  readonly property real screenOriginX: screenOrigin(targetScreen, "x")
  readonly property real screenOriginY: screenOrigin(targetScreen, "y")
  readonly property real rawCursorLocalX: rawCursorX - screenOriginX
  readonly property real rawCursorLocalY: rawCursorY - screenOriginY
  readonly property real cursorLocalX: displayCursorX - screenOriginX
  readonly property real cursorLocalY: displayCursorY - screenOriginY
  readonly property bool cursorOwned: hasValidCursorSample
    && rawCursorLocalX >= 0 && rawCursorLocalY >= 0
    && rawCursorLocalX < width && rawCursorLocalY < height
  readonly property bool pointerForceActive: effectVisible && !reducedMotion
    && pointerMode !== "off" && mouseInfluence > 0.001 && cursorOwned
  readonly property bool simulationRunning: effectVisible && !reducedMotion
    && width > 0 && height > 0 && (driftAmount > 0.001 || pointerForceActive)

  readonly property int targetUpdatesPerSecond: 30
  readonly property int maximumNeighborsPerNode: 4
  readonly property int opacityBucketCount: 8
  readonly property real maximumFrameDelta: 0.05
  readonly property real maximumPointerAcceleration: 90
  readonly property real maximumNodeVelocity: 96
  readonly property real maximumFrameDisplacement: 6
  readonly property real pointerInfluenceRadius: 100 + mouseInfluence * 300
  readonly property int acceptedNodeCount: nodes.length
  readonly property int edgeCount: edges.length
  readonly property int edgeCeiling: Math.floor(acceptedNodeCount * maximumNeighborsPerNode / 2)
  readonly property int shapePathCount: opacityBucketCount
  readonly property int lineSurfaceCount: 1
  readonly property int boundedDelegateCount: nodeRepeater.count
  readonly property color effectiveNodeColor: themeColor(nodeColorRole, "#88c0d0")
  readonly property color effectiveLineColor: themeColor(lineColorRole, "#81a1c1")

  function clamp(value, minimum, maximum) {
    var numeric = Number(value)
    if (isNaN(numeric)) return minimum
    return Math.max(minimum, Math.min(maximum, numeric))
  }

  function isFiniteNumber(value) {
    return typeof value === "number" && isFinite(value)
  }

  function screenOrigin(screen, axis) {
    var value = screen && screen[axis] !== undefined ? Number(screen[axis]) : 0
    return isFiniteNumber(value) ? value : 0
  }

  function themeColor(name, fallbackColor) {
    return theme && theme.colorFor ? theme.colorFor(name, fallbackColor) : fallbackColor
  }

  function resolvedColor(value) {
    return value && value.r !== undefined ? value : Qt.color(value)
  }

  function colorWithAlpha(value, alpha) {
    var color = resolvedColor(value)
    return Qt.rgba(color.r, color.g, color.b, clamp(alpha, 0, 1))
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

  function createNode(index) {
    var angle = seededNoise(index + 307) * Math.PI * 2
    var baseSpeed = 7 + seededNoise(index + 401) * 13
    return {
      index: index,
      initialX: seededNoise(index + 101) * Math.max(1, width),
      initialY: seededNoise(index + 211) * Math.max(1, height),
      x: seededNoise(index + 101) * Math.max(1, width),
      y: seededNoise(index + 211) * Math.max(1, height),
      baseVx: Math.cos(angle) * baseSpeed,
      baseVy: Math.sin(angle) * baseSpeed,
      vx: reducedMotion ? 0 : Math.cos(angle) * baseSpeed * speed * driftAmount,
      vy: reducedMotion ? 0 : Math.sin(angle) * baseSpeed * speed * driftAmount,
      sizeScale: 0.7 + seededNoise(index + 503) * 0.6,
      opacity: 0.34 + seededNoise(index + 601) * 0.42
    }
  }

  function scheduleRebuild() {
    if (!componentReady || rebuildPending) return
    rebuildPending = true
    Qt.callLater(function() {
      rebuildPending = false
      rebuildSimulation()
    })
  }

  function rebuildSimulation() {
    if (!componentReady) return
    var next = []
    for (var index = 0; index < Math.max(0, nodeCount); index++) next.push(createNode(index))
    nodes = next
    rebuildGeneration += 1
    accumulatedFrameTime = 0
    rebuildEdges()
    simulationRevision += 1
  }

  function buildCandidateEdges() {
    var cutoff = Math.max(1, connectionDistance)
    var cutoffSquared = cutoff * cutoff
    var grid = {}
    var candidates = []
    var degrees = []
    var index

    for (index = 0; index < nodes.length; index++) {
      degrees.push(0)
      var cellX = Math.floor(nodes[index].x / cutoff)
      var cellY = Math.floor(nodes[index].y / cutoff)
      var key = cellX + ":" + cellY
      if (!grid[key]) grid[key] = []
      grid[key].push(index)
    }

    for (index = 0; index < nodes.length; index++) {
      var node = nodes[index]
      var originX = Math.floor(node.x / cutoff)
      var originY = Math.floor(node.y / cutoff)
      for (var offsetY = -1; offsetY <= 1; offsetY++) {
        for (var offsetX = -1; offsetX <= 1; offsetX++) {
          var bucket = grid[(originX + offsetX) + ":" + (originY + offsetY)] || []
          for (var bucketIndex = 0; bucketIndex < bucket.length; bucketIndex++) {
            var otherIndex = bucket[bucketIndex]
            if (otherIndex <= index) continue
            var other = nodes[otherIndex]
            var deltaX = other.x - node.x
            var deltaY = other.y - node.y
            var distanceSquared = deltaX * deltaX + deltaY * deltaY
            if (distanceSquared < cutoffSquared)
              candidates.push({a: index, b: otherIndex, distanceSquared: distanceSquared})
          }
        }
      }
    }

    candidates.sort(function(first, second) {
      if (first.distanceSquared !== second.distanceSquared)
        return first.distanceSquared - second.distanceSquared
      if (first.a !== second.a) return first.a - second.a
      return first.b - second.b
    })

    var accepted = []
    var ceiling = Math.floor(nodes.length * maximumNeighborsPerNode / 2)
    for (index = 0; index < candidates.length && accepted.length < ceiling; index++) {
      var candidate = candidates[index]
      if (degrees[candidate.a] >= maximumNeighborsPerNode
          || degrees[candidate.b] >= maximumNeighborsPerNode) continue
      degrees[candidate.a] += 1
      degrees[candidate.b] += 1
      accepted.push({
        a: candidate.a,
        b: candidate.b,
        distance: Math.sqrt(candidate.distanceSquared),
        opacity: 1 - Math.sqrt(candidate.distanceSquared) / cutoff
      })
    }
    return accepted
  }

  function opacityBucket(opacity) {
    return Math.max(0, Math.min(opacityBucketCount - 1,
      Math.floor(clamp(opacity, 0, 1) * opacityBucketCount)))
  }

  function bucketOpacity(index) {
    return (Number(index) + 0.5) / opacityBucketCount
  }

  function publishPaths() {
    var groups = []
    for (var groupIndex = 0; groupIndex < opacityBucketCount; groupIndex++) groups.push([])
    for (var index = 0; index < edges.length; index++) {
      var edge = edges[index]
      var first = nodes[edge.a]
      var second = nodes[edge.b]
      groups[opacityBucket(edge.opacity)].push([
        Qt.point(first.x, first.y), Qt.point(second.x, second.y)
      ])
    }
    pathGroups = groups
    paintRequestCount += 1
  }

  function rebuildEdges() {
    if (!componentReady) return
    edges = buildCandidateEdges()
    publishPaths()
  }

  function invalidateStyle() {
    if (!componentReady) return
    styleRevision += 1
    paintRequestCount += 1
  }

  function pointerForceForPosition(x, y) {
    if (!pointerForceActive || !isFiniteNumber(cursorLocalX) || !isFiniteNumber(cursorLocalY))
      return {x: 0, y: 0, active: false}
    var deltaX = cursorLocalX - x
    var deltaY = cursorLocalY - y
    var distanceSquared = deltaX * deltaX + deltaY * deltaY
    var radius = pointerInfluenceRadius
    if (distanceSquared <= 0.0001 || distanceSquared >= radius * radius)
      return {x: 0, y: 0, active: false}
    var distance = Math.sqrt(distanceSquared)
    var direction = pointerMode === "repel" ? -1 : 1
    var strength = Math.min(maximumPointerAcceleration,
      (18 + mouseInfluence * 72) * Math.pow(1 - distance / radius, 1.4))
    return {
      x: direction * deltaX / distance * strength,
      y: direction * deltaY / distance * strength,
      active: true
    }
  }

  function clampVector(x, y, maximum) {
    var magnitude = Math.sqrt(x * x + y * y)
    if (magnitude <= maximum || magnitude <= 0.0001) return {x: x, y: y}
    var scale = maximum / magnitude
    return {x: x * scale, y: y * scale}
  }

  function integrate(deltaSeconds) {
    var delta = Math.max(0, Math.min(maximumFrameDelta, Number(deltaSeconds)))
    if (delta <= 0 || nodes.length === 0) return
    var overscan = 12 + nodeSize
    for (var index = 0; index < nodes.length; index++) {
      var node = nodes[index]
      var targetVx = node.baseVx * speed * driftAmount
      var targetVy = node.baseVy * speed * driftAmount
      var recovery = Math.min(1, delta * 1.8)
      node.vx += (targetVx - node.vx) * recovery
      node.vy += (targetVy - node.vy) * recovery

      var force = pointerForceForPosition(node.x, node.y)
      if (force.active) {
        node.vx += force.x * delta
        node.vy += force.y * delta
      }
      var velocity = clampVector(node.vx, node.vy, maximumNodeVelocity)
      node.vx = velocity.x
      node.vy = velocity.y
      var displacement = clampVector(node.vx * delta, node.vy * delta, maximumFrameDisplacement)
      node.x += displacement.x
      node.y += displacement.y

      if (node.x < -overscan) node.x = width + overscan
      else if (node.x > width + overscan) node.x = -overscan
      if (node.y < -overscan) node.y = height + overscan
      else if (node.y > height + overscan) node.y = -overscan
    }
    edges = buildCandidateEdges()
    simulationRevision += 1
    simulationUpdateCount += 1
    publishPaths()
  }

  function acceptFrame(frameTime) {
    if (!simulationRunning) {
      accumulatedFrameTime = 0
      return
    }
    var interval = 1 / targetUpdatesPerSecond
    var rawFrameTime = Math.max(0, Number(frameTime))
    if (rawFrameTime > maximumFrameDelta) {
      accumulatedFrameTime = 0
      integrate(interval)
      return
    }
    accumulatedFrameTime = Math.min(interval * 2, accumulatedFrameTime + rawFrameTime)
    if (accumulatedFrameTime + 0.000001 < interval) return
    accumulatedFrameTime = Math.max(0, accumulatedFrameTime - interval)
    integrate(interval)
  }

  function clearPointerMomentum() {
    if (!componentReady || nodes.length === 0) return
    for (var index = 0; index < nodes.length; index++) {
      nodes[index].vx = reducedMotion ? 0 : nodes[index].baseVx * speed * driftAmount
      nodes[index].vy = reducedMotion ? 0 : nodes[index].baseVy * speed * driftAmount
    }
  }

  function resetStaticState() {
    if (!componentReady || nodes.length === 0) return
    for (var index = 0; index < nodes.length; index++) {
      nodes[index].x = nodes[index].initialX
      nodes[index].y = nodes[index].initialY
      nodes[index].vx = 0
      nodes[index].vy = 0
    }
    accumulatedFrameTime = 0
    edges = buildCandidateEdges()
    simulationRevision += 1
    publishPaths()
  }

  function nodeSnapshot(index) {
    var normalized = Math.round(Number(index))
    if (normalized < 0 || normalized >= nodes.length) return null
    var node = nodes[normalized]
    return {
      index: node.index, initialX: node.initialX, initialY: node.initialY,
      x: node.x, y: node.y, vx: node.vx, vy: node.vy,
      size: nodeSize * node.sizeScale, opacity: node.opacity
    }
  }

  function edgeSnapshot(index) {
    var normalized = Math.round(Number(index))
    if (normalized < 0 || normalized >= edges.length) return null
    var edge = edges[normalized]
    return {a: edge.a, b: edge.b, distance: edge.distance, opacity: edge.opacity}
  }

  function nodeObject(index) {
    return nodeRepeater.itemAt(Math.round(Number(index)))
  }

  onNodeCountChanged: scheduleRebuild()
  onWidthChanged: scheduleRebuild()
  onHeightChanged: scheduleRebuild()
  onConnectionDistanceChanged: rebuildEdges()
  onReducedMotionChanged: {
    if (reducedMotion) resetStaticState()
    else clearPointerMomentum()
  }
  onSimulationRunningChanged: if (!simulationRunning) accumulatedFrameTime = 0
  onPointerForceActiveChanged: {
    if (!pointerForceActive) {
      if (driftAmount <= 0.001) resetStaticState()
      else clearPointerMomentum()
    }
  }
  onEffectiveNodeColorChanged: invalidateStyle()
  onEffectiveLineColorChanged: invalidateStyle()
  onLineWidthChanged: invalidateStyle()
  onLineOpacityChanged: invalidateStyle()
  onEffectiveIntensityChanged: invalidateStyle()

  Component.onCompleted: {
    componentReady = true
    rebuildSimulation()
  }
  FrameAnimation {
    running: root.simulationRunning
    onTriggered: root.acceptFrame(frameTime)
  }

  Item {
    id: meshLayer
    anchors.fill: parent
    visible: root.effectVisible
    enabled: false
    clip: true

    Shape {
      id: lineShape
      anchors.fill: parent
      visible: root.lineOpacity > 0.001 && root.effectiveIntensity > 0.001

      ShapePath {
        strokeWidth: root.lineWidth; fillColor: "transparent"
        strokeColor: root.colorWithAlpha(root.effectiveLineColor, root.bucketOpacity(0) * root.lineOpacity * root.effectiveIntensity)
        PathMultiline { paths: root.pathGroups[0] }
      }
      ShapePath {
        strokeWidth: root.lineWidth; fillColor: "transparent"
        strokeColor: root.colorWithAlpha(root.effectiveLineColor, root.bucketOpacity(1) * root.lineOpacity * root.effectiveIntensity)
        PathMultiline { paths: root.pathGroups[1] }
      }
      ShapePath {
        strokeWidth: root.lineWidth; fillColor: "transparent"
        strokeColor: root.colorWithAlpha(root.effectiveLineColor, root.bucketOpacity(2) * root.lineOpacity * root.effectiveIntensity)
        PathMultiline { paths: root.pathGroups[2] }
      }
      ShapePath {
        strokeWidth: root.lineWidth; fillColor: "transparent"
        strokeColor: root.colorWithAlpha(root.effectiveLineColor, root.bucketOpacity(3) * root.lineOpacity * root.effectiveIntensity)
        PathMultiline { paths: root.pathGroups[3] }
      }
      ShapePath {
        strokeWidth: root.lineWidth; fillColor: "transparent"
        strokeColor: root.colorWithAlpha(root.effectiveLineColor, root.bucketOpacity(4) * root.lineOpacity * root.effectiveIntensity)
        PathMultiline { paths: root.pathGroups[4] }
      }
      ShapePath {
        strokeWidth: root.lineWidth; fillColor: "transparent"
        strokeColor: root.colorWithAlpha(root.effectiveLineColor, root.bucketOpacity(5) * root.lineOpacity * root.effectiveIntensity)
        PathMultiline { paths: root.pathGroups[5] }
      }
      ShapePath {
        strokeWidth: root.lineWidth; fillColor: "transparent"
        strokeColor: root.colorWithAlpha(root.effectiveLineColor, root.bucketOpacity(6) * root.lineOpacity * root.effectiveIntensity)
        PathMultiline { paths: root.pathGroups[6] }
      }
      ShapePath {
        strokeWidth: root.lineWidth; fillColor: "transparent"
        strokeColor: root.colorWithAlpha(root.effectiveLineColor, root.bucketOpacity(7) * root.lineOpacity * root.effectiveIntensity)
        PathMultiline { paths: root.pathGroups[7] }
      }
    }

    Repeater {
      id: nodeRepeater
      model: root.acceptedNodeCount

      Rectangle {
        id: nodeDisc
        required property int index
        readonly property var state: root.nodes[index]
        readonly property real currentX: {
          var revision = root.simulationRevision
          return state ? state.x : 0
        }
        readonly property real currentY: {
          var revision = root.simulationRevision
          return state ? state.y : 0
        }
        readonly property real diameter: state ? root.nodeSize * state.sizeScale : 0
        objectName: "nodeMeshNode" + index
        x: currentX - diameter / 2
        y: currentY - diameter / 2
        width: diameter
        height: diameter
        radius: width / 2
        color: root.effectiveNodeColor
        opacity: state ? state.opacity * root.effectiveIntensity : 0
      }
    }
  }
}
