import QtQuick
import QtQuick.Shapes
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
  property var pathGroups: [[], [], [], [], [], [], [], []]
  property real accumulatedFrameTime: 0
  property int simulationRevision: 0
  property int updateCount: 0
  property int paintRequestCount: 0
  readonly property int opacityBucketCount: 8
  readonly property int edgeCount: edges.length
  readonly property int edgeCeiling: Math.floor(nodeCount * maximumNeighbors / 2)
  readonly property int pathObjectCount: opacityBucketCount
  readonly property int renderedSegmentCount: edges.length
  readonly property string rendererKind: "shape"

  function opacityBucket(opacity) {
    return Math.max(0, Math.min(opacityBucketCount - 1,
      Math.floor(Math.max(0, Math.min(1, opacity)) * opacityBucketCount)))
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

  function rebuild() {
    nodes = MeshCore.createNodes(nodeCount, width, height)
    edges = MeshCore.buildEdges(nodes, connectionDistance, maximumNeighbors)
    simulationRevision += 1
    accumulatedFrameTime = 0
    publishPaths()
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
      publishPaths()
      return
    }
    accumulatedFrameTime = Math.min(interval * 2, accumulatedFrameTime + rawFrameTime)
    if (accumulatedFrameTime + 0.000001 < interval) return
    accumulatedFrameTime = Math.max(0, accumulatedFrameTime - interval)
    MeshCore.advance(nodes, interval, width, height)
    edges = MeshCore.buildEdges(nodes, connectionDistance, maximumNeighbors)
    simulationRevision += 1
    updateCount += 1
    publishPaths()
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

  Shape {
    anchors.fill: parent

    ShapePath {
      strokeWidth: 1; fillColor: "transparent"
      strokeColor: Qt.rgba(0.5, 0.72, 0.9, root.bucketOpacity(0) * 0.3)
      PathMultiline { paths: root.pathGroups[0] }
    }
    ShapePath {
      strokeWidth: 1; fillColor: "transparent"
      strokeColor: Qt.rgba(0.5, 0.72, 0.9, root.bucketOpacity(1) * 0.3)
      PathMultiline { paths: root.pathGroups[1] }
    }
    ShapePath {
      strokeWidth: 1; fillColor: "transparent"
      strokeColor: Qt.rgba(0.5, 0.72, 0.9, root.bucketOpacity(2) * 0.3)
      PathMultiline { paths: root.pathGroups[2] }
    }
    ShapePath {
      strokeWidth: 1; fillColor: "transparent"
      strokeColor: Qt.rgba(0.5, 0.72, 0.9, root.bucketOpacity(3) * 0.3)
      PathMultiline { paths: root.pathGroups[3] }
    }
    ShapePath {
      strokeWidth: 1; fillColor: "transparent"
      strokeColor: Qt.rgba(0.5, 0.72, 0.9, root.bucketOpacity(4) * 0.3)
      PathMultiline { paths: root.pathGroups[4] }
    }
    ShapePath {
      strokeWidth: 1; fillColor: "transparent"
      strokeColor: Qt.rgba(0.5, 0.72, 0.9, root.bucketOpacity(5) * 0.3)
      PathMultiline { paths: root.pathGroups[5] }
    }
    ShapePath {
      strokeWidth: 1; fillColor: "transparent"
      strokeColor: Qt.rgba(0.5, 0.72, 0.9, root.bucketOpacity(6) * 0.3)
      PathMultiline { paths: root.pathGroups[6] }
    }
    ShapePath {
      strokeWidth: 1; fillColor: "transparent"
      strokeColor: Qt.rgba(0.5, 0.72, 0.9, root.bucketOpacity(7) * 0.3)
      PathMultiline { paths: root.pathGroups[7] }
    }
  }
}
