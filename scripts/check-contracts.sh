#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"

python -m json.tool manifest.json >/dev/null
python - <<'PY'
import json
from pathlib import Path

root = Path.cwd().resolve()
manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
for kind, entry in manifest.get("entryPoints", {}).items():
    path = Path(entry)
    if path.is_absolute() or ".." in path.parts:
        raise SystemExit(f"unsafe {kind} entry point: {entry}")
    resolved = (root / path).resolve()
    if root not in resolved.parents or not resolved.is_file():
        raise SystemExit(f"missing or external {kind} entry point: {entry}")
PY

for script in scripts/*.sh; do bash -n "$script"; done
python -m compileall -q tests

runtime_files=(
  manifest.json
  Panel.qml
  BarWidget.qml
  components/*.qml
  effects/*.qml
  services/*.qml
  services/*.js
)

if grep -inE '(lacuna|/home/|Projects/|compatibility alias)' "${runtime_files[@]}"; then
  echo "Forbidden runtime dependency found" >&2
  exit 1
fi

if grep -n 'FileView' effects/*.qml; then
  echo "Effect-local FileView found" >&2
  exit 1
fi

file_view_owners=$(grep -l 'property FileView' "${runtime_files[@]}" | sort || true)
expected_owners=$'services/AmbienceSettings.qml\nservices/ThemeAdapter.qml'
if [[ "$file_view_owners" != "$expected_owners" ]]; then
  printf 'Unexpected runtime FileView owners:\n%s\n' "$file_view_owners" >&2
  exit 1
fi

python -m pytest -q \
  tests/test_phase1_contracts.py \
  tests/test_phase2_contracts.py \
  tests/test_phase3_contracts.py \
  tests/test_phase4_contracts.py \
  tests/test_phase5_packaging.py \
  tests/test_launcher_integrations.py \
  tests/test_phase6_release.py \
  tests/test_phase7_contracts.py \
  tests/test_bokeh_contracts.py \
  tests/test_node_mesh_renderer_contracts.py \
  tests/test_node_mesh_contracts.py \
  tests/test_rainfall_baseline_contracts.py \
  tests/test_precipitation_settings.py \
  tests/test_precipitation_styles.py \
  tests/test_precipitation_release.py \
  tests/test_sdlc.py \
  -k 'not BarWidgetBehaviorTests'

git diff --check

echo "Host-independent contract checks passed"
