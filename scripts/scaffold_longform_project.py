#!/usr/bin/env python3
"""Create a resumable 60-180 minute research-to-video project workspace."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "projects"


class ScaffoldError(RuntimeError):
    pass


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|\x00-\x1f]+", "-", value).strip(" .-")
    return cleaned[:100] or "longform-project"


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: object) -> None:
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="Project directory and display name.")
    parser.add_argument("--topic", required=True, help="Long-form video topic.")
    parser.add_argument("--duration", type=int, default=90, help="Target minutes (default: 90).")
    parser.add_argument(
        "--chapter-minutes",
        type=int,
        default=7,
        help="Target minutes per chapter (default: 7).",
    )
    parser.add_argument("--aspect-ratio", choices=["16:9", "9:16", "1:1"], default="16:9")
    parser.add_argument("--language", default="en-US")
    parser.add_argument("--audience", default="General audience")
    parser.add_argument("--style", default="Documentary explainer with high information density and natural narration")
    parser.add_argument("--chars-per-minute", type=int, default=260)
    parser.add_argument("--visual-seconds", type=int, default=10)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if not 30 <= args.duration <= 360:
        parser.error("--duration must be between 30 and 360 minutes")
    if not 3 <= args.chapter_minutes <= 20:
        parser.error("--chapter-minutes must be between 3 and 20")
    if not 120 <= args.chars_per_minute <= 500:
        parser.error("--chars-per-minute must be between 120 and 500")
    if not 4 <= args.visual_seconds <= 30:
        parser.error("--visual-seconds must be between 4 and 30")
    return args


def aspect_dimensions(aspect: str) -> tuple[int, int]:
    return {
        "16:9": (1920, 1080),
        "9:16": (1080, 1920),
        "1:1": (1080, 1080),
    }[aspect]


def make_chapters(project: Path, count: int, duration: int) -> list[dict[str, object]]:
    chapters: list[dict[str, object]] = []
    base = duration // count
    remainder = duration % count
    for index in range(1, count + 1):
        minutes = base + (1 if index <= remainder else 0)
        chapter_id = f"{index:02d}"
        chapter_dir = project / "chapters" / chapter_id
        for relative in (
            "research",
            "assets/images",
            "assets/videos",
            "assets/audio",
            "audio/segments",
            "subtitles",
            "render/shots",
            "render/intermediate",
        ):
            (chapter_dir / relative).mkdir(parents=True, exist_ok=True)
        write_text(
            chapter_dir / "brief.md",
            f"# Chapter {index}\n\n"
            "## Chapter goal\n\nTo be generated.\n\n"
            "## Questions this chapter must answer\n\n- To be generated\n\n"
            "## Primary sources\n\n- To be retrieved\n",
        )
        write_text(chapter_dir / "script.md", "")
        write_text(chapter_dir / "narration.txt", "")
        write_text(chapter_dir / "shots.json", "[]\n")
        write_text(chapter_dir / "timeline.json", "[]\n")
        write_json(
            chapter_dir / "status.json",
            {
                "chapter": index,
                "state": "pending",
                "stages": {
                    "research": "pending",
                    "script": "pending",
                    "shots": "pending",
                    "assets": "pending",
                    "narration": "pending",
                    "render": "pending",
                },
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        chapters.append(
            {
                "id": chapter_id,
                "number": index,
                "title": f"Chapter {index} (planning pending)",
                "target_minutes": minutes,
                "status": "pending",
            }
        )
    return chapters


def main() -> int:
    args = parse_args()
    project = args.output.expanduser().resolve() / safe_name(args.name)
    if project.exists() and any(project.iterdir()) and not args.force:
        raise ScaffoldError(f"project already exists and is not empty: {project}")
    project.mkdir(parents=True, exist_ok=True)

    for relative in (
        "research/inbox",
        "research/extracted",
        "research/summaries",
        "research/search-results",
        "outline",
        "assets/global/images",
        "assets/global/videos",
        "assets/global/audio",
        "assets/search-results",
        "manifests",
        "chapters",
        "state",
        "logs",
        "outputs/chapters",
        "outputs/final",
        "outputs/review",
    ):
        (project / relative).mkdir(parents=True, exist_ok=True)

    chapter_count = math.ceil(args.duration / args.chapter_minutes)
    width, height = aspect_dimensions(args.aspect_ratio)
    target_chars = args.duration * args.chars_per_minute
    target_shots = math.ceil(args.duration * 60 / args.visual_seconds)
    chapters = make_chapters(project, chapter_count, args.duration)
    created_at = datetime.now(timezone.utc).isoformat()

    project_config = {
        "schema_version": "1.0.0",
        "name": args.name,
        "topic": args.topic,
        "audience": args.audience,
        "style": args.style,
        "language": args.language,
        "created_at": created_at,
        "target": {
            "minutes": args.duration,
            "chapters": chapter_count,
            "chapter_minutes": args.chapter_minutes,
            "chars_per_minute": args.chars_per_minute,
            "script_chars": target_chars,
            "visual_seconds_per_shot": args.visual_seconds,
            "shots": target_shots,
        },
        "video": {
            "aspect_ratio": args.aspect_ratio,
            "width": width,
            "height": height,
            "fps": 30,
            "video_bitrate": "8000k",
            "audio_bitrate": "192k",
            "codec": "libx264",
            "pixel_format": "yuv420p",
        },
        "narration": {
            "provider": "edge-tts",
            "voice": "en-US-JennyNeural",
            "rate": "+0%",
            "volume": "+0%",
            "max_chars_per_segment": 1800,
        },
        "quality_gates": {
            "require_source_markers": True,
            "require_asset_rights_validation": True,
            "allow_unknown_rights": False,
            "allow_placeholders_in_final": False,
            "max_consecutive_asset_reuse": 2,
            "minimum_selected_assets_per_chapter": 8,
        },
        "chapters": chapters,
    }
    write_json(project / "project.json", project_config)
    write_json(
        project / "state" / "pipeline.json",
        {
            "project": args.name,
            "state": "created",
            "stages": {
                "corpus": "pending",
                "summaries": "pending",
                "outline": "pending",
                "scripts": "pending",
                "shots": "pending",
                "asset_search": "pending",
                "rights_review": "pending",
                "narration": "pending",
                "chapter_render": "pending",
                "assembly": "pending",
                "quality_review": "pending",
            },
            "updated_at": created_at,
        },
    )
    write_json(project / "outline" / "outline.json", {"chapters": []})
    write_text(project / "research" / "sources.jsonl", "")
    write_text(project / "research" / "chunks.jsonl", "")
    write_text(project / "manifests" / "assets.jsonl", "")
    write_text(project / "manifests" / "facts.jsonl", "")
    write_text(project / "manifests" / "render.jsonl", "")

    with (project / "outline" / "chapter-map.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "chapter",
                "title",
                "target_minutes",
                "target_chars",
                "target_shots",
                "status",
            ]
        )
        for chapter in chapters:
            minutes = int(chapter["target_minutes"])
            writer.writerow(
                [
                    chapter["id"],
                    chapter["title"],
                    minutes,
                    minutes * args.chars_per_minute,
                    math.ceil(minutes * 60 / args.visual_seconds),
                    chapter["status"],
                ]
            )

    brief = f"""# {args.name}

