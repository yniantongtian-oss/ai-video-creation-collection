#!/usr/bin/env python3
"""Run a video pipeline from one project spec.

The spec selects ``longform``, ``web-media``, or ``generation`` and the stages
to chain. Stages run in pipeline order. ``--dry-run`` prints the commands and
does not scaffold a project, download media, call a model, or render video.

Long-form stages:

    scaffold, ingest, research, assets, narration, timeline, render, assemble

Asset review is unchanged. Search results stay unselected, and timeline
construction still rejects a chapter without enough approved assets.
"""

from __future__ import annotations

import argparse
import json
import math
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

import scaffold_longform_project
import scaffold_project
import scaffold_web_media_project

ROOT = Path(__file__).resolve().parents[1]

STAGE_ORDER = {
    "longform": (
        "scaffold",
        "ingest",
        "research",
        "assets",
        "narration",
        "timeline",
        "render",
        "assemble",
    ),
    "web-media": ("scaffold",),
    "generation": ("scaffold",),
}
CHAPTER_STAGES = {"research", "assets", "narration", "timeline", "render"}
LONGFORM_STYLE = (
    "Documentary explainer with high information density and natural narration"
)


class PipelineSpecError(ValueError):
    """The project spec cannot be turned into a command plan."""


class PipelineError(RuntimeError):
    """A chained pipeline command failed."""


