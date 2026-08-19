#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"

python -m json.tool manifest.json >/dev/null
omarchy plugin validate "$repo_root"

if grep -RInE --include='*.qml' --include='*.js' --include='*.json' \
  '(/omarchy/lacuna|lacuna\.)' .; then
  echo "Forbidden runtime dependency found" >&2
  exit 1
fi

echo "Scaffold checks passed"
