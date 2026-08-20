# TODO

## Future effects

- [ ] Add more configurable ambience animations and weather styles:
  - **Drip** — animate droplets slowly forming along the bar-facing screen edge. When the bar is at the top, droplets should gather beneath it and fall downward. When the bar is at the bottom, support an option for droplets to gather above it and drip upward. Fall back to the corresponding screen edge when bar geometry is unavailable. Expose droplet count, size, formation time, fall speed, direction, and theme-color blending.
  - [x] **Tactical Grid** — draw a screen-wide grid with optional subtle parallax and adjustable mouse influence. Add horizontal and vertical guide lines that intersect at the pointer, plus customizable targeting-reticle styles, size, color, opacity, and animation. See [`docs/tactical-grid-plan.md`](docs/tactical-grid-plan.md).
  - **Bokeh** — render softly animated bokeh lights with configurable size, density, blur, drift, speed, and colors derived from selectable theme palette roles.
  - **Node Mesh** — animate a field of drifting nodes that connects nearby points into a responsive mesh. Include controls for node density, connection distance, line opacity, movement speed, theme colors, and optional pointer attraction or repulsion.
  - **Precipitation styles** — extend Rainfall with a precipitation-style selector for rain, snow, and future variants. Give each style appropriate controls while preserving the shared intensity, speed, direction, theme blending, and reduced-motion behavior.
  - Keep every new effect compatible with stack ordering, per-effect enablement, background and foreground presentation, theme changes, reduced motion, multiple outputs, and the existing settings persistence contract.
  - Add contract, normalization, behavior, and performance coverage for each effect before enabling it by default.
