#!/usr/bin/env python3
"""Run the long-form workflow by stage while preserving review gates and resume state."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Iterable

from longform_common import LongformError, load_project

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
NEEDS_ASSET_REVIEW = 10


def run_script(
    name: str,
    arguments: list[str],
    *,
    allowed_codes: Iterable[int] = (0,),
) -> int:
    script = SCRIPTS / name
    if not script.is_file():
        raise LongformError(f"missing pipeline script: {script}")
    command = [sys.executable, str(script), *arguments]
    print("$ " + " ".join(command))
    result = subprocess.run(command, check=False)
    if result.returncode not in set(allowed_codes):
        raise LongformError(
            f"stage failed with exit code {result.returncode}: {name}"
        )
    return result.returncode


def manifest_counts(project: Path) -> tuple[int, int]:
    path = project / "manifests" / "assets.jsonl"
    candidates = 0
    selected = 0
    if not path.is_file():
        return candidates, selected
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            candidates += 1
            if bool(item.get("selected", False)):
                selected += 1
    return candidates, selected


def chapter_arguments(chapters: list[str] | None) -> list[str]:
    values: list[str] = []
    for chapter in chapters or []:
        values.extend(["--chapter", chapter])
    return values


def run_research(args: argparse.Namespace, project: Path) -> None:
    chunks = project / "research" / "chunks.jsonl"
    if args.input:
        ingest_args = ["--project", str(project)]
        for value in args.input:
            ingest_args.extend(["--input", str(value)])
        if args.reset_corpus:
            ingest_args.append("--reset-index")
        run_script("ingest_longform_corpus.py", ingest_args)
    elif not chunks.is_file() or not chunks.read_text(encoding="utf-8").strip():
        raise LongformError(
            "research corpus is empty; provide --input or put documents in research/inbox"
        )
    pipeline_args = ["--project", str(project), "run"]
    pipeline_args.extend(chapter_arguments(args.chapter))
    if args.force:
        pipeline_args.append("--force")
    run_script("longform_pipeline.py", pipeline_args)


def run_assets(args: argparse.Namespace, project: Path) -> None:
    plan_args = [
        "--project",
        str(project),
        "--max-queries-per-chapter",
        str(args.max_queries_per_chapter),
        "--limit",
        str(args.search_limit),
    ]
    plan_args.extend(chapter_arguments(args.chapter))
    if args.execute_search:
        plan_args.append("--execute")
        plan_args.extend(["--download-first", str(args.download_first)])
    if args.fail_fast:
        plan_args.append("--fail-fast")
    run_script("build_longform_asset_plan.py", plan_args)


def print_asset_review_gate(project: Path, candidates: int, selected: int) -> None:
    manifest = project / "manifests" / "assets.jsonl"
    print("LONGFORM_NEEDS_ASSET_REVIEW")
    print(f"MANIFEST={manifest}")
    print(f"CANDIDATES={candidates}")
    print(f"SELECTED={selected}")
    print(
        "List candidates: python scripts/media_asset_manifest.py list "
        f"--manifest \"{manifest}\" --candidates"
    )
    print(
        "Approve one asset: python scripts/media_asset_manifest.py set-selected "
        f"--manifest \"{manifest}\" --id <asset-id> --value true"
    )
    print(
        "After reviewing enough assets, rerun: python scripts/run_longform_project.py "
        f"--project \"{project}\" produce"
    )


def run_production(args: argparse.Namespace, project: Path, project_data: dict) -> None:
    candidates, selected = manifest_counts(project)
    minimum = int(
        project_data.get("quality_gates", {}).get(
            "minimum_selected_assets_per_chapter", 8
        )
    )
    chapter_count = len(args.chapter or project_data.get("chapters", []))
    recommended = minimum if args.chapter else minimum * min(chapter_count, 3)
    if selected < minimum:
        print_asset_review_gate(project, candidates, selected)
        raise SystemExit(NEEDS_ASSET_REVIEW)
    if selected < recommended:
        print(
            f"Warning: only {selected} assets are selected; "
            f"{recommended} or more is recommended for variety.",
            file=sys.stderr,
        )

    preflight_args = ["--project", str(project), "--stage", "assets"]
    run_script("longform_preflight.py", preflight_args)

    narration_args = ["--project", str(project)]
    narration_args.extend(chapter_arguments(args.chapter))
    if args.force:
        narration_args.append("--force")
    run_script("render_longform_narration.py", narration_args)

    timeline_args = ["--project", str(project)]
    timeline_args.extend(chapter_arguments(args.chapter))
    if args.allow_placeholders:
        timeline_args.append("--allow-placeholders")
    run_script("build_longform_timeline.py", timeline_args)

    render_args = ["--project", str(project)]
    render_args.extend(chapter_arguments(args.chapter))
    if args.allow_placeholders:
        render_args.append("--allow-placeholders")
    if args.burn_subtitles:
        render_args.append("--burn-subtitles")
    if args.bgm:
        render_args.extend(["--bgm", str(args.bgm)])
    if args.force:
        render_args.append("--force")
    run_script("render_longform_chapters.py", render_args)

    if args.chapter:
        print("Selected chapters rendered. Final assembly was skipped because --chapter was used.")
        return
    run_script(
        "longform_preflight.py",
        ["--project", str(project), "--stage", "final"],
    )
    assembly_args = ["--project", str(project)]
    if args.force:
        assembly_args.append("--force")
    run_script("assemble_longform_video.py", assembly_args)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument(
        "mode", choices=["research", "assets", "produce", "all", "status"]
    )
    parser.add_argument("--input", type=Path, action="append")
    parser.add_argument("--chapter", action="append")
    parser.add_argument("--reset-corpus", action="store_true")
    parser.add_argument("--execute-search", action="store_true")
    parser.add_argument("--download-first", type=int, default=1)
    parser.add_argument("--search-limit", type=int, default=8)
    parser.add_argument("--max-queries-per-chapter", type=int, default=12)
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--allow-placeholders", action="store_true")
    parser.add_argument("--burn-subtitles", action="store_true")
    parser.add_argument("--bgm", type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if not 0 <= args.download_first <= args.search_limit:
        parser.error("--download-first must be between 0 and --search-limit")
    return args


def main() -> int:
    args = parse_args()
    project, project_data = load_project(args.project)
    if args.mode == "status":
        run_script("longform_pipeline.py", ["--project", str(project), "status"])
        run_script(
            "longform_preflight.py",
            ["--project", str(project), "--stage", "setup"],
            allowed_codes=(0, 1),
        )
        return 0
    if args.mode in {"research", "all"}:
        run_research(args, project)
    if args.mode in {"assets", "all"}:
        run_assets(args, project)
    if args.mode in {"produce", "all"}:
        run_production(args, project, project_data)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (LongformError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
