"""Scaffold tests using tmp_path and the pure shot planner."""

from __future__ import annotations

import csv
import json
import sys

import pytest

import scaffold_project
from scaffold_project import (
    aspect_ratio,
    build_shots,
    positive_float,
    safe_directory_name,
)


def test_build_shots_does_not_invent_an_extra_shot() -> None:
    shots = build_shots(0.3, 0.1, "t2v")
    assert len(shots) == 3
    assert sum(shot["duration_sec"] for shot in shots) == pytest.approx(0.3)
    assert shots[0]["shot_id"] == "S001"
    assert shots[-1]["start_sec"] == pytest.approx(0.2)

    planned = build_shots(7, 3, "mixed")
    assert [shot["duration_sec"] for shot in planned] == [3, 3, 1]
    assert [shot["start_sec"] for shot in planned] == [0.0, 3, 6]
    assert sum(shot["duration_sec"] for shot in planned) == 7


def test_safe_directory_name_sanitizes_and_rejects_reserved_names() -> None:
    assert safe_directory_name("Demo Project") == "Demo-Project"
    assert safe_directory_name("foo/bar") == "foo-bar"
    assert safe_directory_name("ＡB") == "AB"
    truncated = safe_directory_name(("a" * 99) + "." + ("b" * 10))
    assert truncated == "a" * 99
    assert not truncated.endswith(".")
    with pytest.raises(ValueError, match="usable directory name"):
        safe_directory_name("...")
    with pytest.raises(ValueError, match="usable directory name"):
        safe_directory_name("***")
    with pytest.raises(ValueError, match="reserved on Windows"):
        safe_directory_name("CON")
    with pytest.raises(ValueError, match="reserved on Windows"):
        safe_directory_name("aux.txt")


def test_argument_helpers_reject_non_positive_values() -> None:
    assert positive_float("1.5") == 1.5
    assert aspect_ratio("9:16") == "9:16"
    with pytest.raises(Exception):
        positive_float("0")
    with pytest.raises(Exception):
        aspect_ratio("16/9")


def _argv(monkeypatch, *args: str) -> None:
    monkeypatch.setattr(sys, "argv", ["scaffold_project.py", *args])


def test_scaffold_writes_a_project_in_tmp_path(tmp_path, monkeypatch) -> None:
    _argv(
        monkeypatch,
        "--name",
        "Demo Project",
        "--output",
        str(tmp_path),
        "--duration",
        "7",
        "--shot-length",
        "3",
        "--aspect-ratio",
        "9:16",
        "--fps",
        "24",
        "--mode",
        "t2v",
        "--model",
        "Wan2.2",
    )
    assert scaffold_project.main() == 0
    project = tmp_path / "Demo-Project"
    assert (project / "brief.md").read_text(encoding="utf-8").startswith("# Demo Project")
    assert "9:16" in (project / "visual-direction.md").read_text(encoding="utf-8")
    manifest = json.loads((project / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["shot_count"] == 3
    assert manifest["project"]["fps"] == 24
    assert manifest["project"]["mode"] == "t2v"
    assert manifest["project"]["preferred_model"] == "Wan2.2"
    rows = list(csv.DictReader((project / "shots.csv").read_text(encoding="utf-8-sig").splitlines()))
    assert [row["shot_id"] for row in rows] == ["S001", "S002", "S003"]
    assert sum(float(row["duration_sec"]) for row in rows) == pytest.approx(7)


def test_scaffold_refuses_then_replaces_an_existing_project(tmp_path, monkeypatch) -> None:
    common = [
        "--name",
        "Demo",
        "--output",
        str(tmp_path),
        "--duration",
        "5",
        "--shot-length",
        "5",
    ]
    _argv(monkeypatch, *common)
    assert scaffold_project.main() == 0
    marker = tmp_path / "Demo" / "extra.txt"
    marker.write_text("keep", encoding="utf-8")

    _argv(monkeypatch, *common)
    assert scaffold_project.main() == 1
    assert marker.read_text(encoding="utf-8") == "keep"

    _argv(monkeypatch, *common, "--force")
    assert scaffold_project.main() == 0
    assert not marker.exists()
    assert (tmp_path / "Demo" / "brief.md").is_file()


def test_scaffold_rejects_an_unusable_name(tmp_path, monkeypatch) -> None:
    _argv(monkeypatch, "--name", "...", "--output", str(tmp_path))
    assert scaffold_project.main() == 2
    assert list(tmp_path.iterdir()) == []
