#!/usr/bin/env python3
"""Configure pinned web media applications after downloading their source.

This step can install large Python environments. It is intentionally separate
from scripts/install_web_media_stack.py so a creator-only setup does not
implicitly install WhisperX, PyTorch, Demucs, or other heavy optional packages.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "tools" / "web-media-stack.lock.json"
APPS_DIR = ROOT / "tools" / "web-media" / "apps"
APP_DIR_NAMES = {
    "moneyprinterturbo": "MoneyPrinterTurbo",
    "narratoai": "NarratoAI",
    "videolingo": "VideoLingo",
}
SUPPORTED_APPS = tuple(APP_DIR_NAMES)


class ConfigureError(RuntimeError):
    pass


def run(
    command: list[str],
    *,
    cwd: Path | None = None,
    capture: bool = False,
    dry_run: bool = False,
) -> subprocess.CompletedProcess[str]:
    print("$ " + " ".join(command))
    if dry_run:
        return subprocess.CompletedProcess(command, 0, "", "")
    result = subprocess.run(
        command,
        cwd=cwd,
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
        raise ConfigureError(
            f"command failed with exit code {result.returncode}: {' '.join(command)}{detail}"
        )
    return result


def program(name: str, *, dry_run: bool) -> str:
    found = shutil.which(name)
    if found:
        return found
    if dry_run:
        return name
    raise ConfigureError(f"required program not found in PATH: {name}")


def load_apps() -> dict[str, dict[str, Any]]:
    try:
        data = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigureError(f"missing lock file: {LOCK_PATH}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigureError(f"invalid lock file JSON: {exc}") from exc
    apps = data.get("apps")
    if not isinstance(apps, list):
        raise ConfigureError("lock file has no apps array")
    result: dict[str, dict[str, Any]] = {}
    for item in apps:
        if isinstance(item, dict) and item.get("id") in APP_DIR_NAMES:
            result[str(item["id"])] = item
    missing = set(APP_DIR_NAMES) - set(result)
    if missing:
        raise ConfigureError(f"lock file is missing apps: {', '.join(sorted(missing))}")
    return result


def verify_clone(app_id: str, item: dict[str, Any], *, dry_run: bool) -> Path:
    destination = APPS_DIR / APP_DIR_NAMES[app_id]
    expected_ref = str(item["ref"])
    if dry_run and not destination.exists():
        print(f"Would verify {destination} at {expected_ref}")
        return destination
    if not (destination / ".git").is_dir():
        raise ConfigureError(
            f"missing pinned clone for {app_id}: run "
            "python scripts/install_web_media_stack.py --profile full first"
        )
    git = program("git", dry_run=dry_run)
    actual = run(
        [git, "rev-parse", "HEAD"], cwd=destination, capture=True, dry_run=dry_run
    ).stdout.strip()
    if not dry_run and actual != expected_ref:
        raise ConfigureError(
            f"{app_id} is at {actual}, expected locked commit {expected_ref}; "
            "rerun install_web_media_stack.py before configuring"
        )
    if not dry_run:
        dirty = run(
            [git, "status", "--porcelain"], cwd=destination, capture=True
        ).stdout.strip()
        if dirty:
            raise ConfigureError(
                f"{app_id} has uncommitted source changes; refusing to run setup: {destination}"
            )
    return destination


def copy_config_if_missing(
    directory: Path, source_name: str, target_name: str, *, dry_run: bool
) -> None:
    source = directory / source_name
    target = directory / target_name
    if target.exists():
        print(f"Using existing configuration: {target}")
        return
    if dry_run and not source.exists():
        print(f"Would copy {source} to {target}")
        return
    if not source.is_file():
        raise ConfigureError(f"missing configuration template: {source}")
    print(f"Creating configuration: {target}")
    if not dry_run:
        shutil.copy2(source, target)


def configure_moneyprinterturbo(directory: Path, *, dry_run: bool) -> None:
    uv = program("uv", dry_run=dry_run)
    run([uv, "sync", "--frozen"], cwd=directory, dry_run=dry_run)
    copy_config_if_missing(
        directory, "config.example.toml", "config.toml", dry_run=dry_run
    )
    print("MoneyPrinterTurbo runtime is configured.")
    print("Use skills/moneyprinterturbo-video to generate a finished video.")


def configure_narratoai(directory: Path, *, dry_run: bool) -> None:
    uv = program("uv", dry_run=dry_run)
    run([uv, "sync"], cwd=directory, dry_run=dry_run)
    copy_config_if_missing(
        directory, "config.example.toml", "config.toml", dry_run=dry_run
    )
    print("NarratoAI runtime is configured.")
    print("Start with: uv run streamlit run webui.py --server.maxUploadSize=2048")


def configure_videolingo(
    directory: Path, *, dry_run: bool, include_demucs: bool
) -> None:
    setup_script = directory / "setup_env.py"
    if not dry_run and not setup_script.is_file():
        raise ConfigureError(f"missing VideoLingo setup script: {setup_script}")
    command = [sys.executable, str(setup_script), "--yes"]
    if not include_demucs:
        command.append("--skip-demucs")
    run(command, cwd=directory, dry_run=dry_run)
    print("VideoLingo runtime is configured.")
    if os.name == "nt":
        print("Start with: OneKeyStart.bat")
    else:
        print("Start with: .venv/bin/streamlit run st.py")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--app",
        choices=["all", *SUPPORTED_APPS],
        default="all",
        help="Application to configure (default: all).",
    )
    parser.add_argument(
        "--include-demucs",
        action="store_true",
        help="Install VideoLingo's optional Demucs dependency.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the verified setup commands without changing files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    apps = load_apps()
    selected = list(SUPPORTED_APPS) if args.app == "all" else [args.app]
    handlers = {
        "moneyprinterturbo": lambda path: configure_moneyprinterturbo(
            path, dry_run=args.dry_run
        ),
        "narratoai": lambda path: configure_narratoai(path, dry_run=args.dry_run),
        "videolingo": lambda path: configure_videolingo(
            path,
            dry_run=args.dry_run,
            include_demucs=args.include_demucs,
        ),
    }
    for app_id in selected:
        print(f"\nConfiguring {app_id}")
        directory = verify_clone(app_id, apps[app_id], dry_run=args.dry_run)
        handlers[app_id](directory)
    print("\nSelected web media applications are configured.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ConfigureError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
