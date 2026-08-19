#!/usr/bin/env bash
set -euo pipefail

action=${1:-install}
menu_file="$HOME/.config/omarchy/extensions/omarchy-menu.jsonc"

case "$action" in
  install|remove|status) ;;
  *)
    echo "Usage: $0 [install|remove|status]" >&2
    exit 2
    ;;
esac

python - "$action" "$menu_file" <<'PY'
from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path

ACTION = sys.argv[1]
PATH = Path(sys.argv[2])
START = "// jobo-desktop-ambience-menu-start"
END = "// jobo-desktop-ambience-menu-end"
ENTRY = (
    '  "desktop-ambience": {'
    '"icon":"󰖔",'
    '"label":"Desktop Ambience",'
    '"description":"Compose desktop animation and vignette effects",'
    '"keywords":"desktop ambience animation effects vignette",'
    '"action":"omarchy-shell shell summon jobo.desktop-ambience \'{}\'"'
    '}'
)
PATTERN = re.compile(
    r"^[ \t]*" + re.escape(START) + r"\n.*?^[ \t]*" + re.escape(END) + r"\n?",
    re.MULTILINE | re.DOTALL,
)


def installed(text: str) -> bool:
    return START in text and END in text


def write_atomic(text: str) -> None:
    PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{PATH.name}.", dir=PATH.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        if PATH.exists():
            os.chmod(temporary, PATH.stat().st_mode)
        os.replace(temporary, PATH)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


text = PATH.read_text(encoding="utf-8") if PATH.exists() else "{\n}\n"

if ACTION == "status":
    print("installed" if installed(text) else "not-installed")
    raise SystemExit(0 if installed(text) else 1)

cleaned = PATTERN.sub("", text)
if ACTION == "remove":
    if cleaned != text:
        write_atomic(cleaned)
        print(f"Removed Desktop Ambience from {PATH}")
    else:
        print("Desktop Ambience menu entry is not installed")
    raise SystemExit(0)

opening = cleaned.find("{")
closing = cleaned.rfind("}")
if opening < 0 or closing <= opening:
    raise SystemExit(f"Menu extension is not an object: {PATH}")

body = cleaned[opening + 1:closing]
without_comments = re.sub(r"/\*.*?\*/|//[^\n]*", "", body, flags=re.DOTALL).strip()
comma = "," if without_comments else ""
block = f"\n{START}\n{ENTRY}{comma}\n{END}\n"
updated = cleaned[:opening + 1] + block + cleaned[opening + 1:]
write_atomic(updated)
print(f"Installed Desktop Ambience in {PATH}")
PY
