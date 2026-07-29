#!/usr/bin/env python3
"""Deduplicate shot queries and optionally search open-license media providers."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from longform_common import LongformError, load_project, read_json, update_pipeline_stage, write_json

ROOT = Path(__file__).resolve().parents[1]
SEARCH_SCRIPT = ROOT / "scripts" / "search_open_media.py"


def normalize_query(value: str) -> str:
    value = re.sub(r"\s+", " ", value.strip().lower())
    value = re.sub(r"[^0-9a-z\u4e00-\u9fff _-]+", "", value)
    return value[:160]


def provider_plan(visual_type: str) -> list[tuple[str, str]]:
    visual_type = visual_type.lower()
    if visual_type == "video":
        return [("pexels", "video"), ("pixabay", "video"), ("commons", "video")]
    if visual_type in {"document", "map", "timeline", "diagram"}:
        return [("commons", "image"), ("openverse", "image")]
    return [
        ("commons", "image"),
        ("openverse", "image"),
        ("pexels", "image"),
        ("pixabay", "image"),
    ]


def safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip(".-")
    return cleaned[:120] or "query"


def collect_chapter_queries(
    project: Path, chapter_id: str, max_queries: int
) -> list[dict[str, Any]]:
    shots_path = project / "chapters" / chapter_id / "shots.json"
    shots = read_json(shots_path)
    if not isinstance(shots, list) or not shots:
        raise LongformError(f"chapter {chapter_id} has no shot plan")
    grouped: OrderedDict[str, dict[str, Any]] = OrderedDict()
    for shot in shots:
        if not isinstance(shot, dict):
            continue
        visual_type = str(shot.get("visual_type") or "image")
        values = shot.get("search_queries")
        if not isinstance(values, list):
            values = []
        for value in values:
            query = normalize_query(str(value))
            if not query:
                continue
            item = grouped.setdefault(
                query,
                {
                    "query": str(value).strip(),
                    "normalized_query": query,
                    "chapter": chapter_id,
                    "visual_type": visual_type,
                    "shot_ids": [],
                    "providers": [
                        {"provider": provider, "media_type": media_type}
                        for provider, media_type in provider_plan(visual_type)
                    ],
                },
            )
            shot_id = str(shot.get("id") or "")
            if shot_id and shot_id not in item["shot_ids"]:
                item["shot_ids"].append(shot_id)
            if len(grouped) >= max_queries:
                break
        if len(grouped) >= max_queries:
            break
    return list(grouped.values())


def execute_searches(
    project: Path,
    plans: list[dict[str, Any]],
    *,
    limit: int,
    download_first: int,
    continue_on_error: bool,
) -> None:
    if not SEARCH_SCRIPT.is_file():
        raise LongformError(f"missing search helper: {SEARCH_SCRIPT}")
    manifest = project / "manifests" / "assets.jsonl"
    for query_index, item in enumerate(plans, 1):
        query = str(item["query"])
        chapter_id = str(item["chapter"])
        query_slug = safe_filename(f"{chapter_id}-{query_index:03d}-{item['normalized_query']}")
        executions: list[dict[str, Any]] = []
        for provider_item in item.get("providers", []):
            provider = str(provider_item["provider"])
            media_type = str(provider_item["media_type"])
            output = (
                project
                / "assets"
                / "search-results"
                / f"{query_slug}-{provider}.json"
            )
            kind_dir = "videos" if media_type == "video" else "images"
            download_dir = project / "assets" / "global" / kind_dir
            command = [
                sys.executable,
                str(SEARCH_SCRIPT),
                "--provider",
                provider,
                "--media-type",
                media_type,
                "--query",
                query,
                "--limit",
                str(limit),
                "--output",
                str(output),
            ]
            if download_first:
                command.extend(
                    [
                        "--download-dir",
                        str(download_dir),
                        "--download-first",
                        str(download_first),
                        "--manifest",
                        str(manifest),
                    ]
                )
            print("$ " + " ".join(command))
            result = subprocess.run(command, check=False)
            execution = {
                "provider": provider,
                "media_type": media_type,
                "output": str(output.relative_to(project)),
                "returncode": result.returncode,
            }
            executions.append(execution)
            if result.returncode != 0 and not continue_on_error:
                raise LongformError(
                    f"asset search failed: chapter={chapter_id}, provider={provider}, query={query}"
                )
        item["executions"] = executions


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--chapter", action="append")
    parser.add_argument("--max-queries-per-chapter", type=int, default=12)
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--download-first",
        type=int,
        default=0,
        help="Download this many candidates per provider. They remain unselected.",
    )
    parser.add_argument("--fail-fast", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.max_queries_per_chapter <= 50:
        parser.error("--max-queries-per-chapter must be between 1 and 50")
    if not 1 <= args.limit <= 50:
        parser.error("--limit must be between 1 and 50")
    if not 0 <= args.download_first <= args.limit:
        parser.error("--download-first must be between 0 and --limit")
    return args


def main() -> int:
    args = parse_args()
    project, project_data = load_project(args.project)
    available = [str(item.get("id")) for item in project_data.get("chapters", [])]
    if args.chapter:
        chapter_ids = [f"{int(value):02d}" for value in args.chapter]
        missing = [value for value in chapter_ids if value not in available]
        if missing:
            raise LongformError(f"unknown chapters: {', '.join(missing)}")
    else:
        chapter_ids = available

    plans: list[dict[str, Any]] = []
    for chapter_id in chapter_ids:
        plans.extend(
            collect_chapter_queries(
                project, chapter_id, args.max_queries_per_chapter
            )
        )
    payload = {
        "schema_version": "1.0.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project": project_data.get("name"),
        "chapters": chapter_ids,
        "query_count": len(plans),
        "downloaded_candidates_are_selected": False,
        "queries": plans,
    }
    output = project / "assets" / "search-plan.json"
    write_json(output, payload)
    update_pipeline_stage(
        project,
        "asset_search",
        "planned",
        chapters=chapter_ids,
        queries=len(plans),
    )
    print(f"Asset search plan: {output}")
    print(f"Queries: {len(plans)}")

    if args.execute:
        update_pipeline_stage(project, "asset_search", "running")
        try:
            execute_searches(
                project,
                plans,
                limit=args.limit,
                download_first=args.download_first,
                continue_on_error=not args.fail_fast,
            )
        except Exception:
            update_pipeline_stage(project, "asset_search", "failed")
            raise
        payload["executed_at"] = datetime.now(timezone.utc).isoformat()
        payload["queries"] = plans
        write_json(output, payload)
        update_pipeline_stage(
            project,
            "asset_search",
            "completed",
            chapters=chapter_ids,
            queries=len(plans),
            downloaded_first=args.download_first,
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (LongformError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
