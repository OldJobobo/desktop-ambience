# Contributing

## Development lifecycle

1. Start from a clean `main` branch.
2. Create a short-lived branch for one fix or feature.
3. Add or update tests with the code.
4. Run `./scripts/check-contracts.sh` during development.
5. Run `./scripts/check.sh` from an active Omarchy Wayland session before merge.
6. Record user-visible changes in `CHANGELOG.md`.
7. Open a pull request with the problem, change, validation, and remaining risks.
8. Merge only after CI and local runtime checks pass.

Keep renderer-body changes separate from host, settings, and packaging changes. Renderer changes require new visual comparison evidence.

## Version policy

`manifest.json` is the canonical version source. The settings window reads that value at runtime.

Versions follow Semantic Versioning:

- **Patch** (`0.3.1`): compatible fixes, copy changes, and internal maintenance.
- **Minor** (`0.4.0`): compatible features or meaningful UI additions.
- **Major** (`1.0.0`): the stable public contract. After 1.0, breaking settings, IPC, manifest, or installation changes increment the major version.
- **Prerelease** (`0.4.0-rc.1`): a release candidate still completing live validation.

Before 1.0, a breaking contract change increments the minor version and must include migration notes.

Do not bump the version for every commit. Choose the next version when a release candidate is cut, then keep follow-up fixes under that candidate until release.

## Required checks

Fast, host-independent checks:

```bash
./scripts/check-contracts.sh
```

Complete Omarchy runtime checks:

```bash
./scripts/check.sh
```

Release metadata and clean-tree check:

```bash
./scripts/release-check.sh
```

Phase 6 live validation remains required before a stable tag. Record its hardware, visual, lifecycle, and performance evidence under `docs/release/`.

## Release process

1. Confirm Phase 6 evidence covers the supported hardware and lifecycle matrix.
2. Choose the final version and update `manifest.json`.
3. Move the completed entries from **Unreleased** into a matching dated section in `CHANGELOG.md`.
4. Run `./scripts/check-contracts.sh` and `./scripts/check.sh`.
5. Commit with `Release v<version>`.
6. Run `./scripts/release-check.sh` from the clean release commit.
7. Create an annotated tag: `git tag -a v<version> -m "Desktop Ambience v<version>"`.
8. Push the commit and tag, then verify installation and upgrade from the published Git URL.

Never tag a release with skipped runtime tests, uncommitted changes, or missing Phase 6 evidence.
