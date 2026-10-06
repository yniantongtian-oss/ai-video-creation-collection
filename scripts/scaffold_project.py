#!/usr/bin/env python3
"""Create a reproducible AI-video project skeleton with no external dependencies."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import shutil
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ALLOWED_MODES = ("t2v", "i2v", "v2v", "continuation", "mixed")
ASPECT_PATTERN = re.compile(r"^[1-9]\d*:[1-9]\d*$")
INVALID_PATH_CHARS = re.compile(r"[\\/:*?\"<>|]+")


def positive_float(value: str) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a number") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return number


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return number


def aspect_ratio(value: str) -> str:
    if not ASPECT_PATTERN.fullmatch(value):
        raise argparse.ArgumentTypeError("must use a ratio such as 16:9 or 9:16")
    return value


def safe_directory_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip()
    normalized = INVALID_PATH_CHARS.sub("-", normalized)
    normalized = re.sub(r"\s+", "-", normalized)
    normalized = normalized.strip("-. ")
    if not normalized or normalized in {".", ".."}:
        raise ValueError("project name does not contain a usable directory name")
    return normalized[:100]


def build_shots(duration: float, shot_length: float, mode: str) -> list[dict[str, object]]:
    shot_count = max(1, math.ceil(duration / shot_length))
    shots: list[dict[str, object]] = []
    elapsed = 0.0

    for index in range(shot_count):
        remaining = max(0.0, duration - elapsed)
        current_duration = min(shot_length, remaining) if remaining else shot_length
        shots.append(
            {
                "shot_id": f"S{index + 1:03d}",
                "start_sec": round(elapsed, 3),
                "duration_sec": round(current_duration, 3),
                "mode": mode,
                "visual": "",
                "action": "",
                "camera": "",
                "input_asset": "",
                "model": "",
                "seed": "",
                "status": "planned",
                "notes": "",
            }
        )
        elapsed += current_duration

    return shots


def write_brief(path: Path, args: argparse.Namespace) -> None:
    content = f"""# {args.name} — Video Brief

## 1. Project goals

- Purpose:
- Target audience:
- Core message:
- Distribution platform:
- Commercial use: to be confirmed

## 2. Delivery specification

- Total duration: {args.duration:g} seconds
- Aspect ratio: {args.aspect_ratio}
- Frame rate: {args.fps} fps
- Generation mode: {args.mode}
- Target resolution: to be confirmed
- Output format: to be confirmed

## 3. Assets

- Reference images:
- First/last frames:
- Character/product design:
- Existing video:
- Audio/narration/subtitles:

## 4. Visual and audio direction

- Visual style:
- Color and lighting:
- Camera language:
- Music/ambience:
- Prohibited elements:

## 5. Technical environment

- Operating system:
- GPU / available VRAM:
- RAM:
- CUDA / PyTorch:
- ComfyUI or Diffusers version:
- Candidate model: {args.model or 'to be selected'}

## 6. Acceptance criteria

- Subject identity and appearance remain consistent.
- Subject and camera motion are continuous without obvious jumps.
- No severe flicker, ghosting, structural deformation, or unacceptable text artifacts.
- Frame rate, duration, aspect ratio, subtitles, and audio meet the delivery specification.
- Model, seed, prompts, input assets, and post-processing steps are traceable.

## 7. Risks and open questions

- Model and weight licenses: verify before use.
- VRAM requirements and generation speed: measure with a minimal sample.
- Rights for faces, trademarks, music, and source media: confirm before release.
"""
    path.write_text(content, encoding="utf-8")


def write_prompts(path: Path, args: argparse.Namespace) -> None:
    content = f"""# {args.name} — Prompt Pack

## Global visual anchors

```text
Subject:
Scene:
Period/location:
Art direction:
Color:
Lighting:
Camera/lens character:
Aspect ratio: {args.aspect_ratio}
```

## Consistency anchors

```text
Invariant character/product traits:
Wardrobe/material/color:
Proportions and structure:
Signature details:
```

## Negative constraints

```text
Avoid identity drift, extra limbs, structural deformation, unreadable text,
over-sharpening, severe flicker, camera teleportation, and abrupt background changes.
```

## Shot prompts

### S001

```text
[subject and scene] + [action] + [camera motion] + [composition] + [lighting] + [style] + [temporal constraints]
```

- Input assets:
- Must remain stable:
- Allowed to change:
- Suggested seed:
- Result notes:

> Duplicate this section for each shot and keep the heading aligned with shot_id in shots.csv.
"""
    path.write_text(content, encoding="utf-8")


def write_shots(path: Path, shots: list[dict[str, object]]) -> None:
    fieldnames = list(shots[0].keys())
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(shots)


def write_manifest(path: Path, args: argparse.Namespace, shots: list[dict[str, object]]) -> None:
    manifest = {
        "schema_version": "1.0.0",
        "project": {
            "name": args.name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": args.duration,
            "aspect_ratio": args.aspect_ratio,
            "fps": args.fps,
            "mode": args.mode,
            "preferred_model": args.model or None,
        },
        "environment": {
            "operating_system": None,
            "gpu": None,
            "vram_gb": None,
            "python": None,
            "pytorch": None,
            "cuda": None,
            "comfyui": None,
        },
        "reproducibility": {
            "workflow_file": None,
            "model_checkpoint": None,
            "model_revision": None,
            "vae": None,
            "text_encoder": None,
            "loras": [],
            "custom_nodes": [],
            "post_processing": [],
        },
        "shot_count": len(shots),
    }
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="project name")
    parser.add_argument("--output", default="projects", help="parent output directory")
    parser.add_argument("--duration", type=positive_float, default=15.0, help="total duration in seconds")
    parser.add_argument("--shot-length", type=positive_float, default=5.0, help="planned seconds per shot")
    parser.add_argument("--aspect-ratio", type=aspect_ratio, default="16:9")
    parser.add_argument("--fps", type=positive_int, default=24)
    parser.add_argument("--mode", choices=ALLOWED_MODES, default="mixed")
    parser.add_argument("--model", default="", help="optional preferred model name")
    parser.add_argument("--force", action="store_true", help="replace an existing project directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        directory_name = safe_directory_name(args.name)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    output_root = Path(args.output).expanduser().resolve()
    project_dir = output_root / directory_name

    if project_dir.exists():
        if not args.force:
            print(f"ERROR: project already exists: {project_dir}", file=sys.stderr)
            print("Use --force only when replacing it is intentional.", file=sys.stderr)
            return 1
        if project_dir.is_dir():
            shutil.rmtree(project_dir)
        else:
            project_dir.unlink()

    project_dir.mkdir(parents=True, exist_ok=False)
    shots = build_shots(args.duration, args.shot_length, args.mode)

    write_brief(project_dir / "brief.md", args)
    write_manifest(project_dir / "manifest.json", args, shots)
    write_prompts(project_dir / "prompts.md", args)
    write_shots(project_dir / "shots.csv", shots)

    print(f"Created project: {project_dir}")
    print(f"Planned shots: {len(shots)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
