.pragma library

// Canonical Phase 2 schema. Ordered renderers and the dedicated vignette are
// separate contracts: the vignette never participates in activeEffects or z.
var orderedEffects = [
  {
    id: "auroraDrift", label: "Aurora Drift",
    fields: {
      enabled: boolField(true), intensity: realField(0.95, 0, 1),
      speed: realField(1.35, 0.15, 4), ribbonCount: intField(6, 1, 9),
      blurSoftness: realField(0.9, 0, 1), accentBlend: realField(0.88, 0, 1),
      vignette: boolField(true)
    }
  },
  {
    id: "cinematicLight", label: "Cinematic Light",
    fields: {
      enabled: boolField(true), intensity: realField(1, 0, 1),
      speed: realField(1, 0.15, 4),
      stylePreset: enumField("lightLeak", ["lightLeak", "cinematicFlare", "anamorphicGlow"]),
      slowDrift: boolField(true), occasionalSweeps: boolField(false),
      activeShimmer: boolField(false), flareCount: intField(4, 1, 9),
      accentBlend: realField(0.5, 0, 1), vignette: boolField(true)
    }
  },
  {
    id: "crt", label: "CRT",
    fields: {
      enabled: boolField(true), intensity: realField(0.58, 0, 1),
      speed: realField(1, 0.15, 4), scanlineSpacing: intField(3, 2, 9),
      staticBandHeight: intField(150, 60, 320), staticAmount: realField(0.24, 0, 1),
      glowAmount: realField(0.22, 0, 1), bloomPulse: boolField(true),
      bloomPulseAmount: realField(0.52, 0, 1), bloomPulseInterval: intField(18000, 7000, 60000),
      distortion: boolField(true), distortionAmount: realField(0.45, 0, 1),
      vignette: boolField(true)
    }
  },
  {
    id: "dustMotes", label: "Dust Motes",
    fields: {
      enabled: boolField(true), intensity: realField(0.5, 0, 1),
      speed: realField(0.7, 0.15, 4), moteCount: intField(72, 12, 180),
      moteSize: realField(2.6, 1, 8), accentBlend: realField(0.42, 0, 1),
      mouseReactive: boolField(true), mouseInfluence: realField(0.28, 0, 1)
    }
  },
  {
    id: "drip", label: "Drip",
    fields: {
      enabled: boolField(true), intensity: realField(1, 0, 1),
      speed: realField(1, 0.15, 4), dropletCount: intField(28, 6, 72),
      dropletSize: realField(12, 4, 32), formationTime: intField(3800, 600, 12000),
      fallSpeed: realField(260, 40, 900),
      direction: enumField("auto", ["auto", "down", "up"]),
      accentBlend: realField(0, 0, 1), bloodMode: boolField(false)
    }
  },
  {
    id: "filmGrain", label: "Film Grain",
    fields: {
      enabled: boolField(true), intensity: realField(0.28, 0, 1),
      speed: realField(1, 0.2, 5), grainCount: intField(180, 32, 520),
      grainSize: realField(1.35, 0.6, 3.5), accentBlend: realField(0.18, 0, 1)
    }
  },
  {
    id: "godRays", label: "God Rays",
    fields: {
      enabled: boolField(true), intensity: realField(0.82, 0, 1),
      speed: realField(0.85, 0.15, 4), rayCount: intField(7, 1, 12),
      raySpread: realField(0.72, 0.2, 1), blurSoftness: realField(0.88, 0, 1),
      accentBlend: realField(0.58, 0, 1), shimmer: boolField(true),
      vignette: boolField(true),
      origin: enumField("top-left", ["top-left", "top-right", "bottom-left", "bottom-right"])
    }
  },
  {
    id: "rainfall", label: "Rainfall",
    fields: {
      enabled: boolField(true), intensity: realField(0.72, 0, 1),
      speed: realField(0.62, 0.15, 4),
      precipitationStyle: enumField("rain", ["rain", "snow"]),
      dropCount: intField(180, 16, 320), slant: realField(0.08, -0.2, 0.35),
      accentBlend: realField(0.42, 0, 1), vignette: boolField(true),
      mistAmount: conditionalField(realField(0.34, 0, 1), "precipitationStyle", ["rain"]),
      splashAmount: conditionalField(realField(0.38, 0, 1), "precipitationStyle", ["rain"]),
      flakeSize: conditionalField(realField(6, 2, 18), "precipitationStyle", ["snow"]),
      flutterAmount: conditionalField(realField(0.58, 0, 1), "precipitationStyle", ["snow"]),
      flakeDetail: conditionalField(enumField("mixed", ["soft", "crystal", "mixed"]),
        "precipitationStyle", ["snow"])
    }
  },
  {
    id: "tacticalGrid", label: "Tactical Grid",
    fields: {
      enabled: boolField(true), intensity: realField(0.55, 0, 1),
      speed: realField(1, 0.15, 4), gridSpacing: intField(64, 24, 160),
      gridLineWidth: realField(1, 0.5, 4), gridOpacity: realField(0.28, 0, 1),
      guideOpacity: realField(0.58, 0, 1), parallaxEnabled: boolField(true),
      mouseInfluence: realField(0.22, 0, 1), mouseGuides: boolField(true),
      reticleStyle: enumField("brackets", ["crosshair", "brackets", "ring", "diamond"]),
      reticleSize: intField(42, 12, 120), reticlePulse: boolField(true),
      colorRole: enumField("accent", ["accent", "foreground", "color11", "color12", "color13", "color14"])
    }
  },
  {
    id: "trackingLines", label: "VHS",
    fields: {
      enabled: boolField(true), intensity: realField(0.68, 0, 1),
      speed: realField(1, 0.15, 4), lineSpacing: intField(4, 2, 12),
      trackingBands: intField(4, 0, 7), noiseAmount: realField(0.42, 0, 1),
      glitchAmount: realField(0.34, 0, 1), chromaBleed: boolField(true),
      vignette: boolField(true)
    }
  },
  {
    id: "bokeh", label: "Bokeh",
    fields: {
      enabled: boolField(true), intensity: realField(0.52, 0, 1),
      speed: realField(0.65, 0.15, 4), lightCount: intField(28, 6, 72),
      lightSize: realField(88, 20, 240), blurSoftness: realField(0.82, 0, 1),
      driftAmount: realField(0.42, 0, 1), twinkleAmount: realField(0.18, 0, 1),
      primaryColorRole: enumField("accent", ["accent", "foreground", "color09", "color10", "color11", "color12", "color13", "color14"]),
      secondaryColorRole: enumField("color13", ["accent", "foreground", "color09", "color10", "color11", "color12", "color13", "color14"])
    }
  },
  {
    id: "nodeMesh", label: "Node Mesh",
    fields: {
      enabled: boolField(true), intensity: realField(0.48, 0, 1),
      speed: realField(0.7, 0.15, 4), nodeCount: intField(54, 12, 120),
      nodeSize: realField(3, 1, 10), connectionDistance: intField(132, 40, 260),
      lineWidth: realField(1, 0.5, 3), lineOpacity: realField(0.3, 0, 1),
      driftAmount: realField(0.38, 0, 1),
      pointerMode: enumField("off", ["off", "attract", "repel"]),
      mouseInfluence: realField(0.3, 0, 1),
      nodeColorRole: enumField("accent", ["accent", "foreground", "color09", "color10", "color11", "color12", "color13", "color14"]),
      lineColorRole: enumField("color12", ["accent", "foreground", "color09", "color10", "color11", "color12", "color13", "color14"])
    }
  }
]

