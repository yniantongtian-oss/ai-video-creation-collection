"""Unit tests for pure helpers in longform_common.py."""

from __future__ import annotations

import json
import os

import pytest

import longform_common
from longform_common import (
    LongformError,
    append_jsonl,
    env_float,
    env_int,
    load_dotenv,
    parse_dotenv_assignment,
    parse_ffmpeg_duration,
    read_json,
    update_chapter_stage,
    update_pipeline_stage,
    write_json,
)


def test_parse_dotenv_assignment_handles_export_quotes_and_comments() -> None:
    assert parse_dotenv_assignment("  # comment") is None
    assert parse_dotenv_assignment("") is None
    assert parse_dotenv_assignment("export KEY=value") == ("KEY", "value")
    assert parse_dotenv_assignment('KEY="a=b"') == ("KEY", "a=b")
    assert parse_dotenv_assignment("KEY=\"'inner'\"") == ("KEY", "'inner'")
    assert parse_dotenv_assignment("KEY=value # trailing") == ("KEY", "value")
    assert parse_dotenv_assignment("KEY=value#keep") == ("KEY", "value#keep")
    assert parse_dotenv_assignment("=missing") is None


def test_load_dotenv_reads_bom_and_does_not_override(tmp_path, monkeypatch) -> None:
    path = tmp_path / ".env"
    path.write_bytes(
        "\ufeffexport DEMO_EXPORT=from-file\nDEMO_ONLY=present\n".encode("utf-8")
    )
    monkeypatch.delenv("DEMO_EXPORT", raising=False)
    monkeypatch.delenv("DEMO_ONLY", raising=False)
    monkeypatch.setenv("DEMO_EXPORT", "already")

    load_dotenv(path)

    assert os.environ["DEMO_EXPORT"] == "already"
    assert os.environ["DEMO_ONLY"] == "present"


def test_env_int_uses_default_for_blank_and_rejects_text(monkeypatch) -> None:
    monkeypatch.delenv("LONGFORM_TEST_INT", raising=False)
    assert env_int("LONGFORM_TEST_INT", 4) == 4
    monkeypatch.setenv("LONGFORM_TEST_INT", "0")
    assert env_int("LONGFORM_TEST_INT", 4) == 0
    monkeypatch.setenv("LONGFORM_TEST_INT", "   ")
    assert env_int("LONGFORM_TEST_INT", 4) == 4
    monkeypatch.setenv("LONGFORM_TEST_INT", "nope")
    with pytest.raises(LongformError, match="integer"):
        env_int("LONGFORM_TEST_INT", 4)


def test_env_float_rejects_non_finite_values(monkeypatch) -> None:
    monkeypatch.setenv("LONGFORM_TEST_FLOAT", "1.5")
    assert env_float("LONGFORM_TEST_FLOAT", 0.0) == 1.5
    monkeypatch.setenv("LONGFORM_TEST_FLOAT", "nan")
    with pytest.raises(LongformError, match="finite"):
        env_float("LONGFORM_TEST_FLOAT", 0.0)
    monkeypatch.setenv("LONGFORM_TEST_FLOAT", "inf")
    with pytest.raises(LongformError, match="finite"):
        env_float("LONGFORM_TEST_FLOAT", 0.0)
    monkeypatch.setenv("LONGFORM_TEST_FLOAT", "")
    assert env_float("LONGFORM_TEST_FLOAT", 0.25) == 0.25


def test_read_and_write_json_round_trip_and_report_errors(tmp_path) -> None:
    target = tmp_path / "nested" / "payload.json"
    write_json(target, {"name": "demo", "count": 2})
    assert read_json(target) == {"name": "demo", "count": 2}
    assert target.read_text(encoding="utf-8").endswith("\n")

    with pytest.raises(LongformError, match="missing file"):
        read_json(tmp_path / "missing.json")
    (tmp_path / "bad.json").write_text("{", encoding="utf-8")
    with pytest.raises(LongformError, match="invalid JSON"):
        read_json(tmp_path / "bad.json")


def test_append_jsonl_keeps_one_object_per_line(tmp_path) -> None:
    path = tmp_path / "events.jsonl"
    append_jsonl(path, {"b": 1, "a": 2})
    append_jsonl(path, {"c": 3})
    lines = path.read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[0]) == {"a": 2, "b": 1}
    assert json.loads(lines[1]) == {"c": 3}


def test_parse_ffmpeg_duration() -> None:
    banner = "Input #0, mp3, from 'narration.mp3':\n  Duration: 01:02:03.25, start: 0.000000"
    assert parse_ffmpeg_duration(banner) == pytest.approx(3723.25)
    assert parse_ffmpeg_duration("Duration: N/A, bitrate: N/A") is None


def test_update_chapter_stage_records_terminal_states(tmp_path) -> None:
    status_path = tmp_path / "chapters" / "01" / "status.json"
    status_path.parent.mkdir(parents=True)
    status_path.write_text(json.dumps({"state": "pending", "stages": {}}), encoding="utf-8")

    update_chapter_stage(tmp_path, "01", "script", "running")
    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status["state"] == "pending"
    assert status["stages"]["script"] == "running"

    update_chapter_stage(tmp_path, "01", "script", "completed", characters=12)
    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status["state"] == "completed"
    assert status["details"]["script"]["characters"] == 12

    update_chapter_stage(tmp_path, "01", "shots", "running")
    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status["state"] == "completed"
    assert status["stages"]["shots"] == "running"

    update_chapter_stage(tmp_path, "01", "assets", "review-required", placeholders=1)
    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status["state"] == "review-required"
    assert status["details"]["assets"]["placeholders"] == 1

    update_chapter_stage(tmp_path, "01", "render", "failed")
    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status["state"] == "failed"
    assert status["stages"]["render"] == "failed"


def test_update_pipeline_stage_marks_completed(tmp_path) -> None:
    update_pipeline_stage(tmp_path, "corpus", "completed", files=2)
    payload = json.loads((tmp_path / "state" / "pipeline.json").read_text(encoding="utf-8"))
    assert payload["state"] == "completed"
    assert payload["stages"]["corpus"] == "completed"
    assert payload["details"]["corpus"]["files"] == 2
    assert "updated_at" in payload


def test_module_imports_without_touching_the_runtime() -> None:
    assert longform_common.LONGFORM_ROOT.name == "longform"
