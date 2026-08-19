.pragma library

// Phase 2 fills in the copied defaults and bounds. Keep ordered renderers and
// the dedicated vignette in separate contracts: the vignette is never part of
// activeEffects or sibling-z ordering.
const orderedEffects = [
  { id: "auroraDrift", label: "Aurora Drift" },
  { id: "cinematicLight", label: "Cinematic Light" },
  { id: "crt", label: "CRT" },
  { id: "dustMotes", label: "Dust Motes" },
  { id: "filmGrain", label: "Film Grain" },
  { id: "godRays", label: "God Rays" },
  { id: "rainfall", label: "Rainfall" },
  { id: "trackingLines", label: "VHS" }
]

const dedicatedVignette = {
  id: "backgroundVignette",
  label: "Background Vignette"
}