var dedicatedVignette = {
  id: "backgroundVignette", label: "Background Vignette",
  fields: {
    enabled: boolField(false), intensity: realField(0.85, 0, 1),
    ignoreBackgroundAnimationLayer: boolField(false)
  }
}

var fieldLabels = {
  enabled: "Enabled", intensity: "Intensity", speed: "Speed",
  ribbonCount: "Ribbon Count", blurSoftness: "Blur Softness", accentBlend: "Accent Tint",
  vignette: "Built-in Vignette", stylePreset: "Light Style", slowDrift: "Slow Drift",
  occasionalSweeps: "Occasional Sweeps", activeShimmer: "Active Shimmer", flareCount: "Flare Count",
  scanlineSpacing: "Scanline Spacing", staticBandHeight: "Static Band Height",
  staticAmount: "Static Amount", glowAmount: "Glow Amount", bloomPulse: "Bloom Pulse",
  bloomPulseAmount: "Bloom Amount", bloomPulseInterval: "Bloom Interval",
  distortion: "Distortion", distortionAmount: "Distortion Amount", moteCount: "Mote Count",
  moteSize: "Mote Size", mouseReactive: "Mouse Reactive", mouseInfluence: "Mouse Influence",
  dropletCount: "Droplet Count", dropletSize: "Droplet Size", formationTime: "Formation Time",
  fallSpeed: "Fall Speed", direction: "Direction", bloodMode: "Blood Mode",
  grainCount: "Grain Count", grainSize: "Grain Size", rayCount: "Ray Count",
  raySpread: "Ray Spread", shimmer: "Shimmer", origin: "Ray Origin", dropCount: "Drop Count",
  precipitationStyle: "Precipitation Style", slant: "Slant", mistAmount: "Mist Amount",
  splashAmount: "Splash Amount", flakeSize: "Flake Size", flutterAmount: "Flutter Amount",
  flakeDetail: "Flake Detail",
  gridSpacing: "Grid Spacing", gridLineWidth: "Grid Line Width", gridOpacity: "Grid Opacity",
  guideOpacity: "Guide Opacity", parallaxEnabled: "Pointer Parallax",
  mouseGuides: "Pointer Guides", reticleStyle: "Reticle Style", reticleSize: "Reticle Size",
  reticlePulse: "Reticle Pulse", colorRole: "Theme Color",
  lineSpacing: "Line Spacing", trackingBands: "Tracking Bands", noiseAmount: "Noise Amount",
  glitchAmount: "Glitch Amount", chromaBleed: "Chroma Bleed",
  lightCount: "Light Count", lightSize: "Light Size", driftAmount: "Drift Amount",
  twinkleAmount: "Twinkle Amount", primaryColorRole: "Primary Theme Color",
  secondaryColorRole: "Secondary Theme Color", nodeCount: "Node Count",
  nodeSize: "Node Size", connectionDistance: "Connection Distance",
  lineWidth: "Line Width", lineOpacity: "Line Opacity", pointerMode: "Pointer Mode",
  nodeColorRole: "Node Theme Color", lineColorRole: "Line Theme Color",
  ignoreBackgroundAnimationLayer: "Place Behind Animations"
}

