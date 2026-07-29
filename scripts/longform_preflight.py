#!/usr/bin/env python3
"""Check long-form runtime, project completeness, storage, rights, and stage readiness."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from longform_common import (
    LONGFORM_ENV,
    LongformError,
    get_ffmpeg,
    load_dotenv,
    load_project,
    probe_duration,
    runtime_executable,
    runtime_python,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_VALIDATOR = ROOT / "scripts" / "media_asset_manifest.py"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    values: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip():
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                values.append(value)
    return values


def bitrate_bps(value: str, default: int) -> int:
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([kKmM]?)\s*", value)
    if not match:
        return default
    number = float(match.group(1))
    suffix = match.group(2).lower()
    multiplier = 1_000_000 if suffix == "m" else 1_000 if suffix == "k" else 1
    return int(number * multiplier)


def add_check(
    checks: list[dict[str, Any]],
    name: str,
    passed: bool,
    severity: str,
    detail: str,
) -> None:
    checks.append(
        {
            "name": name,
            "passed": passed,
            "severity": severity,
            "detail": detail,
        }
    )


def validate_rights(project: Path) -> tuple[bool, str]:
    manifest = project / "manifests" / "assets.jsonl"
    if not manifest.is_file():
        return False, "assets manifest is missing"
    result = subprocess.run(
        [
            sys.executable,
            str(MANIFEST_VALIDATOR),
            "validate",
            "--manifest",
            str(manifest),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        check=False,
    )
    detail = "\n".join((result.stdout or "").splitlines()[-10:])
    return result.returncode == 0, detail or f"exit code {result.returncode}"


def project_metrics(project: Path, data: dict[str, Any]) -> dict[str, Any]:
    chapters = data.get("chapters", [])
    scripts = 0
    script_chars = 0
    shot_count = 0
    timeline_entries = 0
    placeholders = 0
    narration_chapters = 0
    narration_seconds = 0.0
    rendered_chapters = 0
    rendered_seconds = 0.0
    for chapter in chapters:
        chapter_id = str(chapter.get("id"))
        chapter_dir = project / "chapters" / chapter_id
        narration_text = chapter_dir / "narration.txt"
        if narration_text.is_file():
            text = narration_text.read_text(encoding="utf-8", errors="replace").strip()
            if text:
                scripts += 1
                script_chars += len(text)
        shots_path = chapter_dir / "shots.json"
        if shots_path.is_file():
            try:
                shots = json.loads(shots_path.read_text(encoding="utf-8"))
                if isinstance(shots, list):
                    shot_count += len(shots)
            except json.JSONDecodeError:
                pass
        timeline_path = chapter_dir / "timeline.json"
        if timeline_path.is_file():
            try:
                timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
                if isinstance(timeline, list):
                    timeline_entries += len(timeline)
                    placeholders += sum(
                        1
                        for item in timeline
                        if isinstance(item, dict)
                        and str(item.get("kind") or "") == "placeholder"
                    )
            except json.JSONDecodeError:
                pass
        audio = chapter_dir / "audio" / "narration.mp3"
        if audio.is_file() and audio.stat().st_size > 0:
            narration_chapters += 1
            try:
                narration_seconds += probe_duration(audio)
            except LongformError:
                pass
        rendered = project / "outputs" / "chapters" / f"chapter-{chapter_id}.mp4"
        if rendered.is_file() and rendered.stat().st_size > 0:
            rendered_chapters += 1
            try:
                rendered_seconds += probe_duration(rendered)
            except LongformError:
                pass
    assets = read_jsonl(project / "manifests" / "assets.jsonl")
    selected = [item for item in assets if bool(item.get("selected", False))]
    source_count = len(read_jsonl(project / "research" / "sources.jsonl"))
    chunk_count = len(read_jsonl(project / "research" / "chunks.jsonl"))
    summary_count = len(list((project / "research" / "summaries").glob("*.md")))
    outline_path = project / "outline" / "outline.json"
    outline_chapters = 0
    if outline_path.is_file():
        try:
            outline = json.loads(outline_path.read_text(encoding="utf-8"))
            if isinstance(outline, dict) and isinstance(outline.get("chapters"), list):
                outline_chapters = len(outline["chapters"])
        except json.JSONDecodeError:
            pass
    return {
        "chapters": len(chapters),
        "research_sources": source_count,
        "research_chunks": chunk_count,
        "source_summaries": summary_count,
        "outline_chapters": outline_chapters,
        "scripted_chapters": scripts,
        "script_characters": script_chars,
        "shots": shot_count,
        "selected_assets": len(selected),
        "timeline_entries": timeline_entries,
        "placeholders": placeholders,
        "narration_chapters": narration_chapters,
        "narration_seconds": round(narration_seconds, 3),
        "rendered_chapters": rendered_chapters,
        "rendered_seconds": round(rendered_seconds, 3),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument(
        "--stage",
        choices=["setup", "research", "writing", "assets", "narration", "render", "final"],
        default="setup",
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_dotenv()
    project, data = load_project(args.project)
    checks: list[dict[str, Any]] = []
    target = data.get("target", {})
    video = data.get("video", {})
    metrics = project_metrics(project, data)

    add_check(
        checks,
        "longform-runtime",
        runtime_python().is_file(),
        "error",
        str(runtime_python()),
    )
    edge_tts = runtime_executable("edge-tts")
    add_check(checks, "edge-tts", edge_tts.is_file(), "error", str(edge_tts))
    try:
        ffmpeg = get_ffmpeg()
        add_check(checks, "ffmpeg", True, "error", str(ffmpeg))
    except LongformError as exc:
        add_check(checks, "ffmpeg", False, "error", str(exc))

    llm_ready = all(
        os.environ.get(name, "").strip()
        for name in (
            "LONGFORM_LLM_BASE_URL",
            "LONGFORM_LLM_API_KEY",
            "LONGFORM_LLM_MODEL",
        )
    )
    add_check(
        checks,
        "llm-configuration",
        llm_ready,
        "error" if args.stage in {"research", "writing"} else "warning",
        f"configure {LONGFORM_ENV}",
    )

    minutes = int(target.get("minutes", 90))
    video_bps = bitrate_bps(str(video.get("video_bitrate", "8000k")), 8_000_000)
    audio_bps = bitrate_bps(str(video.get("audio_bitrate", "192k")), 192_000)
    final_bytes = int(minutes * 60 * (video_bps + audio_bps) / 8)
    selected_asset_bytes = 0
    for item in read_jsonl(project / "manifests" / "assets.jsonl"):
        if bool(item.get("selected", False)):
            try:
                selected_asset_bytes += int(item.get("size_bytes") or 0)
            except (TypeError, ValueError):
                pass
    recommended_working_bytes = int(final_bytes * 4.5 + selected_asset_bytes + 5 * 1024**3)
    free_bytes = shutil.disk_usage(project).free
    add_check(
        checks,
        "free-disk-space",
        free_bytes >= recommended_working_bytes,
        "error" if args.stage in {"render", "final"} else "warning",
        f"free={free_bytes / 1024**3:.1f} GiB, recommended={recommended_working_bytes / 1024**3:.1f} GiB, estimated final={final_bytes / 1024**3:.1f} GiB",
    )

    chapter_count = int(target.get("chapters", metrics["chapters"]))
    target_chars = int(target.get("script_chars", minutes * 260))
    add_check(
        checks,
        "research-corpus",
        metrics["research_sources"] > 0 and metrics["research_chunks"] > 0,
        "error" if args.stage in {"research", "writing", "assets", "narration", "render", "final"} else "warning",
        f"sources={metrics['research_sources']}, chunks={metrics['research_chunks']}",
    )
    add_check(
        checks,
        "source-summaries",
        metrics["source_summaries"] >= metrics["research_sources"] > 0,
        "error" if args.stage in {"writing", "assets", "narration", "render", "final"} else "warning",
        f"summaries={metrics['source_summaries']}, sources={metrics['research_sources']}",
    )
    add_check(
        checks,
        "outline",
        metrics["outline_chapters"] == chapter_count,
        "error" if args.stage in {"writing", "assets", "narration", "render", "final"} else "warning",
        f"outline chapters={metrics['outline_chapters']}, target={chapter_count}",
    )
    add_check(
        checks,
        "chapter-scripts",
        metrics["scripted_chapters"] == chapter_count
        and metrics["script_characters"] >= int(target_chars * 0.6),
        "error" if args.stage in {"assets", "narration", "render", "final"} else "warning",
        f"scripted={metrics['scripted_chapters']}/{chapter_count}, chars={metrics['script_characters']}/{target_chars}",
    )
    add_check(
        checks,
        "shot-plans",
        metrics["shots"] > 0,
        "error" if args.stage in {"assets", "narration", "render", "final"} else "warning",
        f"shots={metrics['shots']}",
    )

    rights_ok, rights_detail = validate_rights(project)
    add_check(
        checks,
        "asset-rights",
        rights_ok,
        "error" if args.stage in {"assets", "render", "final"} else "warning",
        rights_detail,
    )
    add_check(
        checks,
        "selected-assets",
        metrics["selected_assets"] > 0,
        "error" if args.stage in {"assets", "render", "final"} else "warning",
        f"selected={metrics['selected_assets']}",
    )
    add_check(
        checks,
        "timeline-placeholders",
        metrics["placeholders"] == 0,
        "error" if args.stage in {"render", "final"} else "warning",
        f"timeline entries={metrics['timeline_entries']}, placeholders={metrics['placeholders']}",
    )
    add_check(
        checks,
        "narration",
        metrics["narration_chapters"] == chapter_count,
        "error" if args.stage in {"render", "final"} else "warning",
        f"narration={metrics['narration_chapters']}/{chapter_count}, duration={metrics['narration_seconds'] / 60:.1f} min",
    )
    add_check(
        checks,
        "rendered-chapters",
        metrics["rendered_chapters"] == chapter_count,
        "error" if args.stage == "final" else "warning",
        f"rendered={metrics['rendered_chapters']}/{chapter_count}, duration={metrics['rendered_seconds'] / 60:.1f} min",
    )

    blocking = [
        item for item in checks if not item["passed"] and item["severity"] == "error"
    ]
    payload = {
        "project": str(project),
        "stage": args.stage,
        "ready": not blocking,
        "metrics": metrics,
        "estimates": {
            "final_size_gib": round(final_bytes / 1024**3, 2),
            "recommended_working_space_gib": round(recommended_working_bytes / 1024**3, 2),
            "free_space_gib": round(free_bytes / 1024**3, 2),
        },
        "checks": checks,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Long-form preflight: stage={args.stage}, ready={not blocking}")
        for item in checks:
            marker = "OK" if item["passed"] else ("ERROR" if item["severity"] == "error" else "WARN")
            print(f"[{marker:5s}] {item['name']}: {item['detail']}")
        print(
            "Estimated final size: "
            f"{payload['estimates']['final_size_gib']} GiB; recommended working space: "
            f"{payload['estimates']['recommended_working_space_gib']} GiB"
        )
    return 0 if not blocking else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (LongformError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
