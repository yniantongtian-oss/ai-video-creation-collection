#!/usr/bin/env python3
"""Check whether the repository's video-editing tools are ready to use."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _local_auto_editor() -> Path:
    name = "auto-editor.exe" if os.name == "nt" else "auto-editor"
    return _repo_root() / "tools" / "auto-editor" / "bin" / name


def _resolve(command: str) -> str | None:
    if command == "auto-editor":
        local = _local_auto_editor()
        if local.is_file():
            return str(local)
    return shutil.which(command)


def _probe(command: str, args: list[str]) -> dict[str, Any]:
    path = _resolve(command)
    if not path:
        return {
            "name": command,
            "status": "missing",
            "path": None,
            "summary": "not found",
        }

    try:
        result = subprocess.run(
            [path, *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "name": command,
            "status": "error",
            "path": path,
            "summary": str(exc),
        }

    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    summary = lines[0] if lines else f"exit code {result.returncode}"
    return {
        "name": command,
        "status": "ready" if result.returncode == 0 else "error",
        "path": path,
        "summary": summary,
        "returncode": result.returncode,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of a human-readable report.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results = [
        _probe("auto-editor", ["--help"]),
        _probe("ffmpeg", ["-version"]),
        _probe("ffprobe", ["-version"]),
    ]

    required_ready = results[0]["status"] == "ready"
    report = {
        "ready": required_ready,
        "required": ["auto-editor"],
        "optional": ["ffmpeg", "ffprobe"],
        "tools": results,
        "notes": [
            "Auto-Editor is required for the imported editing Skills.",
            "FFmpeg and ffprobe are optional command-line helpers; the official Auto-Editor binary includes the media components it needs.",
            "Speech transcription additionally needs a compatible Whisper or Parakeet model, unless the supported Apple backend is used.",
        ],
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("Video editing environment check")
        print("=" * 32)
        for item in results:
            marker = "OK" if item["status"] == "ready" else "--"
            print(f"[{marker}] {item['name']}: {item['summary']}")
            if item["path"]:
                print(f"     {item['path']}")
        print()
        if required_ready:
            print("Required editor is ready.")
        else:
            print("Auto-Editor is missing or failed to start.")
            print("Install it with: python scripts/install_auto_editor.py")

    return 0 if required_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
