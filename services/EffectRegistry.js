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
      speed: realField(0.62, 0.15, 4), dropCount: intField(180, 16, 320),
      slant: realField(0.08, -0.2, 0.35), mistAmount: realField(0.34, 0, 1),
      splashAmount: realField(0.38, 0, 1), accentBlend: realField(0.42, 0, 1),
      vignette: boolField(true)
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
  grainCount: "Grain Count", grainSize: "Grain Size", rayCount: "Ray Count",
  raySpread: "Ray Spread", shimmer: "Shimmer", origin: "Ray Origin", dropCount: "Drop Count",
  slant: "Slant", mistAmount: "Mist Amount", splashAmount: "Splash Amount",
  lineSpacing: "Line Spacing", trackingBands: "Tracking Bands", noiseAmount: "Noise Amount",
  glitchAmount: "Glitch Amount", chromaBleed: "Chroma Bleed",
  ignoreBackgroundAnimationLayer: "Place Behind Animations"
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
  mouseInfluence: "Sets how strongly the pointer pushes motes.",
  grainCount: "Sets the number of film-grain specks.",
  grainSize: "Sets the size of each grain speck.",
  rayCount: "Sets the number of light rays.",
  raySpread: "Sets the width of the ray fan.",
  shimmer: "Varies the ray brightness over time.",
  origin: "Chooses the corner where the rays begin.",
  dropCount: "Sets the number of raindrops.",
  slant: "Sets the angle of the falling rain.",
  mistAmount: "Sets the opacity of the rain mist.",
  splashAmount: "Sets the number of rain splashes.",
  lineSpacing: "Sets the gap between VHS scanlines.",
  trackingBands: "Sets the number of rolling tracking bands.",
  noiseAmount: "Sets the amount of VHS static.",
  glitchAmount: "Sets the strength of displaced VHS slices.",
  chromaBleed: "Separates color channels along tracking edges.",
  ignoreBackgroundAnimationLayer: "Draws the vignette behind all stacked effects."
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

function fieldLabel(key) {
  return fieldLabels[String(key || "")] || String(key || "")
}

function fieldHint(key) {
  var normalized = String(key || "")
  if (fieldHints[normalized]) return fieldHints[normalized]
  if (normalized.indexOf("Count") >= 0) return "Controls how many source elements are rendered."
  if (normalized.indexOf("Size") >= 0 || normalized.indexOf("Spacing") >= 0
      || normalized.indexOf("Height") >= 0) return "Controls the renderer's source geometry."
  if (normalized.indexOf("Amount") >= 0 || normalized.indexOf("Softness") >= 0
      || normalized === "slant" || normalized === "raySpread") return "Tunes this part of the visual treatment."
  if (normalized.indexOf("Interval") >= 0) return "Sets the time between animation pulses."
  return "Adjusts the source renderer setting."
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
    field.label = fieldLabel(key)
    field.hint = fieldHint(key)
    field.step = stepForField(field)
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
