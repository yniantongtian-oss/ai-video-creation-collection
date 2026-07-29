#!/usr/bin/env python3
"""Concatenate rendered chapters, merge subtitles, and write chapter metadata."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from longform_common import (
    LongformError,
    get_ffmpeg,
    load_project,
    probe_duration,
    run_command,
    update_pipeline_stage,
    write_json,
)

TIME_PATTERN = re.compile(
    r"(?P<start>\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(?P<end>\d{2}:\d{2}:\d{2},\d{3})"
)


def safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff._-]+", "-", value).strip(".-")
    return value[:100] or "longform-video"


def concat_path(path: Path) -> str:
    return str(path.resolve()).replace("'", "'\\''")


def parse_time(value: str) -> float:
    hours, minutes, rest = value.split(":")
    seconds, milliseconds = rest.split(",")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000


def format_srt_time(value: float) -> str:
    milliseconds_total = max(0, int(round(value * 1000)))
    hours, remainder = divmod(milliseconds_total, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def format_chapter_time(value: float) -> str:
    seconds_total = max(0, int(round(value)))
    hours, remainder = divmod(seconds_total, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def parse_srt(path: Path) -> list[tuple[float, float, str]]:
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8-sig", errors="replace").strip()
    cues: list[tuple[float, float, str]] = []
    for block in re.split(r"\n\s*\n", text):
        lines = [line.strip("\ufeff") for line in block.splitlines() if line.strip()]
        timing_index = next((index for index, line in enumerate(lines) if "-->" in line), -1)
        if timing_index < 0:
            continue
        match = TIME_PATTERN.search(lines[timing_index])
        if not match:
            continue
        caption = "\n".join(lines[timing_index + 1 :]).strip()
        if caption:
            cues.append(
                (parse_time(match.group("start")), parse_time(match.group("end")), caption)
            )
    return cues


def write_srt(path: Path, cues: list[tuple[float, float, str]]) -> None:
    blocks = [
        f"{index}\n{format_srt_time(start)} --> {format_srt_time(end)}\n{caption}"
        for index, (start, end, caption) in enumerate(cues, 1)
    ]
    path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")


def selected_chapters(project: Path, project_data: dict[str, Any]) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for chapter in project_data.get("chapters", []):
        chapter_id = str(chapter.get("id"))
        video = project / "outputs" / "chapters" / f"chapter-{chapter_id}.mp4"
        subtitle = project / "outputs" / "chapters" / f"chapter-{chapter_id}.srt"
        if not video.is_file() or video.stat().st_size == 0:
            raise LongformError(f"rendered chapter is missing: {video}")
        duration = probe_duration(video)
        values.append(
            {
                "id": chapter_id,
                "title": str(chapter.get("title") or f"第 {int(chapter_id)} 章"),
                "video": video,
                "subtitle": subtitle,
                "duration_seconds": duration,
            }
        )
    if not values:
        raise LongformError("project has no rendered chapters")
    return values


def concatenate(
    chapters: list[dict[str, Any]],
    intermediate: Path,
    *,
    encoder: str,
    preset: str,
    video_bitrate: str,
    audio_bitrate: str,
    force_reencode: bool,
    log_dir: Path,
) -> str:
    ffmpeg = get_ffmpeg()
    concat_file = intermediate.with_suffix(".txt")
    concat_file.write_text(
        "\n".join(f"file '{concat_path(item['video'])}'" for item in chapters) + "\n",
        encoding="utf-8",
    )
    copy_command = [
        str(ffmpeg),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        str(intermediate),
    ]
    if not force_reencode:
        try:
            run_command(copy_command, log_path=log_dir / "assembly-stream-copy.log")
            return "stream-copy"
        except LongformError as exc:
            print(f"Stream-copy assembly failed; falling back to re-encode: {exc}", file=sys.stderr)
    reencode_command = [
        str(ffmpeg),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-c:v",
        encoder,
        "-preset",
        preset,
        "-b:v",
        video_bitrate,
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        audio_bitrate,
        "-movflags",
        "+faststart",
        str(intermediate),
    ]
    run_command(reencode_command, log_path=log_dir / "assembly-reencode.log")
    return "reencode"


def write_chapter_files(
    project: Path, chapters: list[dict[str, Any]]
) -> tuple[Path, Path, list[dict[str, Any]]]:
    metadata = project / "outputs" / "final" / "chapters.ffmetadata"
    youtube = project / "outputs" / "final" / "youtube-chapters.txt"
    lines = [";FFMETADATA1"]
    youtube_lines: list[str] = []
    entries: list[dict[str, Any]] = []
    cursor = 0.0
    for item in chapters:
        start = cursor
        end = cursor + float(item["duration_seconds"])
        title = str(item["title"]).replace("=", "-").replace(";", "-")
        lines.extend(
            [
                "[CHAPTER]",
                "TIMEBASE=1/1000",
                f"START={int(round(start * 1000))}",
                f"END={int(round(end * 1000))}",
                f"title={title}",
            ]
        )
        youtube_lines.append(f"{format_chapter_time(start)} {title}")
        entries.append(
            {
                "id": item["id"],
                "title": title,
                "start_seconds": round(start, 3),
                "end_seconds": round(end, 3),
                "duration_seconds": round(float(item["duration_seconds"]), 3),
            }
        )
        cursor = end
    metadata.write_text("\n".join(lines) + "\n", encoding="utf-8")
    youtube.write_text("\n".join(youtube_lines) + "\n", encoding="utf-8")
    return metadata, youtube, entries


def merge_subtitles(project: Path, chapters: list[dict[str, Any]]) -> Path:
    output = project / "outputs" / "final" / "full.srt"
    cues: list[tuple[float, float, str]] = []
    offset = 0.0
    for item in chapters:
        for start, end, caption in parse_srt(Path(item["subtitle"])):
            cues.append((start + offset, end + offset, caption))
        offset += float(item["duration_seconds"])
    write_srt(output, cues)
    return output


def embed_metadata(intermediate: Path, metadata: Path, output: Path, log_path: Path) -> None:
    ffmpeg = get_ffmpeg()
    run_command(
        [
            str(ffmpeg),
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(intermediate),
            "-f",
            "ffmetadata",
            "-i",
            str(metadata),
            "-map_metadata",
            "1",
            "-map_chapters",
            "1",
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(output),
        ],
        log_path=log_path,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--output-name")
    parser.add_argument("--encoder", default="libx264")
    parser.add_argument("--preset", default="medium")
    parser.add_argument("--video-bitrate", default="8000k")
    parser.add_argument("--audio-bitrate", default="192k")
    parser.add_argument("--force-reencode", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project, project_data = load_project(args.project)
    final_dir = project / "outputs" / "final"
    final_dir.mkdir(parents=True, exist_ok=True)
    name = safe_name(args.output_name or str(project_data.get("name") or "longform-video"))
    output = final_dir / f"{name}.mp4"
    if output.is_file() and output.stat().st_size > 0 and not args.force:
        duration = probe_duration(output)
        print(f"Final video exists: {output} ({duration / 60:.1f} min)")
        return 0

    chapters = selected_chapters(project, project_data)
    update_pipeline_stage(project, "assembly", "running", chapters=len(chapters))
    try:
        metadata, youtube, chapter_entries = write_chapter_files(project, chapters)
        full_srt = merge_subtitles(project, chapters)
        intermediate = final_dir / ".assembled-without-metadata.mp4"
        mode = concatenate(
            chapters,
            intermediate,
            encoder=args.encoder,
            preset=args.preset,
            video_bitrate=args.video_bitrate,
            audio_bitrate=args.audio_bitrate,
            force_reencode=args.force_reencode,
            log_dir=project / "logs",
        )
        embed_metadata(
            intermediate,
            metadata,
            output,
            project / "logs" / "assembly-metadata.log",
        )
        if intermediate.exists():
            intermediate.unlink()
        duration = probe_duration(output)
        expected = sum(float(item["duration_seconds"]) for item in chapters)
        difference = abs(duration - expected)
        report = {
            "schema_version": "1.0.0",
            "assembled_at": datetime.now(timezone.utc).isoformat(),
            "output": str(output.relative_to(project)),
            "file_size_bytes": output.stat().st_size,
            "duration_seconds": round(duration, 3),
            "expected_duration_seconds": round(expected, 3),
            "duration_difference_seconds": round(difference, 3),
            "assembly_mode": mode,
            "chapters": chapter_entries,
            "subtitles": str(full_srt.relative_to(project)),
            "youtube_chapters": str(youtube.relative_to(project)),
            "metadata": str(metadata.relative_to(project)),
            "passed_duration_check": difference <= max(3.0, len(chapters) * 0.25),
        }
        write_json(final_dir / "assembly-report.json", report)
        if not report["passed_duration_check"]:
            raise LongformError(
                f"final duration differs from chapter total by {difference:.2f}s"
            )
    except Exception:
        update_pipeline_stage(project, "assembly", "failed")
        raise
    update_pipeline_stage(
        project,
        "assembly",
        "completed",
        output=str(output.relative_to(project)),
        duration_seconds=round(duration, 3),
        chapters=len(chapters),
        assembly_mode=mode,
    )
    print(f"Final video: {output}")
    print(f"Duration: {duration / 60:.1f} min")
    print(f"Full subtitles: {full_srt}")
    print(f"YouTube chapters: {youtube}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (LongformError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
