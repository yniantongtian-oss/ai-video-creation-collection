"""Catalog validator tests, including valid and invalid fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import validate_catalog
from validate_catalog import (
    canonical_repository,
    collect_errors,
    validate_repository_url,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "catalog"


def test_valid_fixture_has_no_errors() -> None:
    data = json.loads((FIXTURES / "valid.json").read_text(encoding="utf-8"))
    assert collect_errors(data) == []


def test_invalid_fixture_reports_structural_and_rights_problems() -> None:
    data = json.loads((FIXTURES / "invalid.json").read_text(encoding="utf-8"))
    errors = collect_errors(data)
    joined = "\n".join(errors)
    assert "schema_version must be a non-empty string" in joined
    assert "last_reviewed must use YYYY-MM-DD" in joined
    assert "lowercase kebab-case" in joined
    assert "must be one of:" in joined
    assert "https://github.com" in joined
    assert "official must be true or false" in joined
    assert "license must be a non-empty string" in joined
    assert "capabilities must be a non-empty array" in joined
    assert "when_to_use must be a non-empty string" in joined
    assert "unsupported fields: extra" in joined
    assert "duplicate values" in joined
    assert "duplicates 'sample-one'" in joined
    assert "duplicates 'https://github.com/example/sample/'" in joined
    assert ".git suffix" in joined


def test_repository_url_rules_and_canonical_identity() -> None:
    assert validate_repository_url("https://github.com/acme/widget") is None
    assert validate_repository_url("https://github.com/acme/widget/") is None
    assert "query" in validate_repository_url("https://github.com/acme/widget?ref=1")
    assert ".git" in validate_repository_url("https://github.com/acme/widget.git")
    assert "whitespace" in validate_repository_url("https://github.com/acme/widget ")
    assert canonical_repository("https://github.com/Example/Sample/") == canonical_repository(
        "https://github.com/example/sample"
    )


def test_collect_errors_rejects_empty_and_non_object_catalogs() -> None:
    assert collect_errors([]) == ["catalog root must be an object"]
    errors = collect_errors(
        {"schema_version": "1.0.0", "last_reviewed": "2026-10-22", "projects": []}
    )
    assert any("non-empty" in error for error in errors)


def test_repository_catalog_is_current() -> None:
    assert validate_catalog.main() == 0
    data = json.loads((ROOT / "catalog" / "projects.json").read_text(encoding="utf-8"))
    assert data["last_reviewed"] == "2026-10-22"
    by_id = {project["id"]: project for project in data["projects"]}
    for project_id in (
        "wan2-1",
        "ltx-2",
        "framepack",
        "mochi",
        "skyreels-v2",
        "longcat-video",
        "magi-1",
    ):
        assert project_id in by_id
    assert by_id["ltx-2"]["repository"] == "https://github.com/Lightricks/LTX-2"
    assert "South Korea" in by_id["hunyuanvideo-1-5"]["notes"]
    assert collect_errors(data) == []
