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

## 1. 项目目标

- 用途：
- 目标受众：
- 核心信息：
- 发布平台：
- 是否商用：待确认

## 2. 交付规格

- 总时长：{args.duration:g} 秒
- 画面比例：{args.aspect_ratio}
- 帧率：{args.fps} fps
- 生成模式：{args.mode}
- 目标分辨率：待确认
- 输出格式：待确认

## 3. 素材

- 参考图：
- 首尾帧：
- 角色/产品设定：
- 已有视频：
- 音频/旁白/字幕：

## 4. 视觉与声音

- 视觉风格：
- 色彩与光线：
- 镜头语言：
- 音乐/环境声：
- 禁止出现的元素：

## 5. 技术环境

- 操作系统：
- GPU / 可用显存：
- 内存：
- CUDA / PyTorch：
- ComfyUI 或 Diffusers 版本：
- 候选模型：{args.model or '待选'}

## 6. 验收标准

- 主体身份与外观一致。
- 动作和镜头运动连续，无明显跳变。
- 画面无严重闪烁、重影、结构畸变或不可接受的文字错误。
- 帧率、时长、比例、字幕和音频符合交付规格。
- 模型、种子、提示词、输入素材和后处理步骤可追溯。

## 7. 风险与待确认项

- 模型和权重许可证：待核验。
- 具体显存需求与生成速度：需用最小样片实测。
- 人脸、商标、音乐和素材授权：待确认。
"""
    path.write_text(content, encoding="utf-8")


def write_prompts(path: Path, args: argparse.Namespace) -> None:
    content = f"""# {args.name} — Prompt Pack

## 全局视觉锚点

```text
主体：
场景：
时代/地点：
美术风格：
色彩：
光线：
镜头与镜头质感：
画面比例：{args.aspect_ratio}
```

## 一致性锚点

```text
角色/产品不可变化的特征：
服装/材质/颜色：
比例与结构：
标志性细节：
```

## 负向约束

```text
避免主体身份漂移、额外肢体、结构畸变、文字乱码、过度锐化、严重闪烁、镜头瞬移、背景突变。
```

## 镜头提示词

### S001

```text
[主体与场景] + [动作] + [镜头运动] + [构图] + [光线] + [风格] + [时序约束]
```

- 输入素材：
- 需要保持：
- 允许变化：
- 建议种子：
- 结果记录：

> 为每个镜头复制本节，并与 shots.csv 的 shot_id 保持一致。
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