## Core topic

{args.topic}

## Audience

{args.audience}

## Style

{args.style}

## Target specification

- Duration: about {args.duration} minutes
- Chapters: {chapter_count}, about {args.chapter_minutes} minutes each
- Script target: about {target_chars:,} characters
- Visual segments: about {target_shots}, with a major visual change every {args.visual_seconds} seconds
- Aspect ratio: {args.aspect_ratio} ({width}×{height})
- Language: {args.language}

## Long-form production principles

1. Build the source library and chapter outline before drafting chapters.
2. Preserve source markers for factual claims; write `NEEDS_SOURCE` when evidence is insufficient.
3. Narrate, subtitle, and render chapters independently so a failed chapter can be rerun alone.
4. Automatically downloaded media is candidate-only until content, relevance, and rights are reviewed.
5. Before final assembly, verify chapter order, loudness, subtitles, factual claims, media rights, and total duration.
"""
    write_text(project / "brief.md", brief)
    write_text(
        project / "README.md",
        "# Project Workflow\n\n"
        "1. Put PDF, DOCX, PPTX, TXT, Markdown, subtitle, and other research files in `research/inbox/`.\n"
        "2. Run `ingest_longform_corpus.py` to build the searchable corpus.\n"
        "3. Run `longform_pipeline.py run` to create summaries, an outline, chapter scripts, and shot plans.\n"
        "4. Search for and review image, video, and audio assets.\n"
        "5. Run chapter narration and chapter rendering.\n"
        "6. Run final assembly and quality checks.\n",
    )

    print(f"Long-form project created: {project}")
    print(f"Chapters: {chapter_count}")
    print(f"Target script characters: {target_chars}")
    print(f"Target visual segments: {target_shots}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ScaffoldError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
