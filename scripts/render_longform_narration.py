#!/usr/bin/env python3
"""Generate resumable chapter narration and merged SRT subtitles with Edge TTS."""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

from longform_common import (
    LongformError,
    env_int,
    get_ffmpeg,
    load_dotenv,
    load_project,
    probe_duration,
    run_command,
    runtime_executable,
    update_chapter_stage,
    update_pipeline_stage,
)

TIME_PATTERN = re.compile(
    r"(?P<start>\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(?P<end>\d{2}:\d{2}:\d{2},\d{3})"
)


def parse_time(value: str) -> float:
    hours, minutes, rest = value.split(":")
    seconds, milliseconds = rest.split(",")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000


def format_time(value: float) -> str:
    value = max(0.0, value)
    milliseconds_total = int(round(value * 1000))
    hours, remainder = divmod(milliseconds_total, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def parse_srt(path: Path) -> list[tuple[float, float, str]]:
    text = path.read_text(encoding="utf-8-sig", errors="replace").strip()
    if not text:
        return []
    cues: list[tuple[float, float, str]] = []
    for block in re.split(r"\n\s*\n", text):
        lines = [line.strip("\ufeff") for line in block.splitlines() if line.strip()]
        if not lines:
            continue
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
    blocks: list[str] = []
    for index, (start, end, caption) in enumerate(cues, 1):
        blocks.append(
            f"{index}\n{format_time(start)} --> {format_time(end)}\n{caption}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")


def split_text(text: str, max_chars: int) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n+", text) if part.strip()]
    sentences: list[str] = []
    for paragraph in paragraphs:
        sentences.extend(
            value.strip()
            for value in re.split(r"(?<=[。！？!?；;])\s*", paragraph)
            if value.strip()
        )
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if len(sentence) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            for start in range(0, len(sentence), max_chars):
                chunks.append(sentence[start : start + max_chars])
            continue
        candidate = sentence if not current else current + sentence
        if current and len(candidate) > max_chars:
            chunks.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def concat_audio(segment_paths: list[Path], output: Path, list_path: Path) -> None:
    ffmpeg = get_ffmpeg()
    lines = []
    for path in segment_paths:
        escaped = str(path.resolve()).replace("'", "'\\''")
        lines.append(f"file '{escaped}'")
    list_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    run_command(
        [
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
            str(list_path),
            "-c",
            "copy",
            str(output),
        ]
    )


def render_segment(
    edge_tts: Path,
    text_path: Path,
    audio_path: Path,
    subtitle_path: Path,
    *,
    voice: str,
    rate: str,
    volume: str,
    retries: int,
) -> None:
    command = [
        str(edge_tts),
        "--file",
        str(text_path),
        "--voice",
        voice,
        "--rate",
        rate,
        "--volume",
        volume,
        "--write-media",
        str(audio_path),
        "--write-subtitles",
        str(subtitle_path),
    ]
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            run_command(command, capture=True)
            if audio_path.is_file() and audio_path.stat().st_size > 0:
                return
            raise LongformError(f"TTS created an empty file: {audio_path}")
        except (LongformError, OSError) as exc:
            last_error = exc
            if attempt >= retries:
                break
            delay = min(2 ** (attempt - 1), 8)
            print(f"TTS segment failed; retrying in {delay}s: {exc}", file=sys.stderr)
            time.sleep(delay)
    raise LongformError(f"TTS failed after {retries} attempts: {last_error}")


def render_chapter(
    project: Path,
    chapter_id: str,
    *,
    voice: str,
    rate: str,
    volume: str,
    max_chars: int,
    retries: int,
    force: bool,
) -> dict[str, Any]:
    chapter = project / "chapters" / chapter_id
    narration_text = chapter / "narration.txt"
    if not narration_text.is_file() or not narration_text.read_text(
        encoding="utf-8", errors="replace"
    ).strip():
        raise LongformError(f"chapter {chapter_id} has no narration text")
    final_audio = chapter / "audio" / "narration.mp3"
    final_srt = chapter / "subtitles" / "narration.srt"
    if final_audio.is_file() and final_srt.is_file() and not force:
        duration = probe_duration(final_audio)
        print(f"Narration exists, skipping chapter {chapter_id}: {duration:.1f}s")
        return {"duration_seconds": duration, "segments": None, "skipped": True}

    edge_tts = runtime_executable("edge-tts")
    if not edge_tts.is_file():
        raise LongformError(
            "edge-tts is not installed; run python scripts/install_longform_stack.py"
        )
    text = narration_text.read_text(encoding="utf-8", errors="replace").strip()
    chunks = split_text(text, max_chars)
    if not chunks:
        raise LongformError(f"chapter {chapter_id} narration could not be split")

    segment_dir = chapter / "audio" / "segments"
    segment_dir.mkdir(parents=True, exist_ok=True)
    subtitle_dir = chapter / "subtitles" / "segments"
    subtitle_dir.mkdir(parents=True, exist_ok=True)
    audio_paths: list[Path] = []
    merged_cues: list[tuple[float, float, str]] = []
    offset = 0.0
    update_chapter_stage(project, chapter_id, "narration", "running", segments=len(chunks))

    for index, chunk in enumerate(chunks, 1):
        stem = f"segment-{index:04d}"
        text_path = segment_dir / f"{stem}.txt"
        audio_path = segment_dir / f"{stem}.mp3"
        subtitle_path = subtitle_dir / f"{stem}.srt"
        text_path.write_text(chunk + "\n", encoding="utf-8")
        if force or not audio_path.is_file() or audio_path.stat().st_size == 0:
            render_segment(
                edge_tts,
                text_path,
                audio_path,
                subtitle_path,
                voice=voice,
                rate=rate,
                volume=volume,
                retries=retries,
            )
        elif not subtitle_path.is_file():
            render_segment(
                edge_tts,
                text_path,
                audio_path,
                subtitle_path,
                voice=voice,
                rate=rate,
                volume=volume,
                retries=retries,
            )
        duration = probe_duration(audio_path)
        for start, end, caption in parse_srt(subtitle_path):
            merged_cues.append((start + offset, end + offset, caption))
        offset += duration
        audio_paths.append(audio_path)
        print(f"Chapter {chapter_id} TTS: {index}/{len(chunks)}")

    final_audio.parent.mkdir(parents=True, exist_ok=True)
    concat_audio(audio_paths, final_audio, chapter / "audio" / "segments.txt")
    write_srt(final_srt, merged_cues)
    duration = probe_duration(final_audio)
    update_chapter_stage(
        project,
        chapter_id,
        "narration",
        "completed",
        segments=len(chunks),
        duration_seconds=round(duration, 3),
        voice=voice,
        rate=rate,
    )
    return {"duration_seconds": duration, "segments": len(chunks), "skipped": False}


def parse_args() -> argparse.Namespace:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--chapter", action="append")
    parser.add_argument(
        "--voice",
        default=os.environ.get("LONGFORM_TTS_VOICE", "zh-CN-XiaoxiaoNeural"),
    )
    parser.add_argument("--rate", default=os.environ.get("LONGFORM_TTS_RATE", "+0%"))
    parser.add_argument("--volume", default=os.environ.get("LONGFORM_TTS_VOLUME", "+0%"))
    parser.add_argument(
        "--max-chars",
        type=int,
        default=env_int("LONGFORM_TTS_MAX_CHARS", 1800),
    )
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if not 300 <= args.max_chars <= 5000:
        parser.error("--max-chars must be between 300 and 5000")
    if not 1 <= args.retries <= 10:
        parser.error("--retries must be between 1 and 10")
    return args


def main() -> int:
    args = parse_args()
    project, project_data = load_project(args.project)
    available = [str(item.get("id")) for item in project_data.get("chapters", [])]
    chapter_ids = (
        [f"{int(value):02d}" for value in args.chapter] if args.chapter else available
    )
    missing = [value for value in chapter_ids if value not in available]
    if missing:
        raise LongformError(f"unknown chapters: {', '.join(missing)}")

    update_pipeline_stage(project, "narration", "running", chapters=chapter_ids)
    results: dict[str, Any] = {}
    try:
        for chapter_id in chapter_ids:
            results[chapter_id] = render_chapter(
                project,
                chapter_id,
                voice=args.voice,
                rate=args.rate,
                volume=args.volume,
                max_chars=args.max_chars,
                retries=args.retries,
                force=args.force,
            )
    except Exception:
        update_pipeline_stage(project, "narration", "failed")
        raise
    total = sum(float(value["duration_seconds"]) for value in results.values())
    update_pipeline_stage(
        project,
        "narration",
        "completed",
        chapters=chapter_ids,
        duration_seconds=round(total, 3),
    )
    print(f"Narration complete: chapters={len(chapter_ids)}, total={total / 60:.1f} min")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (LongformError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
