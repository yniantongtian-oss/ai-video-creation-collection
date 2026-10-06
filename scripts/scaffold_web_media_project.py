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
    brief = f"""# Project Brief: {name}

## Core goal

- Topic: {args.topic}
- Target audience: {args.audience}
- Duration: {args.duration} seconds
- Aspect ratio: {args.aspect_ratio}
- Language: {args.language}
- Distribution platform: {args.platform}

## Deliverables

- Research notes and summaries with source references
- Media license manifest at `manifests/assets.jsonl`
- Narration/script at `script/script.md`
- Shot list at `storyboard/storyboard.csv`
- Editing plan at `edit/edit-plan.json`
- Subtitles, narration audio, and final video
- Pre-release fact-check and rights-review report

## Content requirements

1. Do not reproduce long passages from articles, video transcripts, or copyrighted text.
2. Every important factual claim should be traceable to a research source.
3. Prefer public-domain, CC0, CC BY, CC BY-SA, provider-licensed, user-owned, or explicitly permitted media.
4. Media with unverified rights must not enter the final edit.
5. Do not bypass paywalls, DRM, authentication restrictions, robots rules, or platform security controls.
"""
    write_text(project / "brief.md", brief)

    source_notes = """# Research Sources

Record each web page, paper, video, and data source here:

- Title:
- URL:
- Author/organization:
- Publication date:
- Access date:
- Key facts:
- Allowed quotation scope: summary / short quotation / data
- Reliability and limitations:

Search-result snippets are discovery aids, not final evidence. Open and verify the original source.
"""
    write_text(project / "research" / "sources.md", source_notes)

    script = f"""# {name} Video Script

## Title candidates

1.
2.
3.

## Opening hook (first 3–8 seconds)


## Main narration


## Ending and call to action


## Fact check

- [ ] Every important claim has a source
- [ ] Data and dates use unambiguous absolute dates
- [ ] No unsupported or exaggerated conclusions
- [ ] No substantial reproduction of copyrighted source text
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

    manifest_readme = """# Asset Manifest

`assets.jsonl` stores one JSON object per line. Recommended fields:

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

The final edit may use only assets with `selected=true` whose rights status passes validation.
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
    parser.add_argument("--audience", default="General online audience")
    parser.add_argument("--duration", type=int, default=60)
    parser.add_argument("--aspect-ratio", choices=sorted(VALID_ASPECT_RATIOS), default="9:16")
    parser.add_argument("--language", default="en-US")
    parser.add_argument("--platform", default="YouTube/TikTok/Instagram")
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
