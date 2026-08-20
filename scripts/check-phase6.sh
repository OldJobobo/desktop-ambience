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

write_versioned_json() {
  python - "$1" "$2" "$version" <<'PY'
import json
import sys
from pathlib import Path
source = Path(sys.argv[1])
destination = Path(sys.argv[2])
version = sys.argv[3]
payload = json.loads(source.read_text(encoding="utf-8"))
payload["pluginVersion"] = version
destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY
}

write_versioned_json \
  "docs/release/evidence/rainfall-extraction-parity.json" \
  "$evidence_dir/rainfall-extraction-parity.json"

./scripts/check-contracts.sh | tee "$evidence_dir/contract-checks.txt"
./scripts/check.sh | tee "$evidence_dir/automated-checks.txt"
python tests/live_phase6_lifecycle.py | tee "$evidence_dir/lifecycle.log"
python tests/live_phase6_output_modes.py | tee "$evidence_dir/output-modes.log"
write_versioned_json "$evidence_dir/output-modes.json" "$evidence_dir/output-modes.json"
python tests/live_phase6_fullscreen.py | tee "$evidence_dir/fullscreen.log"
write_versioned_json "$evidence_dir/fullscreen.json" "$evidence_dir/fullscreen.json"
python tests/live_phase6_visual.py | tee "$evidence_dir/visual-performance.log"
JOBO_AMBIENCE_NODE_MESH_PIXEL_PROBE=1 \
  python tests/live_node_mesh_pixel_probe.py | tee "$evidence_dir/node-mesh-pixels.log"
write_versioned_json \
  "docs/performance/evidence/node-mesh-pixels.json" \
  "$evidence_dir/node-mesh-pixels.json"
python tests/live_node_mesh_multi_output_visual.py | tee "$evidence_dir/node-mesh-multi-output.log"
write_versioned_json \
  "docs/release/evidence/node-mesh-multi-output.json" \
  "$evidence_dir/node-mesh-multi-output.json"
python tests/live_precipitation_multi_output_visual.py | tee "$evidence_dir/precipitation-multi-output.log"
write_versioned_json \
  "docs/release/evidence/precipitation-multi-output.json" \
  "$evidence_dir/precipitation-multi-output.json"

git diff --check
printf 'Phase 6 release matrix passed for v%s\n' "$version"
