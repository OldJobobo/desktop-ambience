from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_manifest_version_is_semver_and_has_release_notes():
    version = json.loads(read("manifest.json"))["version"]
    assert re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", version)
    assert f"## [{version}] - " in read("CHANGELOG.md")


def test_version_has_one_runtime_source_and_is_injected_into_settings():
    panel = read("Panel.qml")
    window = read("components/SettingsWindow.qml")
    assert "root.manifest.version" in panel
    assert "pluginVersion: root.pluginVersion" in panel
    assert 'property string pluginVersion: ""' in window
    assert "root.pluginVersion.toUpperCase()" in window
    assert "0.4.0" not in panel
    assert "0.4.0" not in window


def test_ci_runs_host_independent_contract_and_release_checks():
    workflow = read(".github/workflows/ci.yml")
    assert "pull_request:" in workflow
    assert "permissions:\n  contents: read" in workflow
    assert "./scripts/check-contracts.sh" in workflow
    assert "./scripts/release-check.sh" in workflow
    assert "github.ref_type != 'tag'" in workflow
    assert "./scripts/release-check.sh --tagged" in workflow
    assert "timeout-minutes:" in workflow


def test_release_process_requires_semver_changelog_clean_tree_and_live_evidence():
    release = read("scripts/release-check.sh")
    contributing = read("CONTRIBUTING.md")
    for contract in (
        "Semantic Versioning", "CHANGELOG.md", "clean working tree",
        "docs/release/v$version.md", "tag already exists",
    ):
        assert contract in release or contract in contributing
    assert "--tagged" in release
    assert 'refs/tags/v$version^{commit}' in release
    assert "./scripts/check-contracts.sh" in contributing
    assert "./scripts/check.sh" in contributing
    assert "Never tag a release with skipped runtime tests" in contributing


def test_support_link_is_https_and_opens_externally():
    window = read("components/SettingsWindow.qml")
    assert 'readonly property url donationUrl: "https://ko-fi.com/oldjobobo"' in window
    assert "Qt.openUrlExternally(donationUrl)" in window
    assert 'text: "Donate"' in window
