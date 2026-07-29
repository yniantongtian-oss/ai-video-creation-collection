#!/usr/bin/env python3
"""Render each long-form chapter independently from its timeline and narration."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from longform_common import (
    LongformError,
    append_jsonl,
    env_float,
    get_ffmpeg,
    load_dotenv,
    load_project,
    probe_duration,
    read_json,
    run_command,
    update_chapter_stage,
    update_pipeline_stage,
)

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".avif"}
VIDEO_SUFFIXES = {".mp4", ".mkv", ".webm", ".mov", ".m4v", ".avi", ".ts"}
AUDIO_SUFFIXES = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}


def safe_concat_path(path: Path) -> str:
    return str(path.resolve()).replace("'", "'\\''")


def scale_filter(width: int, height: int, fps: int) -> str:
    return (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},setsar=1,fps={fps},format=yuv420p"
    )


def image_filter(width: int, height: int, fps: int) -> str:
    return (
        f"scale={width * 2}:{height * 2}:force_original_aspect_ratio=increase,"
        f"crop={width * 2}:{height * 2},"
        "zoompan=z='min(zoom+0.00035,1.08)':"
        "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d=1:s={width}x{height}:fps={fps},setsar=1,format=yuv420p"
    )


def render_shot(
    ffmpeg: Path,
    entry: dict[str, Any],
    output: Path,
    *,
    width: int,
    height: int,
    fps: int,
    encoder: str,
    preset: str,
    video_bitrate: str,
    allow_placeholders: bool,
    force: bool,
    log_path: Path,
) -> None:
    if output.is_file() and output.stat().st_size > 0 and not force:
        return
    duration = max(0.5, float(entry.get("duration_seconds") or 1.0))
    kind = str(entry.get("kind") or "")
    asset_value = str(entry.get("asset_path") or "")
    asset = Path(asset_value).expanduser().resolve() if asset_value else None
    common_output = [
        "-an",
        "-c:v",
        encoder,
        "-preset",
        preset,
        "-b:v",
        video_bitrate,
        "-maxrate",
        video_bitrate,
        "-bufsize",
        str(int(re.sub(r"\D", "", video_bitrate) or "8000") * 2) + "k",
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(fps),
        "-g",
        str(fps * 2),
        "-movflags",
        "+faststart",
        str(output),
    ]
    if kind == "placeholder" or not asset:
        if not allow_placeholders:
            raise LongformError(f"placeholder is not allowed in final render: {entry.get('id')}")
        command = [
            str(ffmpeg),
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"color=c=black:s={width}x{height}:r={fps}:d={duration:.3f}",
            "-t",
            f"{duration:.3f}",
            *common_output,
        ]
    elif not asset.is_file():
        raise LongformError(f"timeline asset is missing: {asset}")
    elif kind == "image" or asset.suffix.lower() in IMAGE_SUFFIXES:
        command = [
            str(ffmpeg),
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-loop",
            "1",
            "-i",
            str(asset),
            "-t",
            f"{duration:.3f}",
            "-vf",
            image_filter(width, height, fps),
            *common_output,
        ]
    elif kind == "video" or asset.suffix.lower() in VIDEO_SUFFIXES:
        command = [
            str(ffmpeg),
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-stream_loop",
            "-1",
            "-i",
            str(asset),
            "-t",
            f"{duration:.3f}",
            "-vf",
            scale_filter(width, height, fps),
            *common_output,
        ]
    else:
        raise LongformError(f"unsupported visual asset type: {asset}")
    output.parent.mkdir(parents=True, exist_ok=True)
    run_command(command, log_path=log_path)
    if not output.is_file() or output.stat().st_size == 0:
        raise LongformError(f"shot render produced no output: {output}")


def concat_shots(ffmpeg: Path, shots: list[Path], output: Path, list_path: Path) -> None:
    list_path.write_text(
        "\n".join(f"file '{safe_concat_path(path)}'" for path in shots) + "\n",
        encoding="utf-8",
    )
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
            "-movflags",
            "+faststart",
            str(output),
        ]
    )


def find_bgm(project: Path, chapter_id: str, explicit: Path | None) -> Path | None:
    if explicit:
        path = explicit.expanduser().resolve()
        if not path.is_file():
            raise LongformError(f"BGM file does not exist: {path}")
        return path
    directories = [
        project / "chapters" / chapter_id / "assets" / "audio",
        project / "assets" / "global" / "audio",
    ]
    for directory in directories:
        if not directory.is_dir():
            continue
        preferred = sorted(directory.glob("bgm.*"))
        candidates = preferred or sorted(
            path for path in directory.iterdir() if path.suffix.lower() in AUDIO_SUFFIXES
        )
        if candidates:
            return candidates[0]
    return None


def subtitle_filter_path(path: Path) -> str:
    value = path.resolve().as_posix().replace("'", r"\'")
    value = value.replace(":", r"\:")
    return value


def mux_chapter(
    ffmpeg: Path,
    silent_video: Path,
    narration: Path,
    subtitles: Path,
    output: Path,
    *,
    bgm: Path | None,
    bgm_volume: float,
    audio_bitrate: str,
    encoder: str,
    preset: str,
    video_bitrate: str,
    burn_subtitles: bool,
    embed_subtitles: bool,
    log_path: Path,
) -> None:
    command = [str(ffmpeg), "-y", "-hide_banner", "-loglevel", "error", "-i", str(silent_video), "-i", str(narration)]
    subtitle_input_index: int | None = None
    if bgm:
        command.extend(["-stream_loop", "-1", "-i", str(bgm)])
    if embed_subtitles and subtitles.is_file():
        subtitle_input_index = 3 if bgm else 2
        command.extend(["-i", str(subtitles)])

    if bgm:
        command.extend(
            [
                "-filter_complex",
                f"[1:a]loudnorm=I=-16:LRA=11:TP=-1.5[n];"
                f"[2:a]volume={bgm_volume:.4f}[b];"
                "[n][b]amix=inputs=2:duration=first:dropout_transition=2[a]",
                "-map",
                "0:v:0",
                "-map",
                "[a]",
            ]
        )
    else:
        command.extend(["-map", "0:v:0", "-map", "1:a:0"])
    if subtitle_input_index is not None:
        command.extend(["-map", f"{subtitle_input_index}:0"])

    if burn_subtitles and subtitles.is_file():
        command.extend(
            [
                "-vf",
                "subtitles='"
                + subtitle_filter_path(subtitles)
                + "':force_style='FontSize=22,Outline=2,Shadow=0,MarginV=36'",
                "-c:v",
                encoder,
                "-preset",
                preset,
                "-b:v",
                video_bitrate,
                "-pix_fmt",
                "yuv420p",
            ]
        )
    else:
        command.extend(["-c:v", "copy"])
    command.extend(["-c:a", "aac", "-b:a", audio_bitrate])
    if subtitle_input_index is not None:
        command.extend(["-c:s", "mov_text", "-metadata:s:s:0", "language=chi"])
    command.extend(["-shortest", "-movflags", "+faststart", str(output)])
    run_command(command, log_path=log_path)


def render_chapter(
    project: Path,
    project_data: dict[str, Any],
    chapter_id: str,
    *,
    encoder: str,
    preset: str,
    video_bitrate: str,
    audio_bitrate: str,
    burn_subtitles: bool,
    embed_subtitles: bool,
    allow_placeholders: bool,
    bgm: Path | None,
    bgm_volume: float,
    force: bool,
) -> dict[str, Any]:
    ffmpeg = get_ffmpeg()
    chapter = project / "chapters" / chapter_id
    timeline = read_json(chapter / "timeline.json")
    if not isinstance(timeline, list) or not timeline:
        raise LongformError(
            f"chapter {chapter_id} has no timeline; run build_longform_timeline.py"
        )
    video_config = project_data.get("video", {})
    width = int(video_config.get("width", 1920))
    height = int(video_config.get("height", 1080))
    fps = int(video_config.get("fps", 30))
    narration = chapter / "audio" / "narration.mp3"
    subtitles = chapter / "subtitles" / "narration.srt"
    if not narration.is_file():
        raise LongformError(f"chapter {chapter_id} narration is missing")
    output = project / "outputs" / "chapters" / f"chapter-{chapter_id}.mp4"
    if output.is_file() and output.stat().st_size > 0 and not force:
        duration = probe_duration(output)
        print(f"Chapter video exists, skipping {chapter_id}: {duration:.1f}s")
        return {"chapter": chapter_id, "output": str(output), "duration_seconds": duration, "skipped": True}

    update_chapter_stage(project, chapter_id, "render", "running", shots=len(timeline))
    shot_outputs: list[Path] = []
    for index, entry in enumerate(timeline, 1):
        if not isinstance(entry, dict):
            continue
        shot_output = chapter / "render" / "shots" / f"shot-{index:04d}.mp4"
        render_shot(
            ffmpeg,
            entry,
            shot_output,
            width=width,
            height=height,
            fps=fps,
            encoder=encoder,
            preset=preset,
            video_bitrate=video_bitrate,
            allow_placeholders=allow_placeholders,
            force=force,
            log_path=project / "logs" / f"chapter-{chapter_id}-shot-{index:04d}.log",
        )
        shot_outputs.append(shot_output)
        print(f"Chapter {chapter_id} render: {index}/{len(timeline)}")
    silent = chapter / "render" / "intermediate" / "silent.mp4"
    silent.parent.mkdir(parents=True, exist_ok=True)
    concat_shots(
        ffmpeg,
        shot_outputs,
        silent,
        chapter / "render" / "intermediate" / "shots.txt",
    )
    selected_bgm = find_bgm(project, chapter_id, bgm)
    output.parent.mkdir(parents=True, exist_ok=True)
    mux_chapter(
        ffmpeg,
        silent,
        narration,
        subtitles,
        output,
        bgm=selected_bgm,
        bgm_volume=bgm_volume,
        audio_bitrate=audio_bitrate,
        encoder=encoder,
        preset=preset,
        video_bitrate=video_bitrate,
        burn_subtitles=burn_subtitles,
        embed_subtitles=embed_subtitles,
        log_path=project / "logs" / f"chapter-{chapter_id}-mux.log",
    )
    duration = probe_duration(output)
    sidecar = project / "outputs" / "chapters" / f"chapter-{chapter_id}.srt"
    if subtitles.is_file():
        shutil.copy2(subtitles, sidecar)
    update_chapter_stage(
        project,
        chapter_id,
        "render",
        "completed",
        output=str(output.relative_to(project)),
        duration_seconds=round(duration, 3),
        shots=len(shot_outputs),
        bgm=str(selected_bgm) if selected_bgm else "",
        burn_subtitles=burn_subtitles,
    )
    append_jsonl(
        project / "manifests" / "render.jsonl",
        {
            "chapter": chapter_id,
            "output": str(output.relative_to(project)),
            "duration_seconds": round(duration, 3),
            "shots": len(shot_outputs),
            "rendered_at": datetime.now(timezone.utc).isoformat(),
            "encoder": encoder,
            "video_bitrate": video_bitrate,
            "audio_bitrate": audio_bitrate,
            "bgm": str(selected_bgm) if selected_bgm else "",
        },
    )
    return {"chapter": chapter_id, "output": str(output), "duration_seconds": duration, "skipped": False}


def parse_args() -> argparse.Namespace:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--chapter", action="append")
    parser.add_argument("--encoder", default="libx264")
    parser.add_argument("--preset", default=os.environ.get("LONGFORM_PRESET", "medium"))
    parser.add_argument("--video-bitrate", default=os.environ.get("LONGFORM_VIDEO_BITRATE", "8000k"))
    parser.add_argument("--audio-bitrate", default=os.environ.get("LONGFORM_AUDIO_BITRATE", "192k"))
    parser.add_argument("--bgm", type=Path)
    parser.add_argument(
        "--bgm-volume",
        type=float,
        default=env_float("LONGFORM_BGM_VOLUME", 0.08),
    )
    parser.add_argument("--burn-subtitles", action="store_true")
    parser.add_argument("--no-subtitle-track", action="store_true")
    parser.add_argument("--allow-placeholders", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if not 0 <= args.bgm_volume <= 1:
        parser.error("--bgm-volume must be between 0 and 1")
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
    update_pipeline_stage(project, "chapter_render", "running", chapters=chapter_ids)
    results: list[dict[str, Any]] = []
    try:
        for chapter_id in chapter_ids:
            results.append(
                render_chapter(
                    project,
                    project_data,
                    chapter_id,
                    encoder=args.encoder,
                    preset=args.preset,
                    video_bitrate=args.video_bitrate,
                    audio_bitrate=args.audio_bitrate,
                    burn_subtitles=args.burn_subtitles,
                    embed_subtitles=not args.no_subtitle_track,
                    allow_placeholders=args.allow_placeholders,
                    bgm=args.bgm,
                    bgm_volume=args.bgm_volume,
                    force=args.force,
                )
            )
    except Exception:
        update_pipeline_stage(project, "chapter_render", "failed")
        raise
    total = sum(float(item["duration_seconds"]) for item in results)
    update_pipeline_stage(
        project,
        "chapter_render",
        "completed",
        chapters=chapter_ids,
        duration_seconds=round(total, 3),
    )
    print(f"Chapter rendering complete: {len(results)} chapters, {total / 60:.1f} min")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (LongformError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
