#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"

stable=0
tagged=0
for option in "$@"; do
  case "$option" in
    --stable) stable=1 ;;
    --tagged) tagged=1; stable=1 ;;
    *) echo "Usage: $0 [--stable] [--tagged]" >&2; exit 2 ;;
  esac
done

version=$(python - <<'PY'
import json
from pathlib import Path
print(json.loads(Path("manifest.json").read_text(encoding="utf-8"))["version"])
PY
)

if [[ ! $version =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?$ ]]; then
  echo "manifest version is not Semantic Versioning: $version" >&2
  exit 1
fi

if ! python - "$version" <<'PY'
import re
import sys
from pathlib import Path
version = re.escape(sys.argv[1])
text = Path("CHANGELOG.md").read_text(encoding="utf-8")
raise SystemExit(0 if re.search(rf"^## \[{version}\] - \d{{4}}-\d{{2}}-\d{{2}}$", text, re.MULTILINE) else 1)
PY
then
  echo "CHANGELOG.md needs a dated [$version] section" >&2
  exit 1
fi

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "release checks require a clean working tree" >&2
  exit 1
fi

if (( stable )); then
  if [[ $version == *-* ]]; then
    echo "stable release cannot use prerelease version: $version" >&2
    exit 1
  fi
  evidence="docs/release/v$version.md"
  if [[ ! -s $evidence ]]; then
    echo "stable release evidence is missing: $evidence" >&2
    exit 1
  fi
fi

if git rev-parse -q --verify "refs/tags/v$version" >/dev/null; then
  if (( ! tagged )); then
    echo "tag already exists: v$version" >&2
    exit 1
  fi
  if [[ $(git rev-parse "refs/tags/v$version^{commit}") != $(git rev-parse HEAD) ]]; then
    echo "tag v$version does not point to HEAD" >&2
    exit 1
  fi
elif (( tagged )); then
  echo "tag is missing: v$version" >&2
  exit 1
fi

if (( tagged )); then
  printf 'Tagged release verified for v%s\n' "$version"
else
  printf 'Release metadata ready for v%s\n' "$version"
fi
