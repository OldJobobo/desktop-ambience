#!/usr/bin/env bash
set -euo pipefail

if [[ ${JOBO_AMBIENCE_LIVE_PHASE7:-} != 1 ]]; then
  echo "set JOBO_AMBIENCE_LIVE_PHASE7=1 to run the Phase 7 performance and parity matrix" >&2
  exit 2
fi

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"

version=$(python - <<'PY'
import json
from pathlib import Path
print(json.loads(Path("manifest.json").read_text(encoding="utf-8"))["version"])
PY
)

./scripts/check.sh
python tests/live_phase7_performance.py \
  --output "docs/performance/evidence/$version/phase7-performance.json"
JOBO_AMBIENCE_LIVE_PHASE6=1 ./scripts/check-phase6.sh

printf 'Phase 7 performance and parity matrix passed for v%s\n' "$version"
