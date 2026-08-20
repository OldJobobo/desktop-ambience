# TODO

## Future effects

- [ ] Add more configurable ambience animations and weather styles:
  - **Drip** — animate droplets slowly forming along the bar-facing screen edge. When the bar is at the top, droplets should gather beneath it and fall downward. When the bar is at the bottom, support an option for droplets to gather above it and drip upward. Fall back to the corresponding screen edge when bar geometry is unavailable. Expose droplet count, size, formation time, fall speed, direction, and theme-color blending.
  - [x] **Tactical Grid** — draw a screen-wide grid with optional subtle parallax and adjustable mouse influence. Add horizontal and vertical guide lines that intersect at the pointer, plus customizable targeting-reticle styles, size, color, opacity, and animation. See [`docs/tactical-grid-plan.md`](docs/tactical-grid-plan.md).
  - [x] **Bokeh** — render softly animated bokeh lights with configurable population, size, blur, drift, speed, twinkle, and colors derived from two selectable theme palette roles. See [`docs/bokeh-plan.md`](docs/bokeh-plan.md).
  - [x] **Node Mesh** — animate a bounded field of drifting nodes that connects nearby points into a responsive mesh, with configurable density, distance, line treatment, speed, theme roles, and optional pointer attraction or repulsion. See [`docs/node-mesh-plan.md`](docs/node-mesh-plan.md).
  - **Precipitation styles** — extend Rainfall with a precipitation-style selector for rain, snow, and future variants. Give each style appropriate controls while preserving the shared intensity, speed, direction, theme blending, and reduced-motion behavior.
  - Keep every new effect compatible with stack ordering, per-effect enablement, background and foreground presentation, theme changes, reduced motion, multiple outputs, and the existing settings persistence contract.
  - Add contract, normalization, behavior, and performance coverage for each effect before enabling it by default.