def load_spec(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise PipelineSpecError(f"missing spec: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PipelineSpecError(f"invalid spec JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise PipelineSpecError("spec root must be an object")
    return payload


def _text(spec: dict[str, Any], key: str, default: str | None = None) -> str:
    if key not in spec or spec[key] is None:
        if default is None:
            raise PipelineSpecError(f"{key} must be a non-empty string")
        return default
    value = spec[key]
    if not isinstance(value, str) or not value.strip():
        raise PipelineSpecError(f"{key} must be a non-empty string")
    return value.strip()


def _flag(spec: dict[str, Any], key: str, default: bool = False) -> bool:
    if key not in spec or spec[key] is None:
        return default
    value = spec[key]
    if not isinstance(value, bool):
        raise PipelineSpecError(f"{key} must be true or false")
    return value


def _integer(
    spec: dict[str, Any], key: str, default: int, low: int, high: int
) -> int:
    if key not in spec or spec[key] is None:
        return default
    value = spec[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise PipelineSpecError(f"{key} must be an integer")
    if not low <= value <= high:
        raise PipelineSpecError(f"{key} must be between {low} and {high}")
    return value


def _number(spec: dict[str, Any], key: str, default: float) -> float:
    if key not in spec or spec[key] is None:
        return float(default)
    value = spec[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PipelineSpecError(f"{key} must be a number")
    if not math.isfinite(float(value)) or float(value) <= 0:
        raise PipelineSpecError(f"{key} must be greater than zero")
    return float(value)


def _choice(spec: dict[str, Any], key: str, default: str, choices: set[str] | tuple[str, ...]) -> str:
    if key not in spec or spec[key] is None:
        return default
    value = spec[key]
    if value not in choices:
        allowed = ", ".join(sorted(choices))
        raise PipelineSpecError(f"{key} must be one of: {allowed}")
    return str(value)


def _stages(spec: dict[str, Any], pipeline: str) -> list[str]:
    if "stages" not in spec or spec["stages"] is None:
        return list(STAGE_ORDER[pipeline])
    stages = spec["stages"]
    if (
        not isinstance(stages, list)
        or not stages
        or any(not isinstance(item, str) or not item.strip() for item in stages)
    ):
        raise PipelineSpecError("stages must be a non-empty array of stage names")
    names = [item.strip() for item in stages]
    if len(names) != len(set(names)):
        raise PipelineSpecError("stages must not contain duplicates")
    unknown = [item for item in names if item not in STAGE_ORDER[pipeline]]
    if unknown:
        allowed = ", ".join(STAGE_ORDER[pipeline])
        raise PipelineSpecError(
            f"unknown stages for {pipeline}: {', '.join(unknown)}; expected {allowed}"
        )
    return [stage for stage in STAGE_ORDER[pipeline] if stage in names]


def _chapters(spec: dict[str, Any], stages: list[str]) -> list[int]:
    if "chapters" not in spec or spec["chapters"] is None:
        return []
    chapters = spec["chapters"]
    if not isinstance(chapters, list) or any(
        isinstance(item, bool) or not isinstance(item, int) or item <= 0 for item in chapters
    ):
        raise PipelineSpecError("chapters must be an array of positive integers")
    if chapters and "assemble" in stages:
        raise PipelineSpecError(
            "assemble cannot run on a chapter subset; remove chapters or remove assemble"
        )
    return list(chapters)


def _inputs(spec: dict[str, Any]) -> list[str]:
    if "inputs" not in spec or spec["inputs"] is None:
        return []
    inputs = spec["inputs"]
    if not isinstance(inputs, list) or any(
        not isinstance(item, str) or not item.strip() for item in inputs
    ):
        raise PipelineSpecError("inputs must be an array of paths")
    return [item.strip() for item in inputs]


def normalize_spec(spec: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(spec, dict):
        raise PipelineSpecError("spec root must be an object")
    if spec.get("schema_version") != "1.0.0":
        raise PipelineSpecError("schema_version must be 1.0.0")
    pipeline = spec.get("pipeline")
    if pipeline not in STAGE_ORDER:
        allowed = ", ".join(STAGE_ORDER)
        raise PipelineSpecError(f"pipeline must be one of: {allowed}")
    stages = _stages(spec, pipeline)
    output = _text(spec, "output", "projects")
    normalized: dict[str, Any] = {
        "schema_version": "1.0.0",
        "pipeline": pipeline,
        "name": _text(spec, "name"),
        "output": output,
        "output_path": str(Path(output).expanduser().resolve()),
        "stages": stages,
        "force": _flag(spec, "force"),
        "chapters": _chapters(spec, stages),
    }
    if pipeline == "longform":
        download_first = _integer(spec, "download_first", 1, 0, 50)
        normalized.update(
            {
                "topic": _text(spec, "topic"),
                "duration_minutes": _integer(spec, "duration_minutes", 90, 30, 360),
                "chapter_minutes": _integer(spec, "chapter_minutes", 7, 3, 20),
                "aspect_ratio": _choice(spec, "aspect_ratio", "16:9", {"16:9", "9:16", "1:1"}),
                "language": _text(spec, "language", "en-US"),
                "audience": _text(spec, "audience", "General audience"),
                "style": _text(spec, "style", LONGFORM_STYLE),
                "inputs": _inputs(spec),
                "execute_search": _flag(spec, "execute_search"),
                "download_first": download_first,
                "search_limit": max(8, download_first),
                "allow_placeholders": _flag(spec, "allow_placeholders"),
                "reset_index": _flag(spec, "reset_index"),
            }
        )
    elif pipeline == "web-media":
        normalized.update(
            {
                "topic": _text(spec, "topic"),
                "duration_seconds": _integer(spec, "duration_seconds", 60, 5, 7200),
                "aspect_ratio": _choice(
                    spec, "aspect_ratio", "9:16", scaffold_web_media_project.VALID_ASPECT_RATIOS
                ),
                "language": _text(spec, "language", "en-US"),
                "audience": _text(spec, "audience", "General online audience"),
                "platform": _text(spec, "platform", "YouTube/TikTok/Instagram"),
            }
        )
    else:
        aspect = spec.get("aspect_ratio", "16:9")
        if aspect is None:
            aspect = "16:9"
        if not isinstance(aspect, str):
            raise PipelineSpecError("aspect_ratio must use a ratio such as 16:9 or 9:16")
        try:
            aspect_ratio = scaffold_project.aspect_ratio(aspect)
        except argparse.ArgumentTypeError as exc:
            raise PipelineSpecError(f"aspect_ratio {exc}") from exc
        normalized.update(
            {
                "duration_seconds": _number(spec, "duration_seconds", 15),
                "shot_length": _number(spec, "shot_length", 5),
                "aspect_ratio": aspect_ratio,
                "fps": _integer(spec, "fps", 24, 1, 240),
                "mode": _choice(spec, "mode", "mixed", scaffold_project.ALLOWED_MODES),
                "model": spec.get("model", "") if spec.get("model") is not None else "",
            }
        )
        if not isinstance(normalized["model"], str):
            raise PipelineSpecError("model must be a string")
        normalized["model"] = normalized["model"].strip()
    return normalized


def project_directory(spec: dict[str, Any]) -> Path:
    output = Path(spec["output_path"])
    try:
        if spec["pipeline"] == "longform":
            name = scaffold_longform_project.safe_name(spec["name"])
        elif spec["pipeline"] == "web-media":
            name = scaffold_web_media_project.safe_name(spec["name"])
        else:
            name = scaffold_project.safe_directory_name(spec["name"])
    except ValueError as exc:
        raise PipelineSpecError(str(exc)) from exc
    return output / name


def _chapter_args(spec: dict[str, Any]) -> list[str]:
    arguments: list[str] = []
    for chapter in spec["chapters"]:
        arguments.extend(["--chapter", str(chapter)])
    return arguments


def _with_force(command: list[str], spec: dict[str, Any]) -> list[str]:
    if spec["force"]:
        command.append("--force")
    return command


def _format_number(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return format(value, "g")


def command_for(spec: dict[str, Any], project: Path, stage: str) -> list[str]:
    pipeline = spec["pipeline"]
    if pipeline == "generation":
        command = [
            "scripts/scaffold_project.py",
            "--name",
            spec["name"],
            "--output",
            spec["output_path"],
            "--duration",
            _format_number(spec["duration_seconds"]),
            "--shot-length",
            _format_number(spec["shot_length"]),
            "--aspect-ratio",
            spec["aspect_ratio"],
            "--fps",
            str(spec["fps"]),
            "--mode",
            spec["mode"],
        ]
        if spec["model"]:
            command.extend(["--model", spec["model"]])
        return _with_force(command, spec)
    if pipeline == "web-media":
        command = [
            "scripts/scaffold_web_media_project.py",
            "--name",
            spec["name"],
            "--topic",
            spec["topic"],
            "--audience",
            spec["audience"],
            "--duration",
            str(spec["duration_seconds"]),
            "--aspect-ratio",
            spec["aspect_ratio"],
            "--language",
            spec["language"],
            "--platform",
            spec["platform"],
            "--output",
            spec["output_path"],
        ]
        return _with_force(command, spec)

    if stage == "scaffold":
        command = [
            "scripts/scaffold_longform_project.py",
            "--name",
            spec["name"],
            "--topic",
            spec["topic"],
            "--duration",
            str(spec["duration_minutes"]),
            "--chapter-minutes",
            str(spec["chapter_minutes"]),
            "--aspect-ratio",
            spec["aspect_ratio"],
            "--language",
            spec["language"],
            "--audience",
            spec["audience"],
            "--style",
            spec["style"],
            "--output",
            spec["output_path"],
        ]
        return _with_force(command, spec)
    if stage == "ingest":
        command = ["scripts/ingest_longform_corpus.py", "--project", str(project)]
        for path in spec["inputs"]:
            command.extend(["--input", path])
        if spec["reset_index"]:
            command.append("--reset-index")
        return command
    if stage == "research":
        command = ["scripts/longform_pipeline.py", "--project", str(project), "run"]
        command.extend(_chapter_args(spec))
        return _with_force(command, spec)
    if stage == "assets":
        command = [
            "scripts/build_longform_asset_plan.py",
            "--project",
            str(project),
            "--max-queries-per-chapter",
            "12",
            "--limit",
            str(spec["search_limit"]),
        ]
        command.extend(_chapter_args(spec))
        if spec["execute_search"]:
            command.append("--execute")
            command.extend(["--download-first", str(spec["download_first"])])
        return command
    if stage == "narration":
        command = ["scripts/render_longform_narration.py", "--project", str(project)]
        command.extend(_chapter_args(spec))
        return _with_force(command, spec)
    if stage == "timeline":
        command = ["scripts/build_longform_timeline.py", "--project", str(project)]
        command.extend(_chapter_args(spec))
        if spec["allow_placeholders"]:
            command.append("--allow-placeholders")
        return command
    if stage == "render":
        command = ["scripts/render_longform_chapters.py", "--project", str(project)]
        command.extend(_chapter_args(spec))
        if spec["allow_placeholders"]:
            command.append("--allow-placeholders")
        return _with_force(command, spec)
    if stage == "assemble":
        command = ["scripts/assemble_longform_video.py", "--project", str(project)]
        return _with_force(command, spec)
    raise PipelineSpecError(f"unsupported stage: {stage}")


def build_plan(spec: dict[str, Any]) -> tuple[dict[str, Any], list[list[str]]]:
    normalized = normalize_spec(spec)
    project = project_directory(normalized)
    commands = [command_for(normalized, project, stage) for stage in normalized["stages"]]
    return normalized, commands


def plan_warnings(stages: list[str]) -> list[str]:
    if any(stage in {"timeline", "render", "assemble"} for stage in stages):
        return [
            "Asset review remains mandatory. Timeline construction rejects chapters "
            "without enough approved assets."
        ]
    return []


def format_command(command: list[str]) -> str:
    rendered = " ".join(shlex.quote(part) for part in command)
    return f"$ python {rendered}"


def run_plan(commands: list[list[str]], *, dry_run: bool) -> int:
    for command in commands:
        print(format_command(command))
        if dry_run:
            continue
        script = Path(command[0])
        if not script.is_absolute():
            script = ROOT / script
        result = subprocess.run([sys.executable, str(script), *command[1:]], check=False)
        if result.returncode != 0:
            raise PipelineError(
                f"stage failed with exit code {result.returncode}: {command[0]}"
            )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True, help="path to a project spec JSON file")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the chained commands without running them",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        spec = load_spec(args.spec)
        normalized, commands = build_plan(spec)
    except PipelineSpecError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    for warning in plan_warnings(normalized["stages"]):
        print(warning)
    try:
        return run_plan(commands, dry_run=args.dry_run)
    except (PipelineError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
