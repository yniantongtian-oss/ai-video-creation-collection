#!/usr/bin/env python3
"""Create a traceable research-to-video project workspace for Codex."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "projects"
VALID_ASPECT_RATIOS = {"16:9", "9:16", "1:1", "4:5"}


def safe_name(value: str) -> str:
    value = value.strip()
    value = re.sub(r"[\\/:*?\"<>|\x00-\x1f]", "-", value)
    value = re.sub(r"\s+", " ", value).strip(" .-")
    if not value:
        raise ValueError("project name becomes empty after sanitization")
    return value[:100]


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def create_project(args: argparse.Namespace) -> Path:
    name = safe_name(args.name)
    project = args.output.expanduser().resolve() / name
    if project.exists() and any(project.iterdir()) and not args.force:
        raise FileExistsError(
            f"project directory is not empty: {project}; use --force only for an empty scaffold refresh"
        )

    directories = [
        "research/documents",
        "research/notes",
        "research/search-results",
        "assets/images",
        "assets/videos",
        "assets/audio",
        "assets/fonts",
        "manifests",
        "script",
        "storyboard",
        "edit",
        "subtitles",
        "voice",
        "outputs",
        "logs",
    ]
    for relative in directories:
        (project / relative).mkdir(parents=True, exist_ok=True)

    created_at = datetime.now(timezone.utc).isoformat()
    brief = f"""# 项目 Brief：{name}

## 核心目标

- 主题：{args.topic}
- 目标受众：{args.audience}
- 视频时长：{args.duration} 秒
- 画幅：{args.aspect_ratio}
- 语言：{args.language}
- 发布平台：{args.platform}

## 交付物

- 有来源标记的研究资料和摘要
- 素材许可证清单 `manifests/assets.jsonl`
- 旁白/文案 `script/script.md`
- 镜头表 `storyboard/storyboard.csv`
- 剪辑计划 `edit/edit-plan.json`
- 字幕、配音和最终视频
- 发布前事实核查与版权检查报告

## 内容要求

1. 不整段复制文章、视频字幕或受版权保护文本。
2. 所有事实应能追溯到研究来源。
3. 素材优先使用公共领域、CC0、CC BY、CC BY-SA、素材平台授权、用户自有或已获许可内容。
4. 未确认授权的素材不能进入最终剪辑。
5. 不绕过付费墙、DRM、登录限制、robots 规则或平台安全措施。
"""
    write_text(project / "brief.md", brief)

    source_notes = """# 研究来源

Codex 在这里记录每个网页、论文、视频和数据源：

- 标题：
- URL：
- 作者/机构：
- 发布日期：
- 访问日期：
- 核心事实：
- 可引用范围：摘要/短引文/数据
- 可靠性与局限：

不要把搜索摘要当作最终事实依据；应打开原始来源核验。
"""
    write_text(project / "research" / "sources.md", source_notes)

    script = f"""# {name} 视频文案

## 标题候选

1. 
2. 
3. 

## 开头钩子（前 3–8 秒）


## 正文旁白


## 结尾与行动引导


## 事实核查

- [ ] 每个关键事实已对应来源
- [ ] 数据和日期使用绝对日期
- [ ] 未出现无法证明的夸张结论
- [ ] 未大段复述受版权保护内容
"""
    write_text(project / "script" / "script.md", script)

    storyboard_path = project / "storyboard" / "storyboard.csv"
    with storyboard_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "shot_id",
                "start_sec",
                "end_sec",
                "narration",
                "visual_query",
                "asset_id",
                "visual_action",
                "subtitle",
                "source_citation",
                "status",
            ]
        )
        writer.writerow(["S01", "0", "5", "", "", "", "", "", "", "planned"])

    edit_plan = {
        "schema_version": "1.0.0",
        "project": name,
        "duration_seconds": args.duration,
        "aspect_ratio": args.aspect_ratio,
        "resolution": "1080x1920" if args.aspect_ratio == "9:16" else "1920x1080",
        "fps": 30,
        "language": args.language,
        "audio": {
            "voice_source": "edge-tts-or-configured-provider",
            "background_music": "licensed-only",
            "target_loudness": "-14 LUFS starting point",
        },
        "subtitles": {
            "enabled": True,
            "format": "srt",
            "max_lines": 2,
        },
        "rights_gate": {
            "manifest": "manifests/assets.jsonl",
            "required_before_render": True,
            "allowed": [
                "public-domain",
                "cc0",
                "cc-by",
                "cc-by-sa",
                "provider-licensed",
                "user-owned",
                "permission-granted",
            ],
        },
        "created_at": created_at,
    }
    write_text(
        project / "edit" / "edit-plan.json",
        json.dumps(edit_plan, ensure_ascii=False, indent=2),
    )

    manifest_readme = """# 素材清单

`assets.jsonl` 每行一个 JSON 对象。推荐字段：

```json
{
  "id": "asset-001",
  "kind": "video",
  "local_path": "assets/videos/example.mp4",
  "source_url": "https://...",
  "provider": "Wikimedia Commons",
  "title": "...",
  "creator": "...",
  "license": "CC BY 4.0",
  "license_url": "https://creativecommons.org/licenses/by/4.0/",
  "rights_status": "cc-by",
  "attribution": "...",
  "selected": true,
  "sha256": "..."
}
```

最终剪辑只允许使用 `selected=true` 且授权状态通过校验的素材。
"""
    write_text(project / "manifests" / "README.md", manifest_readme)
    (project / "manifests" / "assets.jsonl").touch(exist_ok=True)

    project_manifest = {
        "schema_version": "1.0.0",
        "name": name,
        "topic": args.topic,
        "audience": args.audience,
        "duration_seconds": args.duration,
        "aspect_ratio": args.aspect_ratio,
        "language": args.language,
        "platform": args.platform,
        "created_at": created_at,
        "status": "research",
    }
    write_text(
        project / "project.json",
        json.dumps(project_manifest, ensure_ascii=False, indent=2),
    )
    return project


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="Project directory name.")
    parser.add_argument("--topic", required=True, help="Video topic or research question.")
    parser.add_argument("--audience", default="中文互联网普通观众")
    parser.add_argument("--duration", type=int, default=60)
    parser.add_argument("--aspect-ratio", choices=sorted(VALID_ASPECT_RATIOS), default="9:16")
    parser.add_argument("--language", default="zh-CN")
    parser.add_argument("--platform", default="抖音/B站/视频号")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if not 5 <= args.duration <= 7200:
        parser.error("--duration must be between 5 and 7200 seconds")
    return args


def main() -> int:
    args = parse_args()
    try:
        project = create_project(args)
    except (FileExistsError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Created web media project: {project}")
    print(f"Brief: {project / 'brief.md'}")
    print(f"Asset manifest: {project / 'manifests' / 'assets.jsonl'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
