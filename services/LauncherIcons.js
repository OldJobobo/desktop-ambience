.pragma library

var DEFAULT_ID = "animation"

var DEFINITIONS = [
  { id: "animation", label: "Animation", glyph: "󰗘" },
  { id: "tune", label: "Tune", glyph: "󰘮" },
  { id: "blur", label: "Blur", glyph: "󰂵" },
  { id: "magicStaff", label: "Magic staff", glyph: "󱡄" },
  { id: "palette", label: "Palette", glyph: "󰏘" },
  { id: "monitorEye", label: "Monitor eye", glyph: "󱎴" },
  { id: "vintageFilter", label: "Vintage filter", glyph: "󰋸" },
  { id: "autoFix", label: "Auto-fix", glyph: "󰁨" }
]

function definitions() {
  return DEFINITIONS.slice()
}

function definition(iconId) {
  var id = String(iconId || "")
  for (var i = 0; i < DEFINITIONS.length; i++)
    if (DEFINITIONS[i].id === id) return DEFINITIONS[i]
  return null
}

function normalize(iconId) {
  return definition(iconId) ? String(iconId) : DEFAULT_ID
}

function glyphFor(iconId) {
  return definition(normalize(iconId)).glyph
}

function labelFor(iconId) {
  return definition(normalize(iconId)).label
}
