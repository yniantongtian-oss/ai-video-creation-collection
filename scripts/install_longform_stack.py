#!/usr/bin/env python3
"""Install the pinned long-form research, narration, and rendering runtime."""

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
LOCK_PATH = ROOT / "tools" / "longform-stack.lock.json"
TOOLS_ROOT = ROOT / "tools" / "longform"
VENV_DIR = TOOLS_ROOT / ".venv"
ENV_TEMPLATE = ROOT / "config" / "longform.env.example"
ENV_PATH = TOOLS_ROOT / ".env"
INSTALL_RECORD = TOOLS_ROOT / "install.json"


class InstallError(RuntimeError):
    """An actionable installation error."""


def run(
    command: list[str],
    *,
    capture: bool = False,
    dry_run: bool = False,
) -> subprocess.CompletedProcess[str]:
    print("$ " + " ".join(command))
    if dry_run:
        return subprocess.CompletedProcess(command, 0, "", "")
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        text=True,
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        output = ""
        if capture:
            merged = (result.stdout or "") + (result.stderr or "")
            output = "\n" + "\n".join(merged.splitlines()[-40:]) if merged else ""
        raise InstallError(
            f"command failed with exit code {result.returncode}: {' '.join(command)}{output}"
        )
    return result


def load_lock() -> dict[str, Any]:
    try:
        data = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise InstallError(f"missing lock file: {LOCK_PATH}") from exc
    except json.JSONDecodeError as exc:
        raise InstallError(f"invalid lock file: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("packages"), list):
        raise InstallError("lock file must contain a packages array")
    for item in data["packages"]:
        if not isinstance(item, dict) or not item.get("id") or not item.get("version"):
            raise InstallError("every package requires id and version")
    return data


def require_uv(*, dry_run: bool) -> str:
    uv = shutil.which("uv")
    if uv:
        return uv
    if dry_run:
        return "uv"
    raise InstallError(
        "uv is required. Install uv from the official Astral documentation, "
        "reopen the terminal, and rerun this script."
    )


def venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def venv_executable(name: str) -> Path:
    suffix = ".exe" if os.name == "nt" else ""
    directory = VENV_DIR / ("Scripts" if os.name == "nt" else "bin")
    return directory / f"{name}{suffix}"


def ensure_environment_file(*, dry_run: bool) -> None:
    if ENV_PATH.exists():
        print(f"Using existing environment file: {ENV_PATH}")
        return
    if not ENV_TEMPLATE.is_file():
        raise InstallError(f"missing environment template: {ENV_TEMPLATE}")
    print(f"Creating local environment file: {ENV_PATH}")
    if not dry_run:
        ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ENV_TEMPLATE, ENV_PATH)


def install_packages(lock: dict[str, Any], *, dry_run: bool) -> list[str]:
    uv = require_uv(dry_run=dry_run)
    python_version = str(lock.get("python") or "3.11")
    if not VENV_DIR.exists():
        run([uv, "venv", "--python", python_version, str(VENV_DIR)], dry_run=dry_run)

    specs = [f"{item['id']}=={item['version']}" for item in lock["packages"]]
    run(
        [uv, "pip", "install", "--python", str(venv_python()), "--upgrade", *specs],
        dry_run=dry_run,
    )
    return specs


def verify_runtime(*, dry_run: bool) -> dict[str, str]:
    if dry_run:
        return {
            "python": str(venv_python()),
            "edge_tts": str(venv_executable("edge-tts")),
            "ffmpeg": "resolved at runtime through imageio_ffmpeg",
        }

    probe = (
        "import json; "
        "import pypdf, docx, edge_tts, imageio_ffmpeg; "
        "print(json.dumps({"
        "'pypdf': getattr(pypdf, '__version__', 'unknown'),"
        "'python_docx': getattr(docx, '__version__', 'unknown'),"
        "'edge_tts': getattr(edge_tts, '__version__', 'unknown'),"
        "'ffmpeg': imageio_ffmpeg.get_ffmpeg_exe()"
        "}))"
    )
    result = run([str(venv_python()), "-c", probe], capture=True)
    try:
        details = json.loads((result.stdout or "").strip())
    except json.JSONDecodeError as exc:
        raise InstallError("runtime verification returned invalid JSON") from exc
    ffmpeg = Path(str(details.get("ffmpeg") or ""))
    if not ffmpeg.is_file():
        raise InstallError(f"imageio-ffmpeg did not provide a valid executable: {ffmpeg}")
    help_result = run([str(ffmpeg), "-version"], capture=True)
    first_line = next(
        (line.strip() for line in (help_result.stdout or "").splitlines() if line.strip()),
        "ffmpeg ready",
    )
    details["ffmpeg_version"] = first_line
    return {str(key): str(value) for key, value in details.items()}


def write_install_record(
    *,
    lock: dict[str, Any],
    specs: list[str],
    runtime: dict[str, str],
    dry_run: bool,
) -> None:
    record = {
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "lock_file": str(LOCK_PATH),
        "venv": str(VENV_DIR),
        "environment_file": str(ENV_PATH),
        "packages": specs,
        "runtime": runtime,
        "licenses": {
            str(item["id"]): str(item.get("license", "unknown"))
            for item in lock["packages"]
        },
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
        "--dry-run",
        action="store_true",
        help="Print the pinned installation plan without changing the filesystem.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    lock = load_lock()
    print("Installing long-form production runtime")
    specs = install_packages(lock, dry_run=args.dry_run)
    ensure_environment_file(dry_run=args.dry_run)
    runtime = verify_runtime(dry_run=args.dry_run)
    write_install_record(
        lock=lock,
        specs=specs,
        runtime=runtime,
        dry_run=args.dry_run,
    )
    print("Long-form runtime is ready.")
    print(f"Environment file: {ENV_PATH}")
    print("Do not commit real API keys.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (InstallError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