var effectFieldLabels = {
  rainfall: {
    enabled: "Enabled", intensity: "Precipitation Intensity", speed: "Precipitation Speed",
    precipitationStyle: "Precipitation Style", dropCount: "Precipitation Count",
    slant: "Wind Slant", accentBlend: "Accent Tint", vignette: "Built-in Vignette",
    mistAmount: "Mist Amount", splashAmount: "Splash Amount", flakeSize: "Flake Size",
    flutterAmount: "Flutter Amount", flakeDetail: "Flake Detail"
  },
  nodeMesh: {
    enabled: "Enabled", intensity: "Mesh Intensity", speed: "Mesh Speed",
    nodeCount: "Node Count", nodeSize: "Node Size", connectionDistance: "Connection Distance",
    lineWidth: "Line Width", lineOpacity: "Line Opacity", driftAmount: "Drift Amount",
    pointerMode: "Pointer Mode", mouseInfluence: "Pointer Influence",
    nodeColorRole: "Node Theme Color", lineColorRole: "Line Theme Color"
  }
}

var fieldHints = {
  enabled: "Shows or hides this effect without removing it from the stack.",
  intensity: "Sets the effect's overall visibility.",
  speed: "Sets the animation speed.",
  ribbonCount: "Sets the number of aurora ribbons.",
  blurSoftness: "Sets how soft the effect's edges appear.",
  accentBlend: "Sets how much of the Omarchy accent color appears.",
  vignette: "Darkens this effect near the screen edges.",
  stylePreset: "Chooses the light pattern.",
  slowDrift: "Adds slow pulsing and side-to-side movement.",
  occasionalSweeps: "Adds infrequent horizontal light sweeps.",
  activeShimmer: "Adds frequent glints and brightness pulses.",
  flareCount: "Sets the number of light flares.",
  scanlineSpacing: "Sets the gap between CRT scanlines.",
  staticBandHeight: "Sets the height of the moving static band.",
  staticAmount: "Sets the strength of the CRT static.",
  glowAmount: "Sets the strength of the CRT glow.",
  bloomPulse: "Makes the CRT glow brighten and fade.",
  bloomPulseAmount: "Sets how much the CRT glow changes during a pulse.",
  bloomPulseInterval: "Sets the time between CRT glow pulses.",
  distortion: "Enables CRT warping only in foreground mode.",
  distortionAmount: "Sets the strength of the CRT warping.",
  moteCount: "Sets the number of dust motes.",
  moteSize: "Sets the size of each dust mote.",
  mouseReactive: "Lets the pointer push nearby motes.",
  mouseInfluence: "Sets how strongly the pointer influences mouse-reactive movement.",
  dropletCount: "Sets the number of droplets forming along the source edge.",
  dropletSize: "Sets the base size of each formed droplet.",
  formationTime: "Sets how long droplets take to form before detaching.",
  fallSpeed: "Sets how quickly detached droplets travel across the screen.",
  direction: "Follows the horizontal bar automatically or forces upward or downward travel.",
  bloodMode: "Overrides the bar color with cinematic blood red and strengthens the shadow and reflection.",
  grainCount: "Sets the number of film-grain specks.",
  grainSize: "Sets the size of each grain speck.",
  rayCount: "Sets the number of light rays.",
  raySpread: "Sets the width of the ray fan.",
  shimmer: "Varies the ray brightness over time.",
  origin: "Chooses the corner where the rays begin.",
  precipitationStyle: "Chooses the precipitation renderer.",
  dropCount: "Sets the bounded precipitation population.",
  slant: "Sets the wind bias applied to precipitation.",
  mistAmount: "Sets the opacity of the rain mist.",
  splashAmount: "Sets the number of rain splashes.",
  flakeSize: "Sets the base snowflake diameter before depth variation.",
  flutterAmount: "Sets the amount of lateral snow movement.",
  flakeDetail: "Chooses soft, crystal, or mixed snowflake shapes.",
  gridSpacing: "Sets the distance between tactical grid lines.",
  gridLineWidth: "Sets the thickness of tactical grid lines.",
  gridOpacity: "Sets the visibility of the tactical grid.",
  guideOpacity: "Sets the visibility of the pointer guide lines and reticle.",
  parallaxEnabled: "Lets the pointer shift the grid with a subtle depth effect.",
  mouseGuides: "Draws horizontal and vertical guides through the pointer.",
  reticleStyle: "Chooses the targeting reticle shape.",
  reticleSize: "Sets the targeting reticle size.",
  reticlePulse: "Animates the targeting reticle with a restrained pulse.",
  colorRole: "Chooses a color from the active Omarchy theme.",
  lineSpacing: "Sets the gap between VHS scanlines.",
  trackingBands: "Sets the number of rolling tracking bands.",
  noiseAmount: "Sets the amount of VHS static.",
  glitchAmount: "Sets the strength of displaced VHS slices.",
  chromaBleed: "Separates color channels along tracking edges.",
  lightCount: "Sets the bounded number of bokeh lights rendered on each display.",
  lightSize: "Sets the base diameter of the bokeh lights before depth variation.",
  driftAmount: "Sets how far bokeh lights travel along their slow paths.",
  twinkleAmount: "Sets the amount of slow opacity breathing without blinking.",
  primaryColorRole: "Chooses the first color from the active Omarchy theme.",
  secondaryColorRole: "Chooses the second color blended across the light field.",
  nodeCount: "Sets the bounded number of mesh nodes rendered on each display.",
  nodeSize: "Sets the base diameter of each mesh node before seeded variation.",
  connectionDistance: "Sets the maximum distance at which nearby nodes connect.",
  lineWidth: "Sets the thickness of mesh connections.",
  lineOpacity: "Sets connection visibility relative to mesh intensity.",
  pointerMode: "Chooses whether the pointer attracts, repels, or does not affect nodes.",
  nodeColorRole: "Chooses the node color from the active Omarchy theme.",
  lineColorRole: "Chooses the connection color from the active Omarchy theme.",
  ignoreBackgroundAnimationLayer: "Draws the vignette behind all stacked effects."
}

