# Desktop Ambience

A standalone Omarchy Shell plugin for an ordered stack of desktop ambience
effects. The repository currently contains the architecture scaffold described
in [`PLAN.md`](PLAN.md); renderer extraction has not started.

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

The manifest and plugin lifecycle shell are present, but rendering, settings
persistence, the settings window, and theme integration are placeholders. Do
not install this revision expecting visible effects.

The 1.0 product boundary is approved: a persistent panel root with background
and explicit click-through foreground presentation, including the dedicated
vignette. Foreground mode may cover stock shell chrome and must suppress paint
per output for fullscreen applications.

## Development

Validate the repository scaffold with:

```bash
./scripts/check.sh
```
