#!/usr/bin/env python3
"""Download the official Auto-Editor binary for the current platform.

The script uses only Python's standard library and downloads release assets from
WyattBlue/auto-editor on GitHub. It does not modify the user's PATH or overwrite
an existing binary unless --force is supplied.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import stat
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

REPOSITORY = "WyattBlue/auto-editor"
API_ROOT = f"https://api.github.com/repos/{REPOSITORY}/releases"
USER_AGENT = "ai-video-creation-collection-auto-editor-installer/1.0"


def _asset_name(system: str, machine: str) -> str:
    system_key = system.lower()
    machine_key = machine.lower().replace(" ", "")

    aliases = {
        "amd64": "x86_64",
        "x64": "x86_64",
        "x86-64": "x86_64",
        "arm64": "aarch64",
        "armv7l": "armv7",
        "armv7": "armv7",
    }
    machine_key = aliases.get(machine_key, machine_key)

    matrix = {
        ("linux", "x86_64"): "auto-editor-linux-x86_64",
        ("linux", "aarch64"): "auto-editor-linux-aarch64",
        ("linux", "armv7"): "auto-editor-linux-armv7",
        ("darwin", "x86_64"): "auto-editor-macos-x86_64",
        ("darwin", "aarch64"): "auto-editor-macos-arm64",
        ("windows", "x86_64"): "auto-editor-windows-x86_64.exe",
        ("windows", "aarch64"): "auto-editor-windows-aarch64.exe",
    }

    try:
        return matrix[(system_key, machine_key)]
    except KeyError as exc:
        supported = ", ".join(f"{s}/{m}" for s, m in sorted(matrix))
        raise RuntimeError(
            f"Unsupported platform: {system}/{machine}. Supported: {supported}"
        ) from exc


def _request_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Unable to reach GitHub: {exc.reason}") from exc


def _release(version: str | None) -> dict[str, Any]:
    if version:
        tag = urllib.parse.quote(version, safe="")
        return _request_json(f"{API_ROOT}/tags/{tag}")
    return _request_json(f"{API_ROOT}/latest")


def _download(url: str, destination: Path, expected_size: int | None) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    destination.parent.mkdir(parents=True, exist_ok=True)

    temp_path: Path | None = None
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            with tempfile.NamedTemporaryFile(
                mode="wb", delete=False, dir=destination.parent, prefix=".download-"
            ) as temp_file:
                temp_path = Path(temp_file.name)
                downloaded = 0
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    temp_file.write(chunk)
                    downloaded += len(chunk)
                    print(
                        f"\rDownloaded {downloaded / (1024 * 1024):.1f} MiB",
                        end="",
                        flush=True,
                    )
        print()

        if expected_size is not None and temp_path.stat().st_size != expected_size:
            raise RuntimeError(
                "Downloaded size does not match the GitHub release metadata: "
                f"expected {expected_size} bytes, got {temp_path.stat().st_size} bytes"
            )

        os.replace(temp_path, destination)
        temp_path = None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Binary download failed: {exc.reason}") from exc
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()


def _make_executable(path: Path) -> None:
    if os.name != "nt":
        mode = path.stat().st_mode
        path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _verify(binary: Path) -> None:
    try:
        result = subprocess.run(
            [str(binary), "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=45,
            check=False,
        )
    except OSError as exc:
        raise RuntimeError(f"Downloaded binary could not be started: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Downloaded binary timed out during verification") from exc

    if result.returncode != 0:
        excerpt = result.stdout[-2000:] if result.stdout else "(no output)"
        raise RuntimeError(
            f"Downloaded binary returned exit code {result.returncode}. Output:\n{excerpt}"
        )


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    default_dir = repo_root / "tools" / "auto-editor" / "bin"

    parser = argparse.ArgumentParser(
        description="Download the official Auto-Editor release binary for this computer."
    )
    parser.add_argument(
        "--version",
        help="Release tag to download. Omit to use the latest GitHub release.",
    )
    parser.add_argument(
        "--install-dir",
        type=Path,
        default=default_dir,
        help=f"Destination directory (default: {default_dir})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing binary.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the selected release asset without downloading it.",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Do not run the downloaded binary with --help after installation.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    system = platform.system()
    machine = platform.machine()
    asset_name = _asset_name(system, machine)
    executable_name = "auto-editor.exe" if system.lower() == "windows" else "auto-editor"
    install_dir = args.install_dir.expanduser().resolve()
    destination = install_dir / executable_name

    release = _release(args.version)
    tag_name = str(release.get("tag_name", "unknown"))
    assets = release.get("assets") or []
    asset = next((item for item in assets if item.get("name") == asset_name), None)
    if asset is None:
        available = ", ".join(str(item.get("name")) for item in assets) or "none"
        raise RuntimeError(
            f"Release {tag_name} has no asset named {asset_name}. Available: {available}"
        )

    download_url = asset.get("browser_download_url")
    if not isinstance(download_url, str) or not download_url.startswith("https://"):
        raise RuntimeError("The selected GitHub release asset has no valid download URL")

    expected_size = asset.get("size") if isinstance(asset.get("size"), int) else None
    print(f"Platform: {system}/{machine}")
    print(f"Release: {tag_name}")
    print(f"Asset: {asset_name}")
    print(f"Destination: {destination}")

    if args.dry_run:
        print(f"Download URL: {download_url}")
        return 0

    if destination.exists() and not args.force:
        print("A binary already exists. Use --force to replace it.")
        if not args.no_verify:
            _verify(destination)
            print("Existing binary verification passed.")
        return 0

    _download(download_url, destination, expected_size)
    _make_executable(destination)

    metadata = {
        "repository": REPOSITORY,
        "tag_name": tag_name,
        "asset_name": asset_name,
        "download_url": download_url,
        "size": expected_size,
        "installed_path": str(destination),
    }
    install_dir.mkdir(parents=True, exist_ok=True)
    (install_dir.parent / "install.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    if not args.no_verify:
        _verify(destination)
        print("Binary verification passed.")

    print("Auto-Editor is ready.")
    print(f'Run: "{destination}" --help')
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