var effectFieldHints = {
  rainfall: {
    enabled: "Shows or hides precipitation without removing Rainfall from the stack.",
    intensity: "Sets the overall visibility of the selected precipitation style.",
    speed: "Sets the shared motion speed for rain or snow.",
    precipitationStyle: "Chooses rain or snow while preserving each style's saved tuning.",
    dropCount: "Sets the bounded number of rain drops or snowflakes rendered on each display.",
    slant: "Sets rain angle and the lateral wind bias applied to snow.",
    accentBlend: "Sets how much of the Omarchy accent color appears in precipitation.",
    vignette: "Darkens the selected precipitation style near the screen edges.",
    mistAmount: "Sets background mist visibility for rain.",
    splashAmount: "Sets the bounded foreground splash population for rain.",
    flakeSize: "Sets the base snowflake diameter before deterministic depth variation.",
    flutterAmount: "Sets the bounded lateral flutter applied to falling snow.",
    flakeDetail: "Chooses soft flakes, crystal flakes, or a bounded mixture of both."
  },
  nodeMesh: {
    enabled: "Shows or hides Node Mesh without removing it from the stack.",
    intensity: "Sets the overall visibility of Node Mesh nodes and connections.",
    speed: "Sets the speed of the bounded node simulation.",
    nodeCount: "Sets the bounded number of mesh nodes rendered on each display.",
    nodeSize: "Sets the base diameter of each node before deterministic variation.",
    connectionDistance: "Connects nodes only while they are closer than this distance.",
    lineWidth: "Sets the thickness of all mesh connections.",
    lineOpacity: "Sets connection visibility relative to the normalized effect intensity.",
    driftAmount: "Sets the magnitude of deterministic autonomous node drift.",
    pointerMode: "Chooses whether the pointer attracts, repels, or does not affect nearby nodes.",
    mouseInfluence: "Sets the strength and radius of the bounded pointer force.",
    nodeColorRole: "Chooses the node color from the active Omarchy theme.",
    lineColorRole: "Chooses the connection color from the active Omarchy theme."
  }
}

