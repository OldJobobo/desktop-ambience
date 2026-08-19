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

## Current status

The manifest and plugin lifecycle shell are present, but rendering, settings
persistence, the settings window, and theme integration are placeholders. Do
not install this revision expecting visible effects.

Before Phase 1, the decisions listed in `PLAN.md` still need approval. The
recommended 1.0 policy is a persistent panel root with background-only
presentation; the dedicated background vignette remains out of scope.

## Development

Validate the repository scaffold with:

```bash
./scripts/check.sh
```
