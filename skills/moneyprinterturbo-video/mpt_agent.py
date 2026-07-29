#!/usr/bin/env python3
"""Verified bootstrap for MoneyPrinterTurbo's official Agent Skill helper.

Both the helper and the MoneyPrinterTurbo project are pinned. The wrapper first
ensures that tools/web-media/apps/MoneyPrinterTurbo is checked out at the audited
commit, then passes that directory to the upstream helper through --root. This
prevents the helper's own first-run fallback from downloading a moving main.zip.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

UPSTREAM_COMMIT = "42f776e2e0950394ea150f28e4ab49d8ab9b3ba1"
UPSTREAM_GIT_BLOB_SHA1 = "e51245ae7a1c263b88ca5b3cd76aa6a1896093a6"
UPSTREAM_URL = (
    "https://raw.githubusercontent.com/harry0703/MoneyPrinterTurbo/"
    f"{UPSTREAM_COMMIT}/docs/skill/mpt_agent.py"
)
USER_AGENT = "ai-video-creation-collection-mpt-skill/1.1"
REPO_ROOT = Path(__file__).resolve().parents[2]
STACK_INSTALLER = REPO_ROOT / "scripts" / "install_web_media_stack.py"
PINNED_PROJECT = REPO_ROOT / "tools" / "web-media" / "apps" / "MoneyPrinterTurbo"


class BootstrapError(RuntimeError):
    pass


def git_blob_sha1(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content).hexdigest()


def cache_path() -> Path:
    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return (
        root
        / "ai-video-creation-collection"
        / "moneyprinterturbo-video"
        / UPSTREAM_COMMIT
        / "mpt_agent.py"
    )


def validate_helper(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        content = path.read_bytes()
    except OSError:
        return False
    return git_blob_sha1(content) == UPSTREAM_GIT_BLOB_SHA1


def download_verified_helper(destination: Path) -> None:
    request = urllib.request.Request(UPSTREAM_URL, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            content = response.read()
    except urllib.error.URLError as exc:
        raise BootstrapError(
            f"unable to download official MPT helper: {exc.reason}"
        ) from exc

    actual = git_blob_sha1(content)
    if actual != UPSTREAM_GIT_BLOB_SHA1:
        raise BootstrapError(
            "official MPT helper integrity check failed: "
            f"expected {UPSTREAM_GIT_BLOB_SHA1}, got {actual}"
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb", delete=False, dir=destination.parent, prefix=".mpt-agent-"
    ) as handle:
        temp_path = Path(handle.name)
        handle.write(content)
    try:
        temp_path.replace(destination)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def project_head(project: Path) -> str:
    if not (project / ".git").is_dir():
        return ""
    git = shutil.which("git")
    if not git:
        raise BootstrapError("git is required to verify the pinned MoneyPrinterTurbo checkout")
    result = subprocess.run(
        [git, "rev-parse", "HEAD"],
        cwd=project,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def project_is_valid(project: Path) -> bool:
    return (
        (project / "cli.py").is_file()
        and (project / "config.example.toml").is_file()
        and project_head(project) == UPSTREAM_COMMIT
    )


def ensure_pinned_project() -> Path:
    if project_is_valid(PINNED_PROJECT):
        return PINNED_PROJECT
    if not STACK_INSTALLER.is_file():
        raise BootstrapError(
            "the pinned MoneyPrinterTurbo project is missing and the stack installer "
            f"was not found at {STACK_INSTALLER}; install this Skill from the full repository"
        )
    result = subprocess.run(
        [
            sys.executable,
            str(STACK_INSTALLER),
            "--profile",
            "creator",
        ],
        cwd=REPO_ROOT,
        check=False,
    )
    if result.returncode != 0:
        raise BootstrapError(
            "failed to install the pinned MoneyPrinterTurbo project; "
            f"installer exit code: {result.returncode}"
        )
    if not project_is_valid(PINNED_PROJECT):
        actual = project_head(PINNED_PROJECT) or "missing"
        raise BootstrapError(
            "MoneyPrinterTurbo checkout verification failed after installation: "
            f"expected {UPSTREAM_COMMIT}, got {actual}"
        )
    return PINNED_PROJECT


def remove_user_root_override(argv: list[str]) -> list[str]:
    """Force the audited checkout instead of an arbitrary or moving project root."""
    cleaned: list[str] = []
    index = 0
    while index < len(argv):
        value = argv[index]
        if value == "--root":
            index += 2
            continue
        if value.startswith("--root="):
            index += 1
            continue
        cleaned.append(value)
        index += 1
    return cleaned


def main() -> int:
    project = ensure_pinned_project()
    helper = cache_path()
    if not validate_helper(helper):
        download_verified_helper(helper)
    forwarded = remove_user_root_override(sys.argv[1:])
    result = subprocess.run(
        [
            sys.executable,
            str(helper),
            "--root",
            str(project),
            *forwarded,
        ],
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BootstrapError, OSError, ValueError) as exc:
        print(f"MPT_ERROR={exc}", file=sys.stderr)
        raise SystemExit(1)