function boolField(defaultValue) {
  return { type: "bool", defaultValue: defaultValue === true }
}

function realField(defaultValue, minimum, maximum) {
  return { type: "real", defaultValue: defaultValue, minimum: minimum, maximum: maximum }
}

function intField(defaultValue, minimum, maximum) {
  return { type: "int", defaultValue: defaultValue, minimum: minimum, maximum: maximum }
}

function enumField(defaultValue, values) {
  return { type: "enum", defaultValue: defaultValue, values: values.slice() }
}

function conditionalField(field, conditionField, values) {
  field.visibleWhen = { field: String(conditionField || ""), values: values.slice() }
  return field
}

function deepCopy(value) {
  return JSON.parse(JSON.stringify(value))
}

function orderedDefinitions() {
  return deepCopy(orderedEffects)
}

function orderedIds() {
  var result = []
  for (var i = 0; i < orderedEffects.length; i++) result.push(orderedEffects[i].id)
  return result
}

function isOrderedId(value) {
  return definition(value) !== null
}

function definition(value) {
  var id = String(value || "")
  for (var i = 0; i < orderedEffects.length; i++) {
    if (orderedEffects[i].id === id) return orderedEffects[i]
  }
  return null
}

function vignetteDefinition() {
  return deepCopy(dedicatedVignette)
}

function fieldLabel(key, effectId) {
  var normalized = String(key || "")
  var effectLabels = effectFieldLabels[String(effectId || "")]
  if (effectLabels && effectLabels[normalized]) return effectLabels[normalized]
  return fieldLabels[normalized] || normalized
}

function fieldHint(key, effectId) {
  var normalized = String(key || "")
  var effectHints = effectFieldHints[String(effectId || "")]
  if (effectHints && effectHints[normalized]) return effectHints[normalized]
  if (fieldHints[normalized]) return fieldHints[normalized]
  if (normalized.indexOf("Count") >= 0) return "Controls how many source elements are rendered."
  if (normalized.indexOf("Size") >= 0 || normalized.indexOf("Spacing") >= 0
      || normalized.indexOf("Height") >= 0) return "Controls the renderer's source geometry."
  if (normalized.indexOf("Amount") >= 0 || normalized.indexOf("Softness") >= 0
      || normalized === "slant" || normalized === "raySpread") return "Tunes this part of the visual treatment."
  if (normalized.indexOf("Interval") >= 0) return "Sets the time between animation pulses."
  return "Adjusts the source renderer setting."
}

