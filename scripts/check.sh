#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"

python -m json.tool manifest.json >/dev/null
omarchy plugin validate "$repo_root"
qmllint -I /usr/share/omarchy/shell \
  Panel.qml components/*.qml effects/*.qml services/*.qml

runtime_files=(
  manifest.json
  Panel.qml
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
  echo "Phase 3 behavior checks require quickshell and an active Wayland session; refusing to report a partial pass" >&2
  exit 1
fi

pytest_output=$(mktemp)
trap 'rm -f "$pytest_output"' EXIT
python -m pytest -q tests -rs | tee "$pytest_output"
if grep -Eq '[0-9]+ skipped' "$pytest_output"; then
  echo "Phase 3 behavior coverage was skipped" >&2
  exit 1
fi

echo "Phase 3 checks passed with runtime behavior coverage"
