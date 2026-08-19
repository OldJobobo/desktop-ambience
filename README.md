# Desktop Ambience

A standalone Omarchy Shell plugin for an ordered stack of desktop ambience
effects. Phase 1 of the extraction described in [`PLAN.md`](PLAN.md) is now
present: the owned renderers, ordered lazy stack, full-output foreground host,
and dedicated vignette are copied into the standalone plugin boundary.

## Planned effects

- Aurora Drift
- Cinematic Light
- CRT
- Dust Motes
- Film Grain
- God Rays
- Rainfall
- VHS
- Dedicated vignette

## Current status

The renderer baseline and in-memory host are present. Settings persistence, the
settings window, centralized theme integration, and removal of effect-local
legacy settings readers remain later phases. Phase 1 defaults to background
presentation with VHS (`trackingLines`) selected and the dedicated vignette
disabled. The vignette has separate enable/intensity state and is not part of
the reorderable effect list. The eight renderer bodies remain byte-identical to
the pinned source except for one
Phase 1 host-boundary injection in `CrtEffect.qml`: its legacy-derived
`foregroundOverlay` readonly property is now an injected boolean property so
CRT foreground-only distortion follows the standalone host presentation. Its
visual math is unchanged.

The 1.0 product boundary is approved: a persistent panel root with background
and explicit click-through foreground presentation, including the dedicated
vignette. Foreground mode may cover stock shell chrome and must suppress paint
per output for fullscreen applications.

## Development

Validate the Phase 1 extraction with:

```bash
./scripts/check.sh
```