function enumOptionLabel(value) {
  var normalized = String(value || "")
  var labels = {
    lightLeak: "Light leak", cinematicFlare: "Cinematic flare",
    anamorphicGlow: "Anamorphic glow", auto: "Automatic",
    down: "Down", up: "Up", rain: "Rain", snow: "Snow",
    soft: "Soft", crystal: "Crystal", mixed: "Mixed",
    off: "Off", attract: "Attract", repel: "Repel",
    "top-left": "Top left", "top-right": "Top right",
    "bottom-left": "Bottom left", "bottom-right": "Bottom right",
    crosshair: "Crosshair", brackets: "Brackets", ring: "Ring", diamond: "Diamond",
    accent: "Accent", foreground: "Foreground",
    color09: "Palette 09", color10: "Palette 10", color11: "Palette 11",
    color12: "Palette 12", color13: "Palette 13", color14: "Palette 14"
  }
  if (labels[normalized]) return labels[normalized]
  var spaced = normalized.replace(/([a-z])([A-Z])/g, "$1 $2").replace(/-/g, " ")
  return spaced.length > 0 ? spaced.charAt(0).toUpperCase() + spaced.slice(1) : normalized
}

function enumOptions(field) {
  var values = field && Array.isArray(field.values) ? field.values : []
  var result = []
  for (var i = 0; i < values.length; i++)
    result.push({ value: String(values[i]), label: enumOptionLabel(values[i]) })
  return result
}

function stepForField(field) {
  if (!field) return 0.01
  if (field.type === "int") {
    var range = Number(field.maximum) - Number(field.minimum)
    return range > 200 ? 4 : 1
  }
  var numericRange = Number(field.maximum) - Number(field.minimum)
  return numericRange > 10 ? 1000 : (numericRange > 4 ? 0.05 : 0.01)
}

function fieldDefinitions(value) {
  var entry = definition(value)
  if (!entry) return []
  var result = []
  var keys = Object.keys(entry.fields)
  for (var i = 0; i < keys.length; i++) {
    var key = keys[i]
    var field = deepCopy(entry.fields[key])
    field.key = key
    field.label = fieldLabel(key, value)
    field.hint = fieldHint(key, value)
    field.step = stepForField(field)
    if (field.type === "enum") field.options = enumOptions(field)
    result.push(field)
  }
  return result
}

function vignetteFieldDefinitions() {
  var result = []
  var keys = Object.keys(dedicatedVignette.fields)
  for (var i = 0; i < keys.length; i++) {
    var key = keys[i]
    var field = deepCopy(dedicatedVignette.fields[key])
    field.key = key
    field.label = fieldLabel(key)
    field.hint = fieldHint(key)
    field.step = stepForField(field)
    result.push(field)
  }
  return result
}

function defaultsFor(value) {
  var entry = definition(value)
  return entry ? defaultsFromFields(entry.fields) : ({})
}

function vignetteDefaults() {
  return defaultsFromFields(dedicatedVignette.fields)
}

function defaultEffects() {
  var result = {}
  for (var i = 0; i < orderedEffects.length; i++)
    result[orderedEffects[i].id] = defaultsFromFields(orderedEffects[i].fields)
  return result
}

function defaultsFromFields(fields) {
  var result = {}
  for (var key in fields) result[key] = fields[key].defaultValue
  return result
}

function normalizeEffect(value, source) {
  var entry = definition(value)
  if (!entry) return null
  return normalizeFields(entry.fields, source)
}

function normalizeVignette(source) {
  return normalizeFields(dedicatedVignette.fields, source)
}

function knownEffectKeys(value) {
  var entry = definition(value)
  var result = {}
  if (!entry) return result
  for (var key in entry.fields) result[key] = true
  return result
}

function knownVignetteKeys() {
  var result = {}
  for (var key in dedicatedVignette.fields) result[key] = true
  return result
}

function normalizeFields(fields, source) {
  var object = source && typeof source === "object" && !Array.isArray(source) ? source : ({})
  if (source === true || source === false) object = { enabled: source === true }
  var result = {}
  for (var key in fields) result[key] = normalizeValue(fields[key], object[key])
  // Cinematic motion always retains at least the source's slow drift mode.
  if (fields.stylePreset && !result.slowDrift && !result.occasionalSweeps && !result.activeShimmer)
    result.slowDrift = true
  return result
}

function normalizeValue(field, value) {
  if (field.type === "bool") {
    if (value === true || value === false) return value
    return field.defaultValue
  }
  if (field.type === "enum") {
    var candidate = String(value === undefined || value === null ? "" : value)
    return field.values.indexOf(candidate) >= 0 ? candidate : field.defaultValue
  }
  var numeric = Number(value)
  if (!isFinite(numeric)) return field.defaultValue
  if (field.type === "int") numeric = Math.round(numeric)
  return Math.max(field.minimum, Math.min(field.maximum, numeric))
}
