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
  readonly property real cursorX: cursorTracker ? Number(cursorTracker.cursorX) : -1
  readonly property real cursorY: cursorTracker ? Number(cursorTracker.cursorY) : -1
  readonly property bool hasCursorSample: cursorTracker && cursorTracker.hasCursorSample === true
  readonly property real cursorVelocityX: cursorTracker ? Number(cursorTracker.cursorVelocityX) : 0
  readonly property real cursorVelocityY: cursorTracker ? Number(cursorTracker.cursorVelocityY) : 0
  readonly property real cursorKick: cursorTracker ? Number(cursorTracker.cursorKick) : 0

  readonly property var overlaySettings: effectSettings
  readonly property bool configuredEnabled: overlaySettings.enabled === true
  readonly property bool effectVisible: configuredEnabled && runtimeEnabled && effectiveIntensity > 0.001
  readonly property real configuredIntensity: Number(overlaySettings.intensity)
  readonly property real effectiveIntensity: (runtimeIntensity >= 0 ? clamp(runtimeIntensity, 0, 1) : configuredIntensity) * clamp(globalOpacity, 0, 1)
  readonly property real speed: Number(overlaySettings.speed)
  readonly property int moteCount: Math.round(Number(overlaySettings.moteCount))
  readonly property real moteSize: Number(overlaySettings.moteSize)
  readonly property real accentBlend: Number(overlaySettings.accentBlend)
  readonly property bool mouseReactive: overlaySettings.mouseReactive === true
  readonly property real mouseInfluence: Number(overlaySettings.mouseInfluence)
  readonly property real cursorInfluenceRadius: 220 + mouseInfluence * 320
  readonly property real cursorInfluenceRadiusSquared: cursorInfluenceRadius * cursorInfluenceRadius
  readonly property real cursorSpeed: Math.sqrt(cursorVelocityX * cursorVelocityX + cursorVelocityY * cursorVelocityY)
  readonly property color themeForeground: themeColor("foreground", "#d8dee9")
  readonly property color themeAccent: themeColor("accent", "#88c0d0")
  readonly property color moteColor: mixColor(themeForeground, themeAccent, accentBlend)

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

  function screenOrigin(screen, axis) {
    var value = screen && screen[axis] !== undefined ? Number(screen[axis]) : 0
    return isNaN(value) ? 0 : value
  }

  function open(payloadJson) {
    var payload = parsePayload(payloadJson)
    runtimeEnabled = true
    if (payload.intensity !== undefined) runtimeIntensity = clamp(payload.intensity, 0, 1)
  }

  function close() {
    runtimeEnabled = false
  }

  Item {
    id: dustWindow

    readonly property real screenOriginX: root.screenOrigin(root.targetScreen, "x")
    readonly property real screenOriginY: root.screenOrigin(root.targetScreen, "y")
    readonly property real cursorLocalX: root.cursorX - screenOriginX
    readonly property real cursorLocalY: root.cursorY - screenOriginY

    anchors.fill: parent
    visible: root.effectVisible


    Item {
      id: dustLayer

      anchors.fill: parent
      enabled: false
      opacity: root.effectiveIntensity

      ListModel {
        id: transientMotes
      }

      function updatePersistentMotes() {
        for (var i = 0; i < persistentMoteRepeater.count; i++) {
          var item = persistentMoteRepeater.itemAt(i)
          if (item) item.applyAirDisturbance()
        }
      }

      function updateTransientMotes() {
        for (var i = transientMoteRepeater.count - 1; i >= 0; i--) {
          var item = transientMoteRepeater.itemAt(i)
          if (item) item.advanceFrame(33)
        }
      }

      function cursorInsideWindow() {
        return root.hasCursorSample
          && dustWindow.cursorLocalX >= 0
          && dustWindow.cursorLocalY >= 0
          && dustWindow.cursorLocalX < dustWindow.width
          && dustWindow.cursorLocalY < dustWindow.height
      }

      function spawnTransientMote() {
        if (!root.mouseReactive || root.mouseInfluence <= 0 || !cursorInsideWindow()) return

        var speed = root.cursorSpeed
        if (speed < 2) return

        var spawnChance = Math.min(0.92, 0.52 + speed / 460) * Math.max(0.72, root.mouseInfluence)
        if (Math.random() > spawnChance) return

        var burstCount = 1 + (Math.random() < Math.min(0.42, speed / 430) ? 1 : 0)
        var maxTransient = Math.round(22 + root.mouseInfluence * 52)

        for (var i = 0; i < burstCount; i++) {
          while (transientMotes.count >= maxTransient) transientMotes.remove(0)

          var angle = Math.random() * Math.PI * 2
          var radius = Math.sqrt(Math.random()) * (14 + root.moteSize * 3.4)
          var originX = Math.cos(angle) * radius
          var originY = Math.sin(angle) * radius
          var outwardX = radius > 0 ? originX / radius : Math.cos(angle)
          var outwardY = radius > 0 ? originY / radius : Math.sin(angle)
          var sideX = -outwardY
          var sideY = outwardX
          var lift = 0.48 + Math.random() * 1.10
          var size = Math.max(1.5, root.moteSize * (0.72 + Math.random() * 0.58))

          transientMotes.append({
            px: dustWindow.cursorLocalX - size / 2 + originX,
            py: dustWindow.cursorLocalY - size / 2 + originY,
            vx: outwardX * lift + sideX * (Math.random() - 0.5) * 0.7 + root.cursorVelocityX * (0.0015 + Math.random() * 0.0035),
            vy: outwardY * lift + sideY * (Math.random() - 0.5) * 0.7 + root.cursorVelocityY * (0.0015 + Math.random() * 0.0035),
            size: size,
            alpha: 0.46 + Math.random() * 0.28,
            age: 0,
            life: 5000 + Math.random() * 4000
          })
        }
      }

      Timer {
        interval: 58
        repeat: true
        running: root.effectVisible && !root.reducedMotion && root.mouseReactive
        onTriggered: dustLayer.spawnTransientMote()
      }

      Timer {
        interval: 33
        repeat: true
        running: root.effectVisible && !root.reducedMotion
        triggeredOnStart: true
        onTriggered: dustLayer.updatePersistentMotes()
      }

      Timer {
        interval: 33
        repeat: true
        running: root.effectVisible && !root.reducedMotion && transientMotes.count > 0
        onTriggered: dustLayer.updateTransientMotes()
      }

      Repeater {
        id: persistentMoteRepeater

        model: root.moteCount

        Rectangle {
          id: mote

          required property int index

          readonly property real seed: index + 1
          readonly property real sizeNoise: root.seededNoise(seed + 2)
          readonly property real moteVariance: 0.65 + root.seededNoise(seed + 83) * 0.7
          readonly property real wakeVariance: 0.86 + root.seededNoise(seed + 89) * 0.28
          readonly property real damping: 0.865 + root.seededNoise(seed + 97) * 0.035
          readonly property real spring: 0.0025 + root.seededNoise(seed + 101) * 0.004
          readonly property real swirlDirection: root.seededNoise(seed + 107) > 0.5 ? 1 : -1
          property real airOffsetX: 0
          property real airOffsetY: 0
          property real airVelocityX: 0
          property real airVelocityY: 0
          property real airAge: 0
          width: Math.max(1, Math.round(root.moteSize * (0.5 + sizeNoise * 1.4)))
          height: width
          radius: width / 2
          color: root.moteColor
          opacity: 0.16 + root.seededNoise(seed + 7) * 0.50
          x: Math.round(root.seededNoise(seed + 11) * Math.max(1, dustWindow.width))
          y: Math.round(root.seededNoise(seed + 17) * Math.max(1, dustWindow.height))

          function clampAir(value) {
            return root.clamp(value, -180, 180)
          }

          function applyAirDisturbance() {
            airAge += 0.033
            // Keep a positional repulsion field around the pointer even after
            // the sampled movement impulse decays. Mouse Influence should not
            // silently become inert whenever the cursor moves between polls.
            if (root.mouseReactive && root.mouseInfluence > 0
                && dustLayer.cursorInsideWindow()) {
              var cursorDx = x + width / 2 + airOffsetX - dustWindow.cursorLocalX
              var cursorDy = y + height / 2 + airOffsetY - dustWindow.cursorLocalY
              var distanceSquared = cursorDx * cursorDx + cursorDy * cursorDy

              if (distanceSquared < root.cursorInfluenceRadiusSquared) {
                var cursorDistance = Math.max(1, Math.sqrt(distanceSquared))
                var cursorFalloff = Math.pow(1 - cursorDistance / root.cursorInfluenceRadius, 1.35)
                var radialStrength = 10 + root.cursorSpeed * (0.07 + root.seededNoise(seed + 113) * 0.045)
                var wakeStrength = 0.18 + root.cursorKick * (0.12 + root.seededNoise(seed + 127) * 0.10)
                var swirlStrength = (1.8 + root.cursorSpeed * 0.012) * swirlDirection
                var noiseX = Math.sin(airAge * (0.8 + root.seededNoise(seed + 131) * 0.5) + seed) * 1.1
                var noiseY = Math.cos(airAge * (0.7 + root.seededNoise(seed + 137) * 0.5) + seed * 0.7) * 1.1
                var forceScale = root.mouseInfluence * cursorFalloff * moteVariance * wakeVariance
                var radialX = cursorDx / cursorDistance
                var radialY = cursorDy / cursorDistance
                var swirlX = -radialY * swirlStrength
                var swirlY = radialX * swirlStrength
                airVelocityX += (radialX * radialStrength + root.cursorVelocityX * wakeStrength + swirlX + noiseX) * forceScale * 0.062
                airVelocityY += (radialY * radialStrength + root.cursorVelocityY * wakeStrength + swirlY + noiseY) * forceScale * 0.062
              }
            }

            airVelocityX = root.clamp((airVelocityX - airOffsetX * spring) * damping, -10, 10)
            airVelocityY = root.clamp((airVelocityY - airOffsetY * spring) * damping, -10, 10)
            airOffsetX = clampAir(airOffsetX + airVelocityX)
            airOffsetY = clampAir(airOffsetY + airVelocityY)

            if (Math.abs(airOffsetX) < 0.05 && Math.abs(airVelocityX) < 0.05) {
              airOffsetX = 0
              airVelocityX = 0
            }
            if (Math.abs(airOffsetY) < 0.05 && Math.abs(airVelocityY) < 0.05) {
              airOffsetY = 0
              airVelocityY = 0
            }
          }

          transform: [
            Translate {
              x: mote.airOffsetX
              y: mote.airOffsetY
            }
          ]

          SequentialAnimation on x {
            running: root.effectVisible && !root.reducedMotion
            loops: Animation.Infinite
            NumberAnimation {
              to: Math.round(root.seededNoise(seed + 23) * Math.max(1, dustWindow.width))
              duration: Math.max(8000, Math.round((22000 + root.seededNoise(seed + 29) * 18000) / root.speed))
              easing.type: Easing.InOutSine
            }
            NumberAnimation {
              to: Math.round(root.seededNoise(seed + 31) * Math.max(1, dustWindow.width))
              duration: Math.max(8000, Math.round((24000 + root.seededNoise(seed + 37) * 16000) / root.speed))
              easing.type: Easing.InOutSine
            }
          }

          SequentialAnimation on y {
            running: root.effectVisible && !root.reducedMotion
            loops: Animation.Infinite
            NumberAnimation {
              to: Math.round(root.seededNoise(seed + 41) * Math.max(1, dustWindow.height))
              duration: Math.max(9000, Math.round((26000 + root.seededNoise(seed + 43) * 20000) / root.speed))
              easing.type: Easing.InOutSine
            }
            NumberAnimation {
              to: Math.round(root.seededNoise(seed + 47) * Math.max(1, dustWindow.height))
              duration: Math.max(9000, Math.round((28000 + root.seededNoise(seed + 53) * 18000) / root.speed))
              easing.type: Easing.InOutSine
            }
          }

          SequentialAnimation on opacity {
            running: root.effectVisible && !root.reducedMotion
            loops: Animation.Infinite
            NumberAnimation {
              to: 0.12 + root.seededNoise(seed + 59) * 0.42
              duration: Math.max(3000, Math.round((6500 + root.seededNoise(seed + 61) * 5500) / root.speed))
              easing.type: Easing.InOutSine
            }
            NumberAnimation {
              to: 0.18 + root.seededNoise(seed + 67) * 0.52
              duration: Math.max(3000, Math.round((7000 + root.seededNoise(seed + 71) * 5000) / root.speed))
              easing.type: Easing.InOutSine
            }
          }
        }
      }

      Repeater {
        id: transientMoteRepeater

        model: transientMotes

        Rectangle {
          id: transientMote

          required property int index
          required property real px
          required property real py
          required property real vx
          required property real vy
          required property real size
          required property real alpha
          required property real age
          required property real life

          width: Math.max(1, size)
          height: width
          radius: width / 2
          x: px
          y: py
          color: root.moteColor
          opacity: alpha * Math.min(1, age / 220) * Math.pow(Math.max(0, 1 - age / life), 0.95)

          function applyCursorInfluence() {
            if (!root.mouseReactive || root.mouseInfluence <= 0
                || !dustLayer.cursorInsideWindow()) return

            var centerX = px + width / 2
            var centerY = py + height / 2
            var dx = centerX - dustWindow.cursorLocalX
            var dy = centerY - dustWindow.cursorLocalY
            var distanceSquared = dx * dx + dy * dy
            if (distanceSquared >= root.cursorInfluenceRadiusSquared) return

            var distance = Math.max(1, Math.sqrt(distanceSquared))
            var falloff = Math.pow(1 - distance / root.cursorInfluenceRadius, 1.2)
            var radialForce = (0.20 + root.cursorSpeed * 0.0025) * root.mouseInfluence * falloff
            var wakeForce = 0.012 * root.mouseInfluence * falloff
            transientMote.vx += dx / distance * radialForce + root.cursorVelocityX * wakeForce
            transientMote.vy += dy / distance * radialForce + root.cursorVelocityY * wakeForce
          }

          function advanceFrame(deltaMs) {
            transientMote.age += deltaMs
            if (transientMote.age >= transientMote.life) {
              if (transientMote.index >= 0 && transientMote.index < transientMotes.count) transientMotes.remove(transientMote.index)
              return
            }

            transientMote.applyCursorInfluence()
            transientMote.vx = root.clamp(transientMote.vx * 0.968, -7.5, 7.5)
            transientMote.vy = root.clamp(transientMote.vy * 0.968, -7.5, 7.5)
            transientMote.px += transientMote.vx
            transientMote.py += transientMote.vy
          }
        }
      }
    }
  }


}
