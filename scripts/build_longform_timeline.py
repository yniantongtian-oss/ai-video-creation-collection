#!/usr/bin/env python3
"""Match rights-approved assets to chapter shots and build timed chapter timelines."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from longform_common import (
    LongformError,
    load_dotenv,
    load_project,
    probe_duration,
    read_json,
    update_chapter_stage,
    update_pipeline_stage,
    write_json,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_VALIDATOR = ROOT / "scripts" / "media_asset_manifest.py"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    values: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise LongformError(f"invalid JSONL at {path}:{number}: {exc}") from exc
        if isinstance(item, dict):
            values.append(item)
    return values


def lexical_terms(text: str) -> set[str]:
    lowered = text.lower()
    terms = {token for token in re.findall(r"[a-z0-9][a-z0-9_-]{1,}", lowered)}
    for sequence in re.findall(r"[\u4e00-\u9fff]{2,}", text):
        if len(sequence) <= 8:
            terms.add(sequence)
        for size in (2, 3):
            for index in range(max(0, len(sequence) - size + 1)):
                terms.add(sequence[index : index + size])
    return terms


def validate_manifest(project: Path) -> None:
    manifest = project / "manifests" / "assets.jsonl"
    if not MANIFEST_VALIDATOR.is_file():
        raise LongformError(f"missing manifest validator: {MANIFEST_VALIDATOR}")
    command = [
        sys.executable,
        str(MANIFEST_VALIDATOR),
        "validate",
        "--manifest",
        str(manifest),
    ]
    print("$ " + " ".join(command))
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        raise LongformError("asset rights validation failed")


def resolve_asset_path(project: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = project / path
    return path.resolve()


def load_assets(project: Path) -> list[dict[str, Any]]:
    manifest = project / "manifests" / "assets.jsonl"
    values: list[dict[str, Any]] = []
    for item in read_jsonl(manifest):
        if not bool(item.get("selected", False)):
            continue
        kind = str(item.get("kind") or "")
        if kind not in {"image", "video"}:
            continue
        local_path = resolve_asset_path(project, str(item.get("local_path") or ""))
        if not local_path.is_file():
            raise LongformError(
                f"selected asset file is missing: {item.get('id')} -> {local_path}"
            )
        searchable = " ".join(
            str(item.get(key) or "")
            for key in (
                "title",
                "notes",
                "attribution",
                "provider",
                "creator",
                "source_url",
            )
        )
        enriched = dict(item)
        enriched["resolved_path"] = str(local_path)
        enriched["terms"] = lexical_terms(searchable)
        values.append(enriched)
    return values


def desired_kinds(shot: dict[str, Any]) -> list[str]:
    visual_type = str(shot.get("visual_type") or "image").lower()
    if visual_type == "video":
        return ["video", "image"]
    if visual_type in {"image", "document", "diagram", "map", "timeline", "title-card"}:
        return ["image", "video"]
    return ["image", "video"]


def shot_terms(shot: dict[str, Any]) -> set[str]:
    values = [
        str(shot.get("visual_description") or ""),
        str(shot.get("narration_excerpt") or ""),
        str(shot.get("on_screen_text") or ""),
    ]
    queries = shot.get("search_queries")
    if isinstance(queries, list):
        values.extend(str(value) for value in queries)
    return lexical_terms(" ".join(values))


def asset_score(
    asset: dict[str, Any],
    shot: dict[str, Any],
    chapter_id: str,
    usage_count: int,
    last_asset_ids: list[str],
) -> float:
    terms = shot_terms(shot)
    overlap = terms & set(asset.get("terms", set()))
    score = sum(4.0 if len(term) >= 3 else 1.5 for term in overlap)
    kind = str(asset.get("kind") or "")
    desired = desired_kinds(shot)
    if kind == desired[0]:
        score += 5.0
    elif kind in desired:
        score += 1.5
    local_path = str(asset.get("local_path") or "").replace("\\", "/")
    if f"chapters/{chapter_id}/" in local_path:
        score += 4.0
    if str(asset.get("id") or "") in last_asset_ids:
        score -= 8.0
    score -= usage_count * 0.35
    return score


def choose_asset(
    assets: list[dict[str, Any]],
    shot: dict[str, Any],
    chapter_id: str,
    usage: dict[str, int],
    last_asset_ids: list[str],
) -> dict[str, Any] | None:
    if not assets:
        return None
    ranked = sorted(
        assets,
        key=lambda asset: asset_score(
            asset,
            shot,
            chapter_id,
            usage.get(str(asset.get("id") or ""), 0),
            last_asset_ids,
        ),
        reverse=True,
    )
    return ranked[0] if ranked else None


def scale_durations(shots: list[dict[str, Any]], total_seconds: float) -> list[float]:
    values = [max(1.0, float(shot.get("duration_seconds") or 1.0)) for shot in shots]
    current = sum(values) or 1.0
    scaled = [value * total_seconds / current for value in values]
    difference = total_seconds - sum(scaled)
    if scaled:
        scaled[-1] += difference
    return scaled


def build_chapter_timeline(
    project: Path,
    chapter_id: str,
    assets: list[dict[str, Any]],
    *,
    allow_placeholders: bool,
    max_consecutive_reuse: int,
    minimum_assets: int,
) -> dict[str, Any]:
    chapter = project / "chapters" / chapter_id
    shots_path = chapter / "shots.json"
    shots = read_json(shots_path)
    if not isinstance(shots, list) or not shots:
        raise LongformError(f"chapter {chapter_id} has no shot plan")
    audio = chapter / "audio" / "narration.mp3"
    if not audio.is_file():
        raise LongformError(
            f"chapter {chapter_id} has no narration audio; run render_longform_narration.py"
        )
    total_seconds = probe_duration(audio)
    durations = scale_durations(shots, total_seconds)
    unique_assets = {str(item.get("id") or "") for item in assets}
    if len(unique_assets) < minimum_assets and not allow_placeholders:
        raise LongformError(
            f"not enough selected visual assets for chapter {chapter_id}: "
            f"required={minimum_assets}, available={len(unique_assets)}"
        )

    usage: dict[str, int] = defaultdict(int)
    recent: list[str] = []
    timeline: list[dict[str, Any]] = []
    cursor = 0.0
    missing = 0
    for index, shot in enumerate(shots):
        if not isinstance(shot, dict):
            continue
        asset = choose_asset(assets, shot, chapter_id, usage, recent)
        if asset is None:
            if not allow_placeholders:
                raise LongformError(
                    f"no rights-approved asset can be assigned to shot {shot.get('id')}"
                )
            missing += 1
            asset_id = "placeholder"
            local_path = ""
            kind = "placeholder"
        else:
            asset_id = str(asset.get("id") or "")
            local_path = str(asset.get("resolved_path") or "")
            kind = str(asset.get("kind") or "image")
            usage[asset_id] += 1
            recent.append(asset_id)
            recent = recent[-max_consecutive_reuse:]
        duration = float(durations[index])
        entry = {
            "id": str(shot.get("id") or f"{chapter_id}-{index + 1:03d}"),
            "chapter": chapter_id,
            "start_seconds": round(cursor, 3),
            "duration_seconds": round(duration, 3),
            "end_seconds": round(cursor + duration, 3),
            "asset_id": asset_id,
            "asset_path": local_path,
            "kind": kind,
            "visual_type": shot.get("visual_type", kind),
            "visual_description": shot.get("visual_description", ""),
            "on_screen_text": shot.get("on_screen_text", ""),
            "narration_excerpt": shot.get("narration_excerpt", ""),
            "source_refs": shot.get("source_refs", []),
            "fit": "cover",
            "motion": "slow-zoom" if kind == "image" else "source-motion",
        }
        timeline.append(entry)
        shot["asset_id"] = asset_id
        shot["asset_path"] = local_path
        shot["status"] = "assigned" if asset is not None else "placeholder"
        cursor += duration
    write_json(chapter / "timeline.json", timeline)
    write_json(shots_path, shots)
    update_chapter_stage(
        project,
        chapter_id,
        "assets",
        "completed" if not missing else "review-required",
        timeline_entries=len(timeline),
        placeholders=missing,
        selected_assets=len(unique_assets),
        duration_seconds=round(total_seconds, 3),
    )
    return {
        "chapter": chapter_id,
        "timeline_entries": len(timeline),
        "placeholders": missing,
        "duration_seconds": total_seconds,
    }


def parse_args() -> argparse.Namespace:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--chapter", action="append")
    parser.add_argument("--allow-placeholders", action="store_true")
    parser.add_argument("--minimum-assets", type=int)
    parser.add_argument("--max-consecutive-reuse", type=int)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project, project_data = load_project(args.project)
    validate_manifest(project)
    assets = load_assets(project)
    available = [str(item.get("id")) for item in project_data.get("chapters", [])]
    chapter_ids = (
        [f"{int(value):02d}" for value in args.chapter] if args.chapter else available
    )
    missing_ids = [value for value in chapter_ids if value not in available]
    if missing_ids:
        raise LongformError(f"unknown chapters: {', '.join(missing_ids)}")
    gates = project_data.get("quality_gates", {})
    minimum_assets = args.minimum_assets or int(
        gates.get("minimum_selected_assets_per_chapter", 8)
    )
    max_reuse = args.max_consecutive_reuse or int(
        gates.get("max_consecutive_asset_reuse", 2)
    )
    if minimum_assets < 1 or max_reuse < 1:
        raise LongformError("minimum assets and reuse values must be positive")

    update_pipeline_stage(project, "rights_review", "completed", selected_assets=len(assets))
    results: list[dict[str, Any]] = []
    try:
        for chapter_id in chapter_ids:
            result = build_chapter_timeline(
                project,
                chapter_id,
                assets,
                allow_placeholders=args.allow_placeholders,
                max_consecutive_reuse=max_reuse,
                minimum_assets=minimum_assets,
            )
            results.append(result)
            print(
                f"Timeline ready: chapter={chapter_id}, "
                f"entries={result['timeline_entries']}, placeholders={result['placeholders']}"
            )
    except Exception:
        update_pipeline_stage(project, "rights_review", "failed")
        raise
    update_pipeline_stage(
        project,
        "rights_review",
        "completed",
        chapters=chapter_ids,
        selected_assets=len(assets),
        placeholders=sum(int(item["placeholders"]) for item in results),
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (LongformError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
