# Node Mesh renderer selection

## Decision

Use one retained `Shape` with eight declarative `ShapePath` objects. Each path owns a retained `PathMultiline` geometry bucket for one distance-opacity band. Declaring the paths with the `Shape` is the render-proven lifecycle on this Qt runtime; dynamically parenting `ShapePath` objects to an already-completed `Shape` did not produce connection pixels and was rejected during final review.

Do not use the immediate `Canvas` prototype on the tested runtime. Both final prototypes visibly draw the same deterministic edge geometry with the same eight opacity bands, but Canvas remains substantially more expensive.

## Pixel equivalence prerequisite

`tests/live_node_mesh_pixel_probe.py` captures production line-opacity off/on and short/long distance cases plus both renderer prototypes. The probe must pass before the benchmark runs. Recorded evidence in `evidence/node-mesh-pixels.json` shows:

- 2,779 production pixels changed when line opacity moved from zero to one;
- 14,112 pixels changed when connection distance moved from 132 to 260 px;
- long-distance output contained 14,525 visible pixels versus 3,368 at the short distance;
- Canvas and Shape both drew all 31 accepted prototype edges; and
- 99.93% of the smaller renderer mask overlaps the other renderer. Canvas antialiasing covers more fringe pixels, so byte identity is neither expected nor used as the equivalence criterion.

## Method

`tests/live_node_mesh_renderer_benchmark.py` renders otherwise identical Canvas and Shape prototypes in isolated Quickshell processes. Both prototypes use the same deterministic node state, uniform-grid candidate discovery, four-neighbor degree cap, fixed 30 Hz update gate, connection cutoff, opacity buckets, and published segment count. The live harness creates reversible 1920×1080 headless Hyprland outputs at negative origins and measures default and maximum settings on one and three outputs.

The recorded run used:

- Qt 6.11.1;
- Quickshell 0.3.0 (`quickshell-git` revision `28771c7c74b42e20afca0b1b63980cb46515537c`);
- a declared 1.2-second QML warmup before the `BENCH_READY` resource boundary;
- an independently bounded 3-second CPU/RSS sample after that boundary; and
- three fresh-process repetitions per renderer/scenario/output count.

CPU ticks and RSS sampling now begin only when the post-warmup marker is observed and stop at the independent 3-second resource deadline. Evidence records the measured sample separately from total process lifetime: the 24 samples measured 3.00002–3.00011 seconds while total process lifetimes were 4.638–5.078 seconds. CPU and memory values are machine-local directional comparisons, not portable release thresholds.

## Results

Median values from `evidence/node-mesh-renderer.json`:

| Scenario | Outputs | Canvas CPU | Shape CPU | Canvas RSS | Shape RSS | Canvas median max callback | Shape median max callback |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Default: 54 nodes, 132 px | 1 | 43.33% | 5.00% | 297.4 MiB | 271.9 MiB | 33.26 ms | 33.80 ms |
| Maximum: 120 nodes, 260 px | 1 | 56.00% | 8.67% | 298.4 MiB | 272.7 MiB | 33.34 ms | 19.13 ms |
| Default: 54 nodes, 132 px | 3 | 44.00% | 7.00% | 336.8 MiB | 282.2 MiB | 30.76 ms | 19.07 ms |
| Maximum: 120 nodes, 260 px | 3 | 62.33% | 16.67% | 339.8 MiB | 285.4 MiB | 34.74 ms | 22.97 ms |

Both prototypes accepted 29.7–30.7 updates per second per output in all samples. Each row reported a non-zero edge population and a rendered segment count equal to its accepted edge count. Maximum-density samples produced 207 edges on one output and 618–621 across three outputs, versus ceilings of 240 and 720 respectively.

## Production constraints pinned by this comparison

- One `FrameAnimation`, with at most one fixed-step simulation update per callback and stalled-frame backlog reset.
- One retained `Shape` line surface per output.
- Eight declarative `ShapePath`/`PathMultiline` opacity buckets; no ShapePath allocation during steady-state simulation.
- At most four incident connections per node, each undirected pair emitted once.
- One bounded node-disc `Repeater`; geometry and state remain shared with the line surface.
- A pixel probe must continue to prove non-blank lines, visible line-opacity/distance changes, and Canvas/Shape geometry equivalence.

Shape remained materially cheaper in CPU and RSS in every cell. Median maximum callback time was lower in three cells and within 2% of Canvas in the one-output default cell, so callback stability remains comparable rather than universally lower. The three-output maximum Shape sample remained bounded and materially cheaper than Canvas. No reduction to the 120-node maximum or 30 Hz update cadence is warranted by this comparison.

## Reproduction

```bash
JOBO_AMBIENCE_NODE_MESH_PIXEL_PROBE=1 \
  python tests/live_node_mesh_pixel_probe.py
JOBO_AMBIENCE_NODE_MESH_BENCHMARK=1 \
  python tests/live_node_mesh_renderer_benchmark.py \
  --duration-ms 3000 --repetitions 3
```

Both commands use isolated configuration. The benchmark creates and removes three headless outputs and writes `docs/performance/evidence/node-mesh-renderer.json`.
