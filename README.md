# Desktop Ambience

A standalone Omarchy Shell plugin for an ordered stack of desktop ambience
effects. Phases 1–3 of [`PLAN.md`](PLAN.md) are present: the owned renderers,
ordered lazy stack, dedicated vignette, standalone settings and theme services,
and persistent per-output host now live inside the plugin boundary.

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
injected adapter seams. Each output now owns exactly one persistent,
input-transparent ambience surface whose layer changes between Bottom and
Overlay without replacing its renderer tree. Foreground fullscreen suppression
is paint-only and resolved per output. Monitor remaps retain the standard
Omarchy `ScreenMoveRemap` guard.

The persistent root also owns one on-demand settings window and truthful IPC
status reporting. Phase 4 will replace the window's lifecycle placeholder with
the extracted effect controls.

The 1.0 product boundary is approved: a persistent panel root with background
and explicit click-through foreground presentation, including the dedicated
vignette. Foreground mode may cover stock shell chrome and must suppress paint
per output for fullscreen applications.

## Development

Validate the Phase 3 extraction with an active Wayland session:

```bash
./scripts/check.sh
```

Run the reversible live monitor lifecycle check explicitly when validating
Hyprland hotplug behavior. It creates and removes one temporary headless output
and uses isolated temporary configuration/state homes:

```bash
JOBO_AMBIENCE_LIVE_HOTPLUG=1 python tests/live_phase3_hotplug.py
```
