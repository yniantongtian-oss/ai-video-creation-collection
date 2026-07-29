#!/usr/bin/env python3
"""Shared helpers for the long-form video pipeline."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LONGFORM_ROOT = ROOT / "tools" / "longform"
LONGFORM_VENV = LONGFORM_ROOT / ".venv"
LONGFORM_ENV = LONGFORM_ROOT / ".env"


class LongformError(RuntimeError):
    """An actionable pipeline error."""


def runtime_python() -> Path:
    if os.name == "nt":
        return LONGFORM_VENV / "Scripts" / "python.exe"
    return LONGFORM_VENV / "bin" / "python"


def runtime_executable(name: str) -> Path:
    suffix = ".exe" if os.name == "nt" else ""
    directory = LONGFORM_VENV / ("Scripts" if os.name == "nt" else "bin")
    return directory / f"{name}{suffix}"


def ensure_runtime() -> None:
    if not runtime_python().is_file():
        raise LongformError(
            "long-form runtime is not installed; run "
            "python scripts/install_longform_stack.py"
        )


def reexec_in_runtime(required_module: str) -> None:
    """Re-execute a script in the managed runtime when a dependency is absent."""
    try:
        __import__(required_module)
        return
    except ImportError:
        pass
    ensure_runtime()
    current = Path(sys.executable).resolve()
    target = runtime_python().resolve()
    if current == target:
        raise LongformError(f"required module is missing in long-form runtime: {required_module}")
    result = subprocess.run([str(target), *sys.argv], check=False)
    raise SystemExit(result.returncode)


def load_dotenv(path: Path = LONGFORM_ENV) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name, "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise LongformError(f"{name} must be an integer") from exc


def env_float(name: str, default: float) -> float:
    value = os.environ.get(name, "").strip()
    if not value:
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise LongformError(f"{name} must be a number") from exc


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LongformError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise LongformError(f"invalid JSON in {path}: {exc}") from exc


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def append_jsonl(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def load_project(project: Path) -> tuple[Path, dict[str, Any]]:
    root = project.expanduser().resolve()
    config_path = root / "project.json"
    data = read_json(config_path)
    if not isinstance(data, dict) or not isinstance(data.get("chapters"), list):
        raise LongformError(f"not a valid long-form project: {root}")
    return root, data


def update_pipeline_stage(project: Path, stage: str, state: str, **details: object) -> None:
    path = project / "state" / "pipeline.json"
    payload = read_json(path) if path.exists() else {"stages": {}}
    if not isinstance(payload, dict):
        payload = {"stages": {}}
    stages = payload.setdefault("stages", {})
    if not isinstance(stages, dict):
        stages = {}
        payload["stages"] = stages
    stages[stage] = state
    payload["state"] = state if state in {"failed", "completed"} else payload.get("state", "running")
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    if details:
        stage_details = payload.setdefault("details", {})
        if isinstance(stage_details, dict):
            stage_details[stage] = details
    write_json(path, payload)


def update_chapter_stage(
    project: Path, chapter_id: str, stage: str, state: str, **details: object
) -> None:
    path = project / "chapters" / chapter_id / "status.json"
    payload = read_json(path) if path.exists() else {"stages": {}}
    if not isinstance(payload, dict):
        payload = {"stages": {}}
    stages = payload.setdefault("stages", {})
    if not isinstance(stages, dict):
        stages = {}
        payload["stages"] = stages
    stages[stage] = state
    payload["state"] = "failed" if state == "failed" else payload.get("state", "running")
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    if details:
        stage_details = payload.setdefault("details", {})
        if isinstance(stage_details, dict):
            stage_details[stage] = details
    write_json(path, payload)


def get_ffmpeg() -> Path:
    configured = os.environ.get("LONGFORM_FFMPEG", "").strip()
    if configured:
        path = Path(configured).expanduser().resolve()
        if path.is_file():
            return path
        raise LongformError(f"LONGFORM_FFMPEG does not exist: {path}")
    system = shutil.which("ffmpeg")
    if system:
        return Path(system)
    reexec_in_runtime("imageio_ffmpeg")
    import imageio_ffmpeg  # type: ignore

    path = Path(imageio_ffmpeg.get_ffmpeg_exe())
    if not path.is_file():
        raise LongformError(f"imageio-ffmpeg returned an invalid executable: {path}")
    return path


def run_command(
    command: list[str],
    *,
    cwd: Path | None = None,
    capture: bool = False,
    log_path: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    print("$ " + " ".join(command))
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("w", encoding="utf-8") as handle:
            result = subprocess.run(
                command,
                cwd=cwd,
                stdout=handle,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
                check=False,
            )
    else:
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
            merged = (result.stdout or "") + (result.stderr or "")
            detail = "\n" + "\n".join(merged.splitlines()[-40:]) if merged else ""
        elif log_path and log_path.exists():
            lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
            detail = "\n" + "\n".join(lines[-40:]) if lines else ""
        raise LongformError(
            f"command failed with exit code {result.returncode}: {' '.join(command)}{detail}"
        )
    return result


def probe_duration(media: Path) -> float:
    ffmpeg = get_ffmpeg()
    result = subprocess.run(
        [str(ffmpeg), "-hide_banner", "-i", str(media)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        check=False,
    )
    output = (result.stdout or "") + (result.stderr or "")
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", output)
    if not match:
        raise LongformError(f"unable to determine media duration: {media}")
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
