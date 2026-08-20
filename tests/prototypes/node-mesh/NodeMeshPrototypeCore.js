.pragma library

function seededNoise(seed) {
  var value = Math.sin(seed * 12.9898) * 43758.5453
  return value - Math.floor(value)
}

function createNodes(count, width, height) {
  var usableWidth = Math.max(1, Number(width))
  var usableHeight = Math.max(1, Number(height))
  var nodes = []
  for (var index = 0; index < count; index++) {
    nodes.push({
      x: seededNoise(index + 101) * usableWidth,
      y: seededNoise(index + 211) * usableHeight,
      vx: (seededNoise(index + 307) - 0.5) * 16,
      vy: (seededNoise(index + 401) - 0.5) * 16
    })
  }
  return nodes
}

function advance(nodes, deltaSeconds, width, height) {
  var usableWidth = Math.max(1, Number(width))
  var usableHeight = Math.max(1, Number(height))
  var delta = Math.max(0, Math.min(0.05, Number(deltaSeconds)))
  var overscan = 8
  for (var index = 0; index < nodes.length; index++) {
    var node = nodes[index]
    node.x += node.vx * delta
    node.y += node.vy * delta
    if (node.x < -overscan) node.x = usableWidth + overscan
    else if (node.x > usableWidth + overscan) node.x = -overscan
    if (node.y < -overscan) node.y = usableHeight + overscan
    else if (node.y > usableHeight + overscan) node.y = -overscan
  }
}

function buildEdges(nodes, connectionDistance, maxNeighbors) {
  var cutoff = Math.max(1, Number(connectionDistance))
  var cutoffSquared = cutoff * cutoff
  var cellSize = cutoff
  var grid = {}
  var candidates = []
  var degrees = []
  var index

  for (index = 0; index < nodes.length; index++) {
    degrees.push(0)
    var cellX = Math.floor(nodes[index].x / cellSize)
    var cellY = Math.floor(nodes[index].y / cellSize)
    var key = cellX + ":" + cellY
    if (!grid[key]) grid[key] = []
    grid[key].push(index)
  }

  for (index = 0; index < nodes.length; index++) {
    var node = nodes[index]
    var originX = Math.floor(node.x / cellSize)
    var originY = Math.floor(node.y / cellSize)
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
          if (distanceSquared < cutoffSquared) {
            candidates.push({a: index, b: otherIndex, distanceSquared: distanceSquared})
          }
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

  var edgeCeiling = Math.floor(nodes.length * maxNeighbors / 2)
  var edges = []
  for (index = 0; index < candidates.length && edges.length < edgeCeiling; index++) {
    var candidate = candidates[index]
    if (degrees[candidate.a] >= maxNeighbors || degrees[candidate.b] >= maxNeighbors) continue
    degrees[candidate.a] += 1
    degrees[candidate.b] += 1
    edges.push({
      a: candidate.a,
      b: candidate.b,
      opacity: 1 - Math.sqrt(candidate.distanceSquared) / cutoff
    })
  }
  return edges
}
