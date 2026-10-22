"""Tests for the spec-driven pipeline orchestrator."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import run_pipeline
from run_pipeline import (
    PipelineSpecError,
    build_plan,
    load_spec,
    plan_warnings,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "config" / "pipeline-spec.example.json"
LONGFORM_SCRIPTS = [
    "scripts/scaffold_longform_project.py",
    "scripts/ingest_longform_corpus.py",
    "scripts/longform_pipeline.py",
    "scripts/build_longform_asset_plan.py",
    "scripts/render_longform_narration.py",
    "scripts/build_longform_timeline.py",
    "scripts/render_longform_chapters.py",
    "scripts/assemble_longform_video.py",
]


def _longform(**overrides):
    spec = {
        "schema_version": "1.0.0",
        "pipeline": "longform",
        "name": "City Water",
        "topic": "How a city water system works",
        "output": "projects",
        "duration_minutes": 60,
        "chapter_minutes": 10,
    }
    spec.update(overrides)
    return spec


def test_example_spec_chains_the_longform_scripts() -> None:
    normalized, commands = build_plan(load_spec(EXAMPLE))
    assert [command[0] for command in commands] == LONGFORM_SCRIPTS
    assert normalized["duration_minutes"] == 60
    assert plan_warnings(normalized["stages"])


def test_stages_run_in_canonical_order(tmp_path) -> None:
    normalized, commands = build_plan(
        _longform(output=str(tmp_path), stages=["timeline", "scaffold"], chapters=[2])
    )
    assert normalized["stages"] == ["scaffold", "timeline"]
    assert [command[0] for command in commands] == [
        "scripts/scaffold_longform_project.py",
        "scripts/build_longform_timeline.py",
    ]
    project = commands[1][commands[1].index("--project") + 1]
    assert Path(project).name == "City Water"
    assert commands[1][commands[1].index("--chapter") + 1] == "2"
    assert "--allow-placeholders" not in commands[1]


def test_asset_search_flags_are_explicit(tmp_path) -> None:
    _normalized, commands = build_plan(
        _longform(
            output=str(tmp_path),
            stages=["assets"],
            execute_search=True,
            download_first=2,
        )
    )
    command = commands[0]
    assert "--execute" in command
    assert command[command.index("--download-first") + 1] == "2"
    assert command[command.index("--limit") + 1] == "8"


def test_spec_validation_rejects_unsafe_plans(tmp_path) -> None:
    with pytest.raises(PipelineSpecError, match="between 30 and 360"):
        build_plan(_longform(output=str(tmp_path), duration_minutes=10))
    with pytest.raises(PipelineSpecError, match="pipeline must be one of"):
        build_plan({"schema_version": "1.0.0", "pipeline": "nope", "name": "Demo"})
    with pytest.raises(PipelineSpecError, match="chapter subset"):
        build_plan(_longform(output=str(tmp_path), stages=["scaffold", "assemble"], chapters=[1]))
    with pytest.raises(PipelineSpecError, match="usable directory name"):
        build_plan(
            {
                "schema_version": "1.0.0",
                "pipeline": "generation",
                "name": "***",
                "output": str(tmp_path),
            }
        )


def test_dry_run_prints_commands_without_creating_a_project(tmp_path, monkeypatch, capsys) -> None:
    spec_path = tmp_path / "spec.json"
    output = tmp_path / "out"
    spec_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "pipeline": "generation",
                "name": "Demo Project",
                "output": str(output),
                "duration_seconds": 7,
                "shot_length": 3,
                "mode": "t2v",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_pipeline.py", "--spec", str(spec_path), "--dry-run"],
    )
    assert run_pipeline.main() == 0
    assert not output.exists()
    assert "scripts/scaffold_project.py" in capsys.readouterr().out


def test_generation_and_longform_scaffold_execute(tmp_path, monkeypatch) -> None:
    output = tmp_path / "out"
    generation = tmp_path / "generation.json"
    generation.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "pipeline": "generation",
                "name": "Demo Project",
                "output": str(output),
                "duration_seconds": 7,
                "shot_length": 3,
                "aspect_ratio": "16:9",
                "mode": "t2v",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["run_pipeline.py", "--spec", str(generation)])
    assert run_pipeline.main() == 0
    project = output / "Demo-Project"
    manifest = json.loads((project / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["shot_count"] == 3
    assert (project / "shots.csv").is_file()

    longform = tmp_path / "longform.json"
    longform.write_text(
        json.dumps(
            _longform(output=str(output / "longform"), stages=["scaffold"], name="Harbor Notes")
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["run_pipeline.py", "--spec", str(longform)])
    assert run_pipeline.main() == 0
    assert (output / "longform" / "Harbor Notes" / "project.json").is_file()


def test_missing_project_stage_returns_failure(tmp_path, monkeypatch) -> None:
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(
        json.dumps(_longform(output=str(tmp_path / "missing"), stages=["ingest"])),
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["run_pipeline.py", "--spec", str(spec_path)])
    assert run_pipeline.main() == 1


def test_invalid_spec_file_returns_usage_status(tmp_path, monkeypatch, capsys) -> None:
    spec_path = tmp_path / "spec.json"
    spec_path.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["run_pipeline.py", "--spec", str(spec_path)])
    assert run_pipeline.main() == 2
    assert "object" in capsys.readouterr().err
