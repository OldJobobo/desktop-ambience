import QtQuick
import "NodeMeshPrototypeCore.js" as MeshCore

Item {
  id: root

  property int nodeCount: 54
  property int connectionDistance: 132
  property int maximumNeighbors: 4
  property int targetUpdatesPerSecond: 30
  property bool running: true
  property var nodes: []
  property var edges: []
  property real accumulatedFrameTime: 0
  property int simulationRevision: 0
  property int updateCount: 0
  property int paintRequestCount: 0
  readonly property int edgeCount: edges.length
  readonly property int edgeCeiling: Math.floor(nodeCount * maximumNeighbors / 2)
  readonly property int pathObjectCount: 0
  readonly property int renderedSegmentCount: edges.length
  readonly property int opacityBucketCount: 8
  readonly property string rendererKind: "canvas"

  function opacityBucket(opacity) {
    return Math.max(0, Math.min(opacityBucketCount - 1,
      Math.floor(Math.max(0, Math.min(1, opacity)) * opacityBucketCount)))
  }

  function bucketOpacity(index) {
    return (Number(index) + 0.5) / opacityBucketCount
  }

  function rebuild() {
    nodes = MeshCore.createNodes(nodeCount, width, height)
    edges = MeshCore.buildEdges(nodes, connectionDistance, maximumNeighbors)
    simulationRevision += 1
    requestLinePaint()
  }

  function requestLinePaint() {
    paintRequestCount += 1
    lineCanvas.requestPaint()
  }

  function advance(frameTime) {
    if (!running || width <= 0 || height <= 0) {
      accumulatedFrameTime = 0
      return
    }
    var interval = 1 / targetUpdatesPerSecond
    var rawFrameTime = Math.max(0, Number(frameTime))
    if (rawFrameTime > 0.05) {
      accumulatedFrameTime = 0
      MeshCore.advance(nodes, interval, width, height)
      edges = MeshCore.buildEdges(nodes, connectionDistance, maximumNeighbors)
      simulationRevision += 1
      updateCount += 1
      requestLinePaint()
      return
    }
    accumulatedFrameTime = Math.min(interval * 2, accumulatedFrameTime + rawFrameTime)
    if (accumulatedFrameTime + 0.000001 < interval) return
    accumulatedFrameTime = Math.max(0, accumulatedFrameTime - interval)
    MeshCore.advance(nodes, interval, width, height)
    edges = MeshCore.buildEdges(nodes, connectionDistance, maximumNeighbors)
    simulationRevision += 1
    updateCount += 1
    requestLinePaint()
  }

  onNodeCountChanged: rebuild()
  onConnectionDistanceChanged: rebuild()
  onWidthChanged: rebuild()
  onHeightChanged: rebuild()
  Component.onCompleted: rebuild()

  FrameAnimation {
    running: root.running
    onTriggered: root.advance(frameTime)
  }

  Canvas {
    id: lineCanvas
    anchors.fill: parent
    renderStrategy: Canvas.Immediate

    onPaint: {
      var context = getContext("2d")
      context.reset()
      context.lineWidth = 1
      for (var index = 0; index < root.edges.length; index++) {
        var edge = root.edges[index]
        var first = root.nodes[edge.a]
        var second = root.nodes[edge.b]
        context.strokeStyle = Qt.rgba(0.5, 0.72, 0.9,
          root.bucketOpacity(root.opacityBucket(edge.opacity)) * 0.3)
        context.beginPath()
        context.moveTo(first.x, first.y)
        context.lineTo(second.x, second.y)
        context.stroke()
      }
    }
  }
}
