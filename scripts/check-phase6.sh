#!/usr/bin/env bash
set -euo pipefail

if [[ ${JOBO_AMBIENCE_LIVE_PHASE6:-} != 1 ]]; then
  echo "set JOBO_AMBIENCE_LIVE_PHASE6=1 to run the Phase 6 release matrix" >&2
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
evidence_dir="docs/release/evidence/$version"
mkdir -p "$evidence_dir"

./scripts/check.sh | tee "$evidence_dir/automated-checks.txt"
python tests/live_phase6_lifecycle.py | tee "$evidence_dir/lifecycle.log"
python tests/live_phase6_output_modes.py | tee "$evidence_dir/output-modes.log"
python tests/live_phase6_fullscreen.py | tee "$evidence_dir/fullscreen.log"
python tests/live_phase6_visual.py | tee "$evidence_dir/visual-performance.log"

git diff --check
printf 'Phase 6 release matrix passed for v%s\n' "$version"
