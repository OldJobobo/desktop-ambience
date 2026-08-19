# Phase 7 Performance Characterization

Date: 2026-08-19

## Scope

Phase 7 preserves the `v0.4.0` renderer output and settings contract while establishing per-effect measurements and removing cursor polling ownership from each per-output Dust Motes renderer.

The first optimization deliberately does not rewrite effect visuals. One `CursorTracker.qml` instance now belongs to the persistent panel root and supplies the same global cursor coordinates, velocity, and kick to every Dust Motes instance.

## Method

`tests/live_phase7_performance.py` runs with temporary XDG homes and three reversible headless Hyprland outputs. Every scenario starts a fresh Quickshell process and records:

- process CPU utilization from `/proc/<pid>/stat`;
- peak RSS from `/proc/<pid>/status`;
- QML frame callback cadence;
- output count; and
- exact shared cursor launch count when the target checkout supports it.

The harness accepts `--target-root`, allowing the current test driver to profile the immutable `v0.4.0` worktree and the Phase 7 candidate under the same environment.

## Per-effect baseline

The baseline covers all eight ordered effects, the dedicated vignette, and the released three-effect stack at one and three outputs. CPU values are directional single samples rather than cross-machine guarantees.

Rainfall was the most expensive individual renderer in this matrix:

| Scenario | One output | Three outputs |
| --- | ---: | ---: |
| Rainfall `v0.4.0` | 38.22% CPU | 48.60% CPU |
| Three-effect stack `v0.4.0` | 58.00% CPU | 70.29% CPU |

The next renderer investigation should therefore begin with Rainfall. No Rainfall rewrite is included in this consolidation change because Phase 7 requires renderer changes to remain independently reviewable and revertible.

## Shared cursor result

Dust Motes was repeated five times for each output count using a two-second steady sample.

| Measurement | `v0.4.0`, 1 output | Shared tracker, 1 output | `v0.4.0`, 3 outputs | Shared tracker, 3 outputs |
| --- | ---: | ---: | ---: | ---: |
| Median CPU | 4.99% | 4.99% | 8.97% | 6.82% |
| Median peak RSS | 287.0 MiB | 286.8 MiB | 304.1 MiB | 304.2 MiB |
| Median frame callback | 16.61 ms | 16.66 ms | 16.95 ms | 16.55 ms |
| Cursor launches in each sample | estimated 17 | 17 exact | estimated 50 | 17 exact |

The three-output median CPU fell by approximately 24%. More importantly, cursor process launches no longer multiply by output count: all five candidate runs launched exactly 17 samplers for both one and three outputs. The released design would schedule approximately 50 launches across three independent 120 ms timers during the same two-second interval.

## Activation and ownership

The tracker runs only when all of the following are true:

- global ambience is enabled;
- Dust Motes is selected and enabled;
- its effective intensity is non-zero;
- mouse reactivity is enabled;
- reduced motion is disabled; and
- at least one mapped ambience output is allowed to paint.

Runtime status exposes active/running state, launch count, failure count, and the latest error. Dust Motes owns no `Process`, cursor timer, or Quickshell I/O import.

## Evidence

- `evidence/phase7/v0.4.0-baseline.json`
- `evidence/phase7/shared-cursor.json`
- `evidence/phase7/v0.4.0-dust-repeated.json`
- `evidence/phase7/shared-cursor-dust-repeated.json`

These measurements describe this machine and session. They rank local hotspots and validate ownership changes; they are not general performance guarantees.
