# Desktop Ambience

A standalone Omarchy Shell plugin for an ordered stack of desktop ambience
effects. Phases 1 and 2 of [`PLAN.md`](PLAN.md) are present: the owned
renderers, ordered lazy stack, foreground host, dedicated vignette, standalone
settings owner, and shared theme adapter now live inside the plugin boundary.

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

The plugin now owns normalized, atomic, retryable settings at
`$XDG_CONFIG_HOME/omarchy/jobo/desktop-ambience/settings.json`. One shared theme
adapter supplies native Omarchy colors and extended Base16 roles to every
renderer. Effects no longer read external plugin settings or own file watchers.
VHS uses the canonical `trackingLines` ID; the dedicated vignette has separate
state and never enters the reorderable effect list.

Renderer scene bodies remain byte-identical to the pinned source after their
injected adapter seams. The settings window remains Phase 4 work, and Phase 3
will replace the source-derived dual window trees with one dynamically selected
surface per output.

The 1.0 product boundary is approved: a persistent panel root with background
and explicit click-through foreground presentation, including the dedicated
vignette. Foreground mode may cover stock shell chrome and must suppress paint
per output for fullscreen applications.

## Development

Validate the Phase 2 extraction with an active Wayland session:

```bash
./scripts/check.sh
```
