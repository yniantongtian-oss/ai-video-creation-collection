"""Unit tests for manifest hashing and rights checks."""

from __future__ import annotations

import argparse
import json

import pytest

from media_asset_manifest import (
    DEFAULT_ALLOWED,
    ManifestError,
    command_set_selected,
    command_validate,
    file_sha256,
    is_https_url,
    read_entries,
    validation_errors,
    write_entries,
)

EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def _paths(tmp_path):
    target = tmp_path / "assets" / "clip.bin"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"frame-bytes")
    manifest = tmp_path / "manifests" / "assets.jsonl"
    manifest.parent.mkdir(parents=True)
    return manifest, target


def _entry(**overrides):
    entry = {
        "id": "clip-1",
        "kind": "image",
        "local_path": "assets/clip.bin",
        "source_url": "HTTPS://example.com/clip",
        "provider": "Example",
        "title": "Clip",
        "creator": "Ada",
        "license": "CC0",
        "license_url": "",
        "rights_status": "cc0",
        "attribution": "",
        "permission_note": "",
        "selected": True,
        "sha256": "",
        "notes": "",
    }
    entry.update(overrides)
    return entry


def test_file_sha256_of_empty_file(tmp_path) -> None:
    empty = tmp_path / "empty.bin"
    empty.write_bytes(b"")
    assert file_sha256(empty) == EMPTY_SHA256


def test_is_https_url_accepts_only_absolute_https() -> None:
    assert is_https_url("HTTPS://example.com/a")
    assert not is_https_url("http://example.com/a")
    assert not is_https_url("https://")
    assert not is_https_url(None)
    assert not is_https_url("example.com")


def test_validation_does_not_mutate_entries(tmp_path) -> None:
    manifest, _target = _paths(tmp_path)
    item = _entry()
    original = json.loads(json.dumps(item))
    assert validation_errors([item], manifest, DEFAULT_ALLOWED) == []
    assert item == original


def test_validation_accepts_uppercase_sha256(tmp_path) -> None:
    manifest, target = _paths(tmp_path)
    item = _entry(sha256=file_sha256(target).upper())
    assert validation_errors([item], manifest, DEFAULT_ALLOWED) == []


def test_validation_rejects_rights_and_duplicate_ids(tmp_path) -> None:
    manifest, _target = _paths(tmp_path)
    http_item = _entry(source_url="http://example.com/a")
    assert any("HTTPS" in error for error in validation_errors([http_item], manifest, DEFAULT_ALLOWED))

    missing_creator = _entry(
        rights_status="cc-by",
        creator="",
        license_url="https://creativecommons.org/licenses/by/4.0/",
    )
    assert any(
        "creator" in error
        for error in validation_errors([missing_creator], manifest, DEFAULT_ALLOWED)
    )

    owned = _entry(
        rights_status="user-owned",
        source_url="",
        permission_note="Owned by the project",
    )
    assert validation_errors([owned], manifest, DEFAULT_ALLOWED) == []

    duplicate = validation_errors([_entry(), _entry()], manifest, DEFAULT_ALLOWED)
    assert any("duplicate" in error for error in duplicate)

    missing = _entry(local_path="assets/missing.bin")
    assert any("missing" in error for error in validation_errors([missing], manifest, DEFAULT_ALLOWED))


def test_read_entries_rejects_non_objects_and_invalid_json(tmp_path) -> None:
    manifest, _target = _paths(tmp_path)
    manifest.write_text("[]\n", encoding="utf-8")
    with pytest.raises(ManifestError, match="JSON object"):
        read_entries(manifest)
    manifest.write_text("{bad}\n", encoding="utf-8")
    with pytest.raises(ManifestError, match="invalid JSON"):
        read_entries(manifest)
    assert read_entries(tmp_path / "missing.jsonl") == []


def test_set_selected_persists_sha256(tmp_path) -> None:
    manifest, target = _paths(tmp_path)
    write_entries(manifest, [_entry(selected=False, sha256="")])
    args = argparse.Namespace(
        manifest=manifest,
        id=["clip-1"],
        ids_file=None,
        value="true",
        note="reviewed",
        allowed="",
    )
    assert command_set_selected(args) == 0
    saved = read_entries(manifest)[0]
    assert saved["selected"] is True
    assert saved["sha256"] == file_sha256(target)


def test_validate_command_does_not_rewrite_the_manifest(tmp_path) -> None:
    manifest, _target = _paths(tmp_path)
    write_entries(manifest, [_entry(sha256="")])
    before = manifest.read_bytes()
    args = argparse.Namespace(manifest=manifest, allowed="")
    assert command_validate(args) == 0
    assert manifest.read_bytes() == before
