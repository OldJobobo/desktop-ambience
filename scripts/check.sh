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
omarchy plugin validate "$repo_root"
bash -n scripts/check.sh
bash -n scripts/menu-entry.sh
python -m compileall -q tests
qmllint -I /usr/share/omarchy/shell \
  Panel.qml BarWidget.qml components/*.qml effects/*.qml services/*.qml

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

[[ $(grep -c 'AmbienceSettings { id: ambienceSettings }' Panel.qml) -eq 1 ]]
[[ $(grep -c 'ThemeAdapter { id: themeAdapter }' Panel.qml) -eq 1 ]]

if ! command -v quickshell >/dev/null 2>&1 || [[ -z ${WAYLAND_DISPLAY:-} ]]; then
  echo "Phase 5 behavior checks require quickshell and an active Wayland session; refusing to report a partial pass" >&2
  exit 1
fi

pytest_output=$(mktemp)
trap 'rm -f "$pytest_output"' EXIT
python -m pytest -q tests -rs | tee "$pytest_output"
if grep -Eq '[0-9]+ skipped' "$pytest_output"; then
  echo "Phase 5 behavior coverage was skipped" >&2
  exit 1
fi

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git diff --check
fi

echo "Phase 5 checks passed with runtime behavior coverage"
