#!/usr/bin/env python3
"""Install the pinned web research and AI video production stack.

Profiles:
- core: yt-dlp, gallery-dl, and Trafilatura in one isolated uv environment.
- creator: core plus MoneyPrinterTurbo.
- full: creator plus NarratoAI and VideoLingo.

Third-party applications are cloned into ignored tool directories and checked out
at commits recorded in tools/web-media-stack.lock.json. Existing dirty clones are
never overwritten.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "tools" / "web-media-stack.lock.json"
TOOLS_ROOT = ROOT / "tools" / "web-media"
VENV_DIR = TOOLS_ROOT / ".venv"
APPS_DIR = TOOLS_ROOT / "apps"
ENV_TEMPLATE = ROOT / "config" / "web-media.env.example"
ENV_PATH = TOOLS_ROOT / ".env"
INSTALL_RECORD = TOOLS_ROOT / "install.json"
PROFILE_LEVEL = {"core": 0, "creator": 1, "full": 2}
APP_DIR_NAMES = {
    "moneyprinterturbo": "MoneyPrinterTurbo",
    "narratoai": "NarratoAI",
    "videolingo": "VideoLingo",
}


class InstallError(RuntimeError):
    """A concise and actionable installation error."""


def run(
    command: list[str],
    *,
    cwd: Path | None = None,
    capture: bool = False,
    check: bool = True,
    dry_run: bool = False,
) -> subprocess.CompletedProcess[str]:
    printable = " ".join(command)
    print(f"$ {printable}")
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
    if check and result.returncode != 0:
        detail = ""
        if capture:
            detail = (result.stdout or "") + (result.stderr or "")
            detail = "\n" + "\n".join(detail.splitlines()[-30:]) if detail else ""
        raise InstallError(
            f"command failed with exit code {result.returncode}: {printable}{detail}"
        )
    return result


def load_lock() -> dict[str, Any]:
    try:
        data = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise InstallError(f"missing lock file: {LOCK_PATH}") from exc
    except json.JSONDecodeError as exc:
        raise InstallError(f"invalid lock file JSON: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("core"), list):
        raise InstallError("lock file must contain core and apps arrays")
    if not isinstance(data.get("apps"), list):
        raise InstallError("lock file must contain an apps array")
    return data


def executable_in_venv(name: str) -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / f"{name}.exe"
    return VENV_DIR / "bin" / name


def python_in_venv() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def require_program(name: str) -> str:
    path = shutil.which(name)
    if not path:
        if name == "uv":
            raise InstallError(
                "uv is required. Install it from the official Astral documentation, "
                "reopen the terminal, and rerun this script."
            )
        raise InstallError(f"required program not found in PATH: {name}")
    return path


def program_for_plan(name: str, *, dry_run: bool) -> str:
    """Resolve an executable, but allow a side-effect-free dry-run without it."""
    if dry_run:
        return shutil.which(name) or name
    return require_program(name)


def normalize_repo_url(url: str) -> str:
    value = url.rstrip("/")
    return value[:-4] if value.endswith(".git") else value


def install_core(lock: dict[str, Any], *, dry_run: bool) -> list[dict[str, str]]:
    uv = program_for_plan("uv", dry_run=dry_run)
    if not dry_run:
        TOOLS_ROOT.mkdir(parents=True, exist_ok=True)
    if not VENV_DIR.exists():
        run([uv, "venv", "--python", "3.11", str(VENV_DIR)], dry_run=dry_run)

    python_path = python_in_venv()
    specs: list[str] = []
    records: list[dict[str, str]] = []
    for item in lock["core"]:
        package_id = str(item["id"])
        repository = normalize_repo_url(str(item["repository"]))
        ref = str(item["ref"])
        specs.append(f"{package_id} @ git+{repository}.git@{ref}")
        records.append(
            {
                "id": package_id,
                "repository": repository,
                "ref": ref,
                "license": str(item.get("license", "unknown")),
            }
        )

    run(
        [uv, "pip", "install", "--python", str(python_path), "--upgrade", *specs],
        dry_run=dry_run,
    )

    if not dry_run:
        probes = [
            ("yt-dlp", [str(executable_in_venv("yt-dlp")), "--version"]),
            ("gallery-dl", [str(executable_in_venv("gallery-dl")), "--version"]),
            ("trafilatura", [str(executable_in_venv("trafilatura")), "--version"]),
        ]
        for label, command in probes:
            result = run(command, capture=True)
            first_line = next(
                (line.strip() for line in (result.stdout or "").splitlines() if line.strip()),
                "ready",
            )
            print(f"[OK] {label}: {first_line}")
    return records


def ensure_clean_clone(
    destination: Path, repository: str, ref: str, *, dry_run: bool
) -> None:
    git = program_for_plan("git", dry_run=dry_run)
    repository = normalize_repo_url(repository)
    if destination.exists() and not (destination / ".git").is_dir():
        if any(destination.iterdir()):
            raise InstallError(
                f"destination exists but is not a Git clone: {destination}"
            )
        if not dry_run:
            destination.rmdir()

    if not destination.exists():
        if not dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
        run(
            [
                git,
                "clone",
                "--filter=blob:none",
                "--no-checkout",
                f"{repository}.git",
                str(destination),
            ],
            dry_run=dry_run,
        )

    if dry_run:
        print(f"Would check out {repository}@{ref} in {destination}")
        return

    remote = run(
        [git, "remote", "get-url", "origin"],
        cwd=destination,
        capture=True,
    ).stdout.strip()
    if normalize_repo_url(remote) != repository:
        raise InstallError(
            f"existing clone has an unexpected origin: {destination} -> {remote}"
        )

    dirty = run(
        [git, "status", "--porcelain"],
        cwd=destination,
        capture=True,
    ).stdout.strip()
    if dirty:
        raise InstallError(
            f"existing clone has local changes and will not be overwritten: {destination}"
        )

    run([git, "fetch", "--depth", "1", "origin", ref], cwd=destination)
    run([git, "checkout", "--detach", "FETCH_HEAD"], cwd=destination)
    actual = run([git, "rev-parse", "HEAD"], cwd=destination, capture=True).stdout.strip()
    if actual != ref:
        raise InstallError(
            f"checked-out commit mismatch for {destination}: expected {ref}, got {actual}"
        )
    print(f"[OK] {destination.name}: {actual}")


def install_apps(
    lock: dict[str, Any], profile: str, *, dry_run: bool
) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    requested_level = PROFILE_LEVEL[profile]
    for item in lock["apps"]:
        item_profile = str(item.get("profile", "full"))
        if PROFILE_LEVEL.get(item_profile, 99) > requested_level:
            continue
        app_id = str(item["id"])
        repository = str(item["repository"])
        ref = str(item["ref"])
        destination = APPS_DIR / APP_DIR_NAMES.get(app_id, app_id)
        ensure_clean_clone(destination, repository, ref, dry_run=dry_run)
        selected.append(
            {
                "id": app_id,
                "repository": normalize_repo_url(repository),
                "ref": ref,
                "license": str(item.get("license", "unknown")),
                "path": str(destination),
            }
        )
    return selected


def ensure_env(*, dry_run: bool) -> None:
    if ENV_PATH.exists():
        print(f"Using existing environment file: {ENV_PATH}")
        return
    if not ENV_TEMPLATE.is_file():
        raise InstallError(f"missing environment template: {ENV_TEMPLATE}")
    print(f"Creating local environment template: {ENV_PATH}")
    if not dry_run:
        ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ENV_TEMPLATE, ENV_PATH)


def write_install_record(
    *, profile: str, core: list[dict[str, str]], apps: list[dict[str, str]], dry_run: bool
) -> None:
    record = {
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "profile": profile,
        "lock_file": str(LOCK_PATH),
        "venv": str(VENV_DIR),
        "environment_file": str(ENV_PATH),
        "core": core,
        "apps": apps,
    }
    if dry_run:
        print(json.dumps(record, ensure_ascii=False, indent=2))
        return
    INSTALL_RECORD.parent.mkdir(parents=True, exist_ok=True)
    INSTALL_RECORD.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILE_LEVEL, key=PROFILE_LEVEL.get),
        default="creator",
        help="Installation profile (default: creator).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show commands and selected revisions without changing the filesystem.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    lock = load_lock()
    print(f"Installing web media stack profile: {args.profile}")
    core = install_core(lock, dry_run=args.dry_run)
    apps = install_apps(lock, args.profile, dry_run=args.dry_run)
    ensure_env(dry_run=args.dry_run)
    write_install_record(
        profile=args.profile,
        core=core,
        apps=apps,
        dry_run=args.dry_run,
    )
    print("Web media stack is ready.")
    print(f"Environment file: {ENV_PATH}")
    print("Do not commit real API keys.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (InstallError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
