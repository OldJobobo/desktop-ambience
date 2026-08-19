#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"

python -m json.tool manifest.json >/dev/null
omarchy plugin validate "$repo_root"
qmllint -I /usr/share/omarchy/shell \
  Panel.qml components/*.qml effects/*.qml services/*.qml

# Phase 1 severs host and vignette dependencies. The eight byte-preserved
# renderers retain legacy settings readers until Phase 2 injects central state.
runtime_boundary_files=(
  manifest.json
  Panel.qml
  components/*.qml
  effects/VignetteEffect.qml
  services/*.qml
  services/*.js
)
if grep -nE '(/omarchy/lacuna|lacuna\.|lacuna-|lacunaState)' "${runtime_boundary_files[@]}"; then
  echo "Forbidden host or vignette runtime dependency found" >&2
  exit 1
fi

python -m pytest -q tests

echo "Phase 1 checks passed"
