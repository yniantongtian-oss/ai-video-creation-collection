#!/usr/bin/env python3
"""Download model files required by a bundled ComfyUI workflow."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "workflows" / "models.json"
WORKFLOWS = (
    "wan22_t2v_4step.json",
    "wan22_i2v_4step.json",
    "wan22_long_video_3shot.json",
)


def existing_directory(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.is_dir():
        raise argparse.ArgumentTypeError(f"directory does not exist: {path}")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow", required=True, choices=WORKFLOWS)
    parser.add_argument(
        "--comfyui",
        required=True,
        type=existing_directory,
        help="path to the ComfyUI repository or installation directory",
    )
    parser.add_argument("--dry-run", action="store_true", help="print the plan without downloading")
    parser.add_argument("--force", action="store_true", help="replace existing destination files")
    parser.add_argument("--timeout", type=float, default=60.0, help="request timeout in seconds")
    return parser.parse_args()


def load_manifest() -> list[dict]:
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    entries = data.get("models")
    if not isinstance(entries, list):
        raise ValueError("workflows/models.json has no models array")
    return entries


def format_bytes(value: int | None) -> str:
    if value is None:
        return "unknown size"
    size = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TiB"


def remote_size(url: str, timeout: float) -> int | None:
    request = urllib.request.Request(
        url,
        method="HEAD",
        headers={"User-Agent": "ai-video-workflow-downloader/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            value = response.headers.get("Content-Length")
            return int(value) if value and value.isdigit() else None
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return None


def download(url: str, destination: Path, timeout: float) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=destination.name + ".",
        suffix=".part",
        dir=destination.parent,
        delete=False,
    ) as handle:
        temporary = Path(handle.name)

    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "ai-video-workflow-downloader/1.0"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response, temporary.open("wb") as output:
            shutil.copyfileobj(response, output, length=1024 * 1024)
        os.replace(temporary, destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def main() -> int:
    args = parse_args()
    model_root = args.comfyui / "models"
    entries = [
        entry
        for entry in load_manifest()
        if args.workflow in entry.get("workflows", [])
    ]

    if not entries:
        print(f"ERROR: no model entries found for {args.workflow}", file=sys.stderr)
        return 1

    print(f"Workflow: {args.workflow}")
    print(f"ComfyUI: {args.comfyui}")
    print(f"Files: {len(entries)}")

    failures = 0
    for entry in entries:
        destination = model_root / entry["directory"] / entry["filename"]
        if destination.exists() and not args.force:
            print(f"SKIP  {destination} (already exists)")
            continue

        size = remote_size(entry["url"], args.timeout) if args.dry_run else None
        print(f"{'PLAN' if args.dry_run else 'GET '}  {destination} ({format_bytes(size)})")
        if args.dry_run:
            continue

        try:
            download(entry["url"], destination, args.timeout)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            failures += 1
            print(f"ERROR {entry['filename']}: {exc}", file=sys.stderr)

    if failures:
        print(f"Download finished with {failures} failure(s).", file=sys.stderr)
        return 1

    print("Dry run complete. No files were changed." if args.dry_run else "Download complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
