#!/usr/bin/env python3
"""Ingest one public or user-authorized URL into a project with provenance.

This wrapper deliberately does not accept cookie files, passwords, DRM options,
paywall bypasses, or browser-profile extraction. Use it only for sources that are
publicly downloadable or that the user is authorized to reuse.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / "tools" / "web-media" / ".venv"
ALLOWED_RIGHTS = {
    "public-domain",
    "cc0",
    "cc-by",
    "cc-by-sa",
    "provider-licensed",
    "user-owned",
    "permission-granted",
    "unknown",
    "restricted",
}


class IngestError(RuntimeError):
    pass


def executable(name: str) -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / f"{name}.exe"
    return VENV / "bin" / name


def safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip(".-")
    return value[:100] or "asset"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    print("$ " + " ".join(command))
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        text=True,
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        detail = ""
        if capture:
            output = (result.stdout or "") + (result.stderr or "")
            detail = "\n" + "\n".join(output.splitlines()[-30:]) if output else ""
        raise IngestError(
            f"command failed with exit code {result.returncode}: {' '.join(command)}{detail}"
        )
    return result


def append_manifest(manifest: Path, entry: dict[str, Any]) -> None:
    manifest.parent.mkdir(parents=True, exist_ok=True)
    with manifest.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")


def relative_to_project(path: Path, project: Path) -> str:
    try:
        return path.resolve().relative_to(project.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def manifest_entry(
    args: argparse.Namespace,
    *,
    asset_id: str,
    kind: str,
    local_path: Path,
    notes: str = "",
) -> dict[str, Any]:
    host = urllib.parse.urlparse(args.url).netloc.lower()
    return {
        "id": asset_id,
        "kind": kind,
        "local_path": relative_to_project(local_path, args.project),
        "source_url": args.url,
        "provider": args.provider or host,
        "title": args.title,
        "creator": args.creator,
        "license": args.license,
        "license_url": args.license_url,
        "rights_status": args.rights_status,
        "attribution": args.attribution,
        "permission_note": args.permission_note,
        "selected": args.selected,
        "sha256": sha256(local_path),
        "size_bytes": local_path.stat().st_size,
        "acquired_at": datetime.now(timezone.utc).isoformat(),
        "notes": notes,
    }


def ingest_document(args: argparse.Namespace) -> list[tuple[str, str, Path, str]]:
    tool = executable("trafilatura")
    if not tool.is_file():
        raise IngestError(
            "Trafilatura is not installed; run python scripts/install_web_media_stack.py"
        )
    destination = args.project / "research" / "documents" / f"{safe_name(args.asset_id)}.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    result = run(
        [
            str(tool),
            "--URL",
            args.url,
            "--markdown",
            "--with-metadata",
            "--links",
            "--no-comments",
        ],
        capture=True,
    )
    content = (result.stdout or "").strip()
    if not content:
        raise IngestError("Trafilatura returned no readable document content")
    header = (
        f"<!-- source: {args.url} -->\n"
        f"<!-- acquired_at: {datetime.now(timezone.utc).isoformat()} -->\n\n"
    )
    destination.write_text(header + content + "\n", encoding="utf-8")
    return [(args.asset_id, "document", destination, "Readable extraction; facts still require source verification.")]


def media_candidates(directory: Path, before: set[Path]) -> list[Path]:
    ignored = {
        ".json",
        ".description",
        ".srt",
        ".vtt",
        ".ass",
        ".lrc",
        ".part",
        ".ytdl",
    }
    files = [
        path
        for path in directory.rglob("*")
        if path.is_file() and path.resolve() not in before and path.suffix.lower() not in ignored
    ]
    return sorted(files)


def ingest_video(args: argparse.Namespace) -> list[tuple[str, str, Path, str]]:
    tool = executable("yt-dlp")
    if not tool.is_file():
        raise IngestError(
            "yt-dlp is not installed; run python scripts/install_web_media_stack.py"
        )
    directory = args.project / "assets" / "videos"
    directory.mkdir(parents=True, exist_ok=True)
    before = {path.resolve() for path in directory.rglob("*") if path.is_file()}
    template = directory / f"{safe_name(args.asset_id)}-%(id)s.%(ext)s"
    command = [
        str(tool),
        "--no-playlist",
        "--restrict-filenames",
        "--write-info-json",
        "--write-thumbnail",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs",
        "zh.*,en.*",
        "--merge-output-format",
        "mp4",
        "-o",
        str(template),
        args.url,
    ]
    run(command)
    files = media_candidates(directory, before)
    videos = [path for path in files if path.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov", ".m4v"}]
    if not videos:
        raise IngestError("yt-dlp completed without producing a video file")
    return [
        (
            args.asset_id if len(videos) == 1 else f"{args.asset_id}-{index:03d}",
            "video",
            path,
            "Downloaded from a public or user-authorized URL with yt-dlp; platform and copyright terms still apply.",
        )
        for index, path in enumerate(videos, 1)
    ]


def ingest_gallery(args: argparse.Namespace) -> list[tuple[str, str, Path, str]]:
    tool = executable("gallery-dl")
    if not tool.is_file():
        raise IngestError(
            "gallery-dl is not installed; run python scripts/install_web_media_stack.py"
        )
    directory = args.project / "assets" / "images"
    directory.mkdir(parents=True, exist_ok=True)
    before = {path.resolve() for path in directory.rglob("*") if path.is_file()}
    run([str(tool), "--dest", str(directory), args.url])
    files = media_candidates(directory, before)
    images = [
        path
        for path in files
        if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".svg"}
    ]
    if not images:
        raise IngestError("gallery-dl completed without producing image files")
    return [
        (
            f"{args.asset_id}-{index:03d}",
            "image",
            path,
            "Downloaded from a public or user-authorized gallery with gallery-dl; each image requires rights review.",
        )
        for index, path in enumerate(images, 1)
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--type", choices=["document", "video", "gallery"], required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--asset-id", required=True)
    parser.add_argument("--title", default="")
    parser.add_argument("--creator", default="")
    parser.add_argument("--provider", default="")
    parser.add_argument("--license", required=True)
    parser.add_argument("--license-url", default="")
    parser.add_argument("--rights-status", choices=sorted(ALLOWED_RIGHTS), required=True)
    parser.add_argument("--attribution", default="")
    parser.add_argument("--permission-note", default="")
    parser.add_argument("--selected", action="store_true")
    args = parser.parse_args()
    parsed = urllib.parse.urlparse(args.url)
    if parsed.scheme != "https" or not parsed.netloc:
        parser.error("--url must be a public HTTPS URL")
    args.project = args.project.expanduser().resolve()
    if not (args.project / "project.json").is_file():
        parser.error("--project must be a workspace created by scaffold_web_media_project.py")
    args.asset_id = safe_name(args.asset_id)
    if args.rights_status == "permission-granted" and not args.permission_note.strip():
        parser.error("permission-granted requires --permission-note")
    if args.selected and args.rights_status in {"unknown", "restricted"}:
        parser.error("unknown or restricted assets cannot be selected")
    return args


def main() -> int:
    args = parse_args()
    manifest = args.project / "manifests" / "assets.jsonl"
    handlers = {
        "document": ingest_document,
        "video": ingest_video,
        "gallery": ingest_gallery,
    }
    try:
        results = handlers[args.type](args)
        for asset_id, kind, local_path, notes in results:
            append_manifest(
                manifest,
                manifest_entry(
                    args,
                    asset_id=asset_id,
                    kind=kind,
                    local_path=local_path,
                    notes=notes,
                ),
            )
            print(f"Ingested {asset_id}: {local_path}")
        print(f"Manifest: {manifest}")
        return 0
    except (IngestError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
