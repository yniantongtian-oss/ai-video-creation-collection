#!/usr/bin/env python3
"""Verified bootstrap for MoneyPrinterTurbo's official Agent Skill helper.

The upstream helper is pinned by commit and Git blob SHA. It is cached outside
this repository, then executed with the current Python interpreter. Updating the
pin requires reviewing the upstream helper and changing both constants.
"""

from __future__ import annotations

import hashlib
import os
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
USER_AGENT = "ai-video-creation-collection-mpt-skill/1.0"


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


def validate(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        content = path.read_bytes()
    except OSError:
        return False
    return git_blob_sha1(content) == UPSTREAM_GIT_BLOB_SHA1


def download_verified(destination: Path) -> None:
    request = urllib.request.Request(UPSTREAM_URL, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            content = response.read()
    except urllib.error.URLError as exc:
        raise BootstrapError(f"unable to download official MPT helper: {exc.reason}") from exc

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


def main() -> int:
    helper = cache_path()
    if not validate(helper):
        download_verified(helper)
    result = subprocess.run([sys.executable, str(helper), *sys.argv[1:]], check=False)
    return result.returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BootstrapError, OSError, ValueError) as exc:
        print(f"MPT_ERROR={exc}", file=sys.stderr)
        raise SystemExit(1)
