import QtQuick
import "../effects"

Item {
  id: root

  property var targetScreen: null
  property var settings: null
  property var theme: null
  property var barState: null
  property var cursorTracker: null
  property var activeEffects: settings && settings.activeEffects ? settings.activeEffects : []
  property bool foregroundOverlay: false
  property bool paintEnabled: true
  property bool productionEffectsEnabled: true
  property bool animationGeometryReady: false
  readonly property bool rendererPaintEnabled: paintEnabled && animationGeometryReady
  property Component testFrontComponent: null
  property Component testBackComponent: null
  readonly property var supportedEffects: [
    "auroraDrift",
    "cinematicLight",
    "crt",
    "dustMotes",
    "drip",
    "filmGrain",
    "godRays",
    "rainfall",
    "tacticalGrid",
    "trackingLines",
    "bokeh",
    "nodeMesh"
  ]
  readonly property var normalizedActiveEffects: normalizeActiveEffects(activeEffects)
  readonly property var testFrontObject: testFrontLoader.item
  readonly property var testBackObject: testBackLoader.item
  readonly property int activeProductionEffectCount: [
    auroraDriftLoader,
    cinematicLightLoader,
    crtLoader,
    dustMotesLoader,
    dripLoader,
    filmGrainLoader,
    godRaysLoader,
    rainfallLoader,
    tacticalGridLoader,
    vhsLoader,
    bokehLoader,
    nodeMeshLoader
  ].filter(function(loader) {
    if (!loader.active || loader.item === null) return false
    return loader !== nodeMeshLoader || root.settingsFor("nodeMesh").enabled === true
  }).length

  function scheduleGeometryReady() {
    animationGeometryReady = false
    geometrySettle.restart()
  }

  onWidthChanged: scheduleGeometryReady()
  onHeightChanged: scheduleGeometryReady()
  Component.onCompleted: scheduleGeometryReady()

  Timer {
    id: geometrySettle
    interval: 80
    onTriggered: {
      if (root.width > 0 && root.height > 0) root.animationGeometryReady = true
    }
  }

  function normalizeActiveEffects(source) {
    var result = []
    var seen = {}
    var values = Array.isArray(source) ? source : []
    for (var i = 0; i < values.length; i++) {
      var effectId = String(values[i] || "")
      if (supportedEffects.indexOf(effectId) < 0 || seen[effectId]) continue
      seen[effectId] = true
      result.push(effectId)
    }
    return result
  }

  function stackIndex(effectId) {
    return normalizedActiveEffects.indexOf(String(effectId || ""))
  }

  function zForEffect(effectId) {
    var index = stackIndex(effectId)
    return index < 0 ? -1 : normalizedActiveEffects.length - index
  }

  function productionEffectActive(effectId) {
    var effect = settingsFor(effectId)
    return productionEffectsEnabled && stackIndex(effectId) >= 0
      && effect.enabled === true
  }

  function nodeMeshResident() {
    return productionEffectsEnabled && stackIndex("nodeMesh") >= 0
  }

  function settingsFor(effectId) {
    var effects = settings && settings.effects && typeof settings.effects === "object"
      ? settings.effects : ({})
    var value = effects[String(effectId || "")]
    return value && typeof value === "object" ? value : ({})
  }

  function productionEffectObject(effectId) {
    var loaders = {
      auroraDrift: auroraDriftLoader,
      cinematicLight: cinematicLightLoader,
      crt: crtLoader,
      dustMotes: dustMotesLoader,
      drip: dripLoader,
      filmGrain: filmGrainLoader,
      godRays: godRaysLoader,
      rainfall: rainfallLoader,
      tacticalGrid: tacticalGridLoader,
      trackingLines: vhsLoader,
      bokeh: bokehLoader,
      nodeMesh: nodeMeshLoader
    }
    var loader = loaders[String(effectId || "")]
    return loader ? loader.item : null
  }

  Component {
    id: auroraDriftComponent
    AuroraDriftEffect {
      objectName: "auroraDriftEffect"
      anchors.fill: parent
      effectSettings: root.settingsFor("auroraDrift")
      globalOpacity: root.settings ? root.settings.opacity : 1
      reducedMotion: root.settings ? root.settings.reduceMotion : false
      theme: root.theme
      runtimeEnabled: root.rendererPaintEnabled && root.productionEffectsEnabled
    }
  }

  Component {
    id: cinematicLightComponent
    CinematicLightEffect {
      objectName: "cinematicLightEffect"
      anchors.fill: parent
      effectSettings: root.settingsFor("cinematicLight")
      globalOpacity: root.settings ? root.settings.opacity : 1
      reducedMotion: root.settings ? root.settings.reduceMotion : false
      theme: root.theme
      runtimeEnabled: root.rendererPaintEnabled && root.productionEffectsEnabled
    }
  }

  Component {
    id: crtComponent
    CrtEffect {
      objectName: "crtEffect"
      anchors.fill: parent
      foregroundOverlay: root.foregroundOverlay
      effectSettings: root.settingsFor("crt")
      globalOpacity: root.settings ? root.settings.opacity : 1
      reducedMotion: root.settings ? root.settings.reduceMotion : false
      runtimeEnabled: root.rendererPaintEnabled && root.productionEffectsEnabled
    }
  }

  Component {
    id: dustMotesComponent
    DustMotesEffect {
      objectName: "dustMotesEffect"
      anchors.fill: parent
      targetScreen: root.targetScreen
      cursorTracker: root.cursorTracker
      effectSettings: root.settingsFor("dustMotes")
      globalOpacity: root.settings ? root.settings.opacity : 1
      reducedMotion: root.settings ? root.settings.reduceMotion : false
      theme: root.theme
      runtimeEnabled: root.rendererPaintEnabled && root.productionEffectsEnabled
    }
  }

  Component {
    id: dripComponent
    DripEffect {
      objectName: "dripEffect"
      anchors.fill: parent
      effectSettings: root.settingsFor("drip")
      globalOpacity: root.settings ? root.settings.opacity : 1
      reducedMotion: root.settings ? root.settings.reduceMotion : false
      theme: root.theme
      barState: root.barState
      runtimeEnabled: root.rendererPaintEnabled && root.productionEffectsEnabled
    }
  }

  Component {
    id: filmGrainComponent
    FilmGrainEffect {
      objectName: "filmGrainEffect"
      anchors.fill: parent
      effectSettings: root.settingsFor("filmGrain")
      globalOpacity: root.settings ? root.settings.opacity : 1
      reducedMotion: root.settings ? root.settings.reduceMotion : false
      theme: root.theme
      runtimeEnabled: root.rendererPaintEnabled && root.productionEffectsEnabled
    }
  }

  Component {
    id: godRaysComponent
    GodRaysEffect {
      objectName: "godRaysEffect"
      anchors.fill: parent
      effectSettings: root.settingsFor("godRays")
      globalOpacity: root.settings ? root.settings.opacity : 1
      reducedMotion: root.settings ? root.settings.reduceMotion : false
      theme: root.theme
      runtimeEnabled: root.rendererPaintEnabled && root.productionEffectsEnabled
    }
  }

  Component {
    id: rainfallComponent
    RainfallEffect {
      objectName: "rainfallEffect"
      anchors.fill: parent
      effectSettings: root.settingsFor("rainfall")
      globalOpacity: root.settings ? root.settings.opacity : 1
      reducedMotion: root.settings ? root.settings.reduceMotion : false
      theme: root.theme
      runtimeEnabled: root.rendererPaintEnabled && root.productionEffectsEnabled
    }
  }

  Component {
    id: tacticalGridComponent
    TacticalGridEffect {
      objectName: "tacticalGridEffect"
      anchors.fill: parent
      targetScreen: root.targetScreen
      cursorTracker: root.cursorTracker
      effectSettings: root.settingsFor("tacticalGrid")
      globalOpacity: root.settings ? root.settings.opacity : 1
      reducedMotion: root.settings ? root.settings.reduceMotion : false
      theme: root.theme
      runtimeEnabled: root.rendererPaintEnabled && root.productionEffectsEnabled
    }
  }

  Component {
    id: vhsComponent
    VhsEffect {
      objectName: "vhsEffect"
      anchors.fill: parent
      effectSettings: root.settingsFor("trackingLines")
      globalOpacity: root.settings ? root.settings.opacity : 1
      reducedMotion: root.settings ? root.settings.reduceMotion : false
      runtimeEnabled: root.rendererPaintEnabled && root.productionEffectsEnabled
    }
  }

  Component {
    id: bokehComponent
    BokehEffect {
      objectName: "bokehEffect"
      anchors.fill: parent
      effectSettings: root.settingsFor("bokeh")
      globalOpacity: root.settings ? root.settings.opacity : 1
      reducedMotion: root.settings ? root.settings.reduceMotion : false
      theme: root.theme
      runtimeEnabled: root.rendererPaintEnabled && root.productionEffectsEnabled
    }
  }

  Component {
    id: nodeMeshComponent
    NodeMeshEffect {
      objectName: "nodeMeshEffect"
      anchors.fill: parent
      targetScreen: root.targetScreen
      cursorTracker: root.cursorTracker
      effectSettings: root.settingsFor("nodeMesh")
      globalOpacity: root.settings ? root.settings.opacity : 1
      reducedMotion: root.settings ? root.settings.reduceMotion : false
      theme: root.theme
      runtimeEnabled: root.rendererPaintEnabled && root.productionEffectsEnabled
    }
  }

  Loader {
    id: auroraDriftLoader
    anchors.fill: parent
    active: root.productionEffectActive("auroraDrift")
    sourceComponent: auroraDriftComponent
    z: root.zForEffect("auroraDrift")
  }

  Loader {
    id: cinematicLightLoader
    anchors.fill: parent
    active: root.productionEffectActive("cinematicLight")
    sourceComponent: cinematicLightComponent
    z: root.zForEffect("cinematicLight")
  }

  Loader {
    id: crtLoader
    anchors.fill: parent
    active: root.productionEffectActive("crt")
    sourceComponent: crtComponent
    z: root.zForEffect("crt")
  }

  Loader {
    id: dustMotesLoader
    anchors.fill: parent
    active: root.productionEffectActive("dustMotes")
    sourceComponent: dustMotesComponent
    z: root.zForEffect("dustMotes")
  }

  Loader {
    id: dripLoader
    anchors.fill: parent
    active: root.productionEffectActive("drip")
    sourceComponent: dripComponent
    z: root.zForEffect("drip")
  }

  Loader {
    id: filmGrainLoader
    anchors.fill: parent
    active: root.productionEffectActive("filmGrain")
    sourceComponent: filmGrainComponent
    z: root.zForEffect("filmGrain")
  }

  Loader {
    id: godRaysLoader
    anchors.fill: parent
    active: root.productionEffectActive("godRays")
    sourceComponent: godRaysComponent
    z: root.zForEffect("godRays")
  }

  Loader {
    id: rainfallLoader
    anchors.fill: parent
    active: root.productionEffectActive("rainfall")
    sourceComponent: rainfallComponent
    z: root.zForEffect("rainfall")
  }

  Loader {
    id: tacticalGridLoader
    anchors.fill: parent
    active: root.productionEffectActive("tacticalGrid")
    sourceComponent: tacticalGridComponent
    z: root.zForEffect("tacticalGrid")
  }

  Loader {
    id: vhsLoader
    anchors.fill: parent
    active: root.productionEffectActive("trackingLines")
    sourceComponent: vhsComponent
    z: root.zForEffect("trackingLines")
  }

  Loader {
    id: bokehLoader
    anchors.fill: parent
    active: root.productionEffectActive("bokeh")
    sourceComponent: bokehComponent
    z: root.zForEffect("bokeh")
  }

  Loader {
    id: nodeMeshLoader
    anchors.fill: parent
    active: root.nodeMeshResident()
    sourceComponent: nodeMeshComponent
    z: root.zForEffect("nodeMesh")
  }

  Loader {
    id: testFrontLoader
    objectName: "testFrontLoader"
    anchors.fill: parent
    active: root.testFrontComponent !== null
    sourceComponent: root.testFrontComponent
    z: root.zForEffect("auroraDrift")
  }

  Loader {
    id: testBackLoader
    objectName: "testBackLoader"
    anchors.fill: parent
    active: root.testBackComponent !== null
    sourceComponent: root.testBackComponent
    z: root.zForEffect("filmGrain")
  }
}
