"""Unit tests for pure timeline helpers."""

from __future__ import annotations

import json

import pytest

from build_longform_timeline import (
    build_chapter_timeline,
    choose_asset,
    desired_kinds,
    lexical_terms,
    read_jsonl,
    scale_durations,
)
from longform_common import LongformError


def test_lexical_terms_split_compounds_and_keep_cjk_ngrams() -> None:
    assert {"solar", "power"} <= lexical_terms("solar-power")
    assert lexical_terms("solar-power") & lexical_terms("solar power") >= {"solar", "power"}
    assert "a" not in lexical_terms("a b")
    assert "太阳能" in lexical_terms("太阳能")
    assert "太阳" in lexical_terms("太阳能")
    long_sequence = "一二三四五六七八九"
    terms = lexical_terms(long_sequence)
    assert long_sequence not in terms
    assert "一二" in terms
    assert "一二三" in terms
    assert "一二三四五六七八" in lexical_terms("一二三四五六七八")


def test_desired_kinds_prefer_the_requested_visual() -> None:
    assert desired_kinds({"visual_type": "VIDEO"}) == ["video", "image"]
    assert desired_kinds({"visual_type": "map"}) == ["image", "video"]
    assert desired_kinds({}) == ["image", "video"]
    assert desired_kinds({"visual_type": "mystery"}) == ["image", "video"]


def test_scale_durations_preserves_subsecond_ratios() -> None:
    scaled = scale_durations(
        [{"duration_seconds": 0.5}, {"duration_seconds": 1.5}],
        10,
    )
    assert scaled[0] == pytest.approx(2.5)
    assert scaled[1] == pytest.approx(7.5)
    assert sum(scaled) == pytest.approx(10)

    equal = scale_durations(
        [{"duration_seconds": 1}, {"duration_seconds": 1}, {"duration_seconds": 1}],
        10,
    )
    assert sum(equal) == pytest.approx(10)

    missing = scale_durations([{}, {"duration_seconds": ""}], 4)
    assert missing == pytest.approx([2, 2])


def test_scale_durations_rejects_bad_totals_and_values() -> None:
    with pytest.raises(LongformError, match="positive"):
        scale_durations([{}], 0)
    with pytest.raises(LongformError, match="number"):
        scale_durations([{"duration_seconds": "soon"}], 5)
    with pytest.raises(LongformError, match="finite"):
        scale_durations([{"duration_seconds": float("inf")}], 5)
    with pytest.raises(LongformError, match="number"):
        scale_durations([{"duration_seconds": True}], 5)


def test_choose_asset_prefers_kind_terms_and_penalizes_recent_reuse() -> None:
    solar = {
        "id": "solar",
        "kind": "image",
        "local_path": "global/solar.jpg",
        "terms": lexical_terms("solar-power farm"),
    }
    other = {
        "id": "other",
        "kind": "image",
        "local_path": "global/other.jpg",
        "terms": lexical_terms("unrelated object"),
    }
    shot = {"visual_type": "image", "visual_description": "solar power"}
    assert choose_asset([other, solar], shot, "01", {}, [])["id"] == "solar"

    image = {
        "id": "img",
        "kind": "image",
        "local_path": "global/harbor.jpg",
        "terms": lexical_terms("harbor"),
    }
    video = {
        "id": "vid",
        "kind": "video",
        "local_path": "global/harbor.mp4",
        "terms": lexical_terms("harbor"),
    }
    video_shot = {"visual_type": "video", "visual_description": "harbor"}
    assert choose_asset([image, video], video_shot, "02", {}, [])["id"] == "vid"

    panel = {"visual_type": "image", "visual_description": "solar panel", "search_queries": ["panel"]}
    panel_asset = {
        "id": "solar",
        "kind": "image",
        "local_path": "global/a.jpg",
        "terms": lexical_terms("solar panel"),
    }
    battery = {
        "id": "battery",
        "kind": "image",
        "local_path": "global/b.jpg",
        "terms": lexical_terms("battery cell"),
    }
    assert choose_asset([battery, panel_asset], panel, "01", {}, [])["id"] == "solar"
    assert choose_asset([battery, panel_asset], panel, "01", {}, ["solar"])["id"] == "battery"
    assert choose_asset([], panel, "01", {}, []) is None


def test_read_jsonl_skips_blanks_and_rejects_non_objects(tmp_path) -> None:
    path = tmp_path / "items.jsonl"
    path.write_text('{"id": "a"}\n\n{"id": "b"}\n', encoding="utf-8")
    assert [item["id"] for item in read_jsonl(path)] == ["a", "b"]

    path.write_text('{"id": "a"}\n[1]\n', encoding="utf-8")
    with pytest.raises(LongformError, match="must be an object"):
        read_jsonl(path)

    path.write_text("{}\n{", encoding="utf-8")
    with pytest.raises(LongformError, match="invalid JSONL"):
        read_jsonl(path)
    assert read_jsonl(tmp_path / "missing.jsonl") == []


def _chapter(tmp_path, shots):
    project = tmp_path / "demo"
    chapter = project / "chapters" / "01"
    (chapter / "audio").mkdir(parents=True)
    (chapter / "audio" / "narration.mp3").write_bytes(b"not-audio")
    (chapter / "shots.json").write_text(json.dumps(shots), encoding="utf-8")
    return project


def test_build_chapter_timeline_ignores_non_dict_shots_and_matches_audio(tmp_path, monkeypatch) -> None:
    shots = [
        {"id": "a", "duration_seconds": 1, "visual_type": "image", "visual_description": "solar"},
        "not-a-shot",
        {"id": "b", "duration_seconds": 3, "visual_type": "image", "visual_description": "solar"},
    ]
    project = _chapter(tmp_path, shots)
    monkeypatch.setattr("build_longform_timeline.probe_duration", lambda media: 8.0)

    result = build_chapter_timeline(
        project,
        "01",
        [],
        allow_placeholders=True,
        max_consecutive_reuse=2,
        minimum_assets=1,
    )

    timeline = json.loads((project / "chapters" / "01" / "timeline.json").read_text(encoding="utf-8"))
    assert result["placeholders"] == 2
    assert [item["id"] for item in timeline] == ["a", "b"]
    assert [item["duration_seconds"] for item in timeline] == pytest.approx([2, 6])
    assert timeline[-1]["end_seconds"] == pytest.approx(8)
    status = json.loads((project / "chapters" / "01" / "status.json").read_text(encoding="utf-8"))
    assert status["state"] == "review-required"
    assert status["stages"]["assets"] == "review-required"


def test_build_chapter_timeline_requires_enough_selected_assets(tmp_path, monkeypatch) -> None:
    project = _chapter(
        tmp_path,
        [{"id": "a", "duration_seconds": 2, "visual_type": "image", "visual_description": "solar"}],
    )
    monkeypatch.setattr("build_longform_timeline.probe_duration", lambda media: 4.0)
    assets = [
        {
            "id": "only",
            "kind": "image",
            "local_path": "global/only.jpg",
            "resolved_path": "global/only.jpg",
            "terms": lexical_terms("solar"),
        }
    ]
    with pytest.raises(LongformError, match="not enough selected"):
        build_chapter_timeline(
            project,
            "01",
            assets,
            allow_placeholders=False,
            max_consecutive_reuse=2,
            minimum_assets=2,
        )
