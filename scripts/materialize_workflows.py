#!/usr/bin/env python3
"""Expand compressed workflow sources into standard ComfyUI JSON files."""

from __future__ import annotations

import argparse
import gzip
import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / "workflows"
SOURCES = {
    WORKFLOW_DIR / "wan22_long_video_3shot.json.gz":
        WORKFLOW_DIR / "wan22_long_video_3shot.json",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace an existing JSON file when its content differs",
    )
    return parser.parse_args()


def read_source(path: Path) -> bytes:
    try:
        payload = gzip.decompress(path.read_bytes())
    except FileNotFoundError:
        raise SystemExit(f"ERROR: missing compressed workflow: {path.relative_to(ROOT)}")
    except gzip.BadGzipFile as exc:
        raise SystemExit(f"ERROR: invalid gzip source: {path.relative_to(ROOT)}") from exc

    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"ERROR: decompressed workflow is not valid UTF-8 JSON: {path.name}") from exc

    if not isinstance(data, dict) or not isinstance(data.get("nodes"), list):
        raise SystemExit(f"ERROR: decompressed workflow has an invalid structure: {path.name}")
    return payload


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=path.parent,
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        handle.write(payload)
    try:
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def main() -> int:
    args = parse_args()
    changed = 0

    for source, destination in SOURCES.items():
        payload = read_source(source)
        if destination.exists():
            current = destination.read_bytes()
            if current == payload:
                print(f"OK    {destination.relative_to(ROOT)}")
                continue
            if not args.force:
                print(
                    f"ERROR: {destination.relative_to(ROOT)} already exists with different content; "
                    "use --force only when replacement is intentional."
                )
                return 1

        atomic_write(destination, payload)
        changed += 1
        print(f"WRITE {destination.relative_to(ROOT)}")

    print(f"Materialization complete: {changed} file(s) written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
