#!/usr/bin/env python3
"""Validate catalog/projects.json using only the Python standard library."""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "catalog" / "projects.json"

ALLOWED_CATEGORIES = {
    "agent-skills",
    "python-library",
    "research-framework",
    "video-editing-cli",
    "video-model",
    "workflow-engine",
    "workflow-tool",
}
REQUIRED_FIELDS = {
    "id",
    "name",
    "category",
    "repository",
    "official",
    "license",
    "capabilities",
    "when_to_use",
    "notes",
}
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)


def validate_repository_url(value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return "repository must be a non-empty string"

    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.netloc.lower() != "github.com":
        return "repository must use an https://github.com/... URL"

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 2:
        return "repository URL must point to a repository root (owner/name)"

    if parsed.query or parsed.fragment:
        return "repository URL must not contain a query string or fragment"

    return None


def main() -> int:
    errors: list[str] = []

    try:
        raw = CATALOG_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        fail(f"missing catalog: {CATALOG_PATH}")
        return 1

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}")
        return 1

    if not isinstance(data, dict):
        fail("catalog root must be an object")
        return 1

    if not isinstance(data.get("schema_version"), str):
        errors.append("schema_version must be a string")

    reviewed = data.get("last_reviewed")
    if not isinstance(reviewed, str):
        errors.append("last_reviewed must be an ISO date string")
    else:
        try:
            date.fromisoformat(reviewed)
        except ValueError:
            errors.append("last_reviewed must use YYYY-MM-DD")

    projects = data.get("projects")
    if not isinstance(projects, list) or not projects:
        errors.append("projects must be a non-empty array")
        projects = []

    seen_ids: set[str] = set()
    seen_repositories: set[str] = set()

    for index, project in enumerate(projects):
        prefix = f"projects[{index}]"
        if not isinstance(project, dict):
            errors.append(f"{prefix} must be an object")
            continue

        missing = sorted(REQUIRED_FIELDS - set(project))
        if missing:
            errors.append(f"{prefix} missing fields: {', '.join(missing)}")

        project_id = project.get("id")
        if not isinstance(project_id, str) or not ID_PATTERN.fullmatch(project_id):
            errors.append(f"{prefix}.id must be lowercase kebab-case")
        elif project_id in seen_ids:
            errors.append(f"{prefix}.id duplicates {project_id!r}")
        else:
            seen_ids.add(project_id)

        name = project.get("name")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"{prefix}.name must be a non-empty string")

        category = project.get("category")
        if category not in ALLOWED_CATEGORIES:
            allowed = ", ".join(sorted(ALLOWED_CATEGORIES))
            errors.append(f"{prefix}.category must be one of: {allowed}")

        repository = project.get("repository")
        url_error = validate_repository_url(repository)
        if url_error:
            errors.append(f"{prefix}.repository {url_error}")
        elif repository in seen_repositories:
            errors.append(f"{prefix}.repository duplicates {repository!r}")
        else:
            seen_repositories.add(repository)

        if not isinstance(project.get("official"), bool):
            errors.append(f"{prefix}.official must be true or false")

        for field in ("license", "when_to_use", "notes"):
            value = project.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{prefix}.{field} must be a non-empty string")

        capabilities = project.get("capabilities")
        if not isinstance(capabilities, list) or not capabilities:
            errors.append(f"{prefix}.capabilities must be a non-empty array")
        elif any(not isinstance(item, str) or not item.strip() for item in capabilities):
            errors.append(f"{prefix}.capabilities must contain non-empty strings")
        elif len(capabilities) != len(set(capabilities)):
            errors.append(f"{prefix}.capabilities contains duplicate values")

        extra = sorted(set(project) - REQUIRED_FIELDS)
        if extra:
            errors.append(f"{prefix} contains unsupported fields: {', '.join(extra)}")

    if errors:
        for message in errors:
            fail(message)
        print(f"Catalog validation failed with {len(errors)} error(s).", file=sys.stderr)
        return 1

    print(f"Catalog OK: {len(projects)} projects, {len(seen_repositories)} unique repositories.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
