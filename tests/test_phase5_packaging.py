from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_repository_root_is_the_installable_plugin_boundary():
    manifest = json.loads(read("manifest.json"))
    assert ROOT.joinpath(".git").is_dir()
    assert manifest["id"] == "jobo.desktop-ambience"
    assert manifest["kinds"] == ["panel"]
    assert manifest["keepLoaded"] is True
    for entry in manifest["entryPoints"].values():
        path = Path(entry)
        assert not path.is_absolute()
        assert ".." not in path.parts
        resolved = (ROOT / path).resolve()
        assert ROOT in resolved.parents
        assert resolved.is_file()


def test_runtime_files_are_regular_repository_owned_files():
    runtime_paths = [
        ROOT / "manifest.json",
        ROOT / "Panel.qml",
        *sorted((ROOT / "components").glob("*.qml")),
        *sorted((ROOT / "effects").glob("*.qml")),
        *sorted((ROOT / "services").glob("*.qml")),
        *sorted((ROOT / "services").glob("*.js")),
        *sorted((ROOT / "assets").glob("*")),
    ]
    for path in runtime_paths:
        assert path.is_file(), path
        assert not path.is_symlink(), path
        assert ROOT in path.resolve().parents, path


def test_check_script_covers_packaging_runtime_and_forbidden_dependencies():
    check = read("scripts/check.sh")
    for command in (
        "python -m json.tool manifest.json",
        "omarchy plugin validate",
        "qmllint",
        "python -m pytest",
        "git diff --check",
        "python -m compileall",
        "bash -n scripts/check.sh",
    ):
        assert command in check
    assert "unsafe {kind} entry point" in check
    assert "Forbidden runtime dependency found" in check
    assert "Effect-local FileView found" in check
    assert "refusing to report a partial pass" in check


def test_readme_documents_repository_lifecycle_and_owned_state_cleanup():
    readme = read("README.md")
    for heading in (
        "## Requirements",
        "## Install",
        "## Open settings",
        "## Upgrade",
        "## Disable",
        "## Uninstall",
        "## Troubleshooting",
        "## Development",
    ):
        assert heading in readme
    for command in (
        "omarchy plugin add",
        "omarchy plugin enable jobo.desktop-ambience",
        "omarchy plugin update jobo.desktop-ambience",
        "omarchy plugin disable jobo.desktop-ambience",
        "omarchy plugin remove jobo.desktop-ambience",
        "omarchy-shell shell summon jobo.desktop-ambience",
        "omarchy-shell jobo-desktop-ambience status",
    ):
        assert command in readme
    assert "$XDG_CONFIG_HOME/omarchy/jobo/desktop-ambience" in readme
    assert "${XDG_CONFIG_HOME:-$HOME/.config}/omarchy/jobo/desktop-ambience" in readme
