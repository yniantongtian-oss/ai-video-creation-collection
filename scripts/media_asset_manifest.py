#!/usr/bin/env python3
"""Add, list, hash, and validate research/video asset manifest entries."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_ALLOWED = {
    "public-domain",
    "cc0",
    "cc-by",
    "cc-by-sa",
    "provider-licensed",
    "user-owned",
    "permission-granted",
}
KNOWN_RIGHTS = DEFAULT_ALLOWED | {"unknown", "restricted"}
KNOWN_KINDS = {"video", "image", "audio", "document", "subtitle", "font", "other"}


class ManifestError(RuntimeError):
    pass


def read_entries(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ManifestError(f"invalid JSON on line {number}: {exc}") from exc
        if not isinstance(item, dict):
            raise ManifestError(f"line {number} must contain a JSON object")
        entries.append(item)
    return entries


def append_entry(path: Path, entry: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def command_add(args: argparse.Namespace) -> int:
    manifest = args.manifest.expanduser().resolve()
    entries = read_entries(manifest)
    existing_ids = {str(item.get("id")) for item in entries}
    if args.id in existing_ids:
        raise ManifestError(f"duplicate asset id: {args.id}")
    if args.kind not in KNOWN_KINDS:
        raise ManifestError(f"unsupported kind: {args.kind}")
    if args.rights_status not in KNOWN_RIGHTS:
        raise ManifestError(f"unsupported rights status: {args.rights_status}")
    if args.selected and args.rights_status in {"unknown", "restricted"}:
        raise ManifestError("unknown or restricted assets cannot be selected")
    if args.rights_status in {"user-owned", "permission-granted"}:
        if not args.permission_note.strip():
            raise ManifestError(
                f"{args.rights_status} requires a concise --permission-note"
            )

    local_path = args.local_path
    sha256 = ""
    size_bytes: int | None = None
    if local_path:
        candidate = Path(local_path).expanduser()
        if not candidate.is_absolute():
            candidate = (manifest.parent.parent / candidate).resolve()
        if not candidate.is_file():
            raise ManifestError(f"local file does not exist: {candidate}")
        sha256 = file_sha256(candidate)
        size_bytes = candidate.stat().st_size

    entry: dict[str, Any] = {
        "id": args.id,
        "kind": args.kind,
        "local_path": local_path or "",
        "source_url": args.source_url,
        "provider": args.provider,
        "title": args.title,
        "creator": args.creator,
        "license": args.license,
        "license_url": args.license_url,
        "rights_status": args.rights_status,
        "attribution": args.attribution,
        "permission_note": args.permission_note,
        "selected": args.selected,
        "sha256": sha256,
        "size_bytes": size_bytes,
        "acquired_at": datetime.now(timezone.utc).isoformat(),
        "notes": args.notes,
    }
    append_entry(manifest, entry)
    print(f"Added {args.id} to {manifest}")
    return 0


def validation_errors(
    entries: list[dict[str, Any]], manifest: Path, allowed: set[str]
) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    project_root = manifest.parent.parent
    for index, item in enumerate(entries, 1):
        asset_id = str(item.get("id") or "")
        prefix = asset_id or f"line {index}"
        if not asset_id:
            errors.append(f"line {index}: missing id")
        elif asset_id in seen:
            errors.append(f"{prefix}: duplicate id")
        else:
            seen.add(asset_id)

        rights = str(item.get("rights_status") or "unknown")
        selected = bool(item.get("selected", False))
        source_url = str(item.get("source_url") or "")
        permission_note = str(item.get("permission_note") or "").strip()

        if selected and rights not in allowed:
            errors.append(
                f"{prefix}: selected asset has disallowed rights status {rights!r}"
            )
        if selected and rights != "user-owned" and not source_url.startswith("https://"):
            errors.append(f"{prefix}: selected non-local asset requires an HTTPS source_url")
        if selected and not str(item.get("license") or "").strip():
            errors.append(f"{prefix}: selected asset is missing license information")
        if selected and rights in {"cc-by", "cc-by-sa"}:
            if not str(item.get("creator") or "").strip():
                errors.append(f"{prefix}: attribution license requires creator")
            if not str(item.get("license_url") or "").startswith("https://"):
                errors.append(f"{prefix}: attribution license requires license_url")
        if selected and rights in {"permission-granted", "user-owned"}:
            if not permission_note:
                errors.append(f"{prefix}: {rights} requires permission_note")

        local_path = str(item.get("local_path") or "")
        if selected and not local_path:
            errors.append(f"{prefix}: selected asset has no local_path")
        elif local_path:
            candidate = Path(local_path).expanduser()
            if not candidate.is_absolute():
                candidate = (project_root / candidate).resolve()
            if not candidate.is_file():
                errors.append(f"{prefix}: local file is missing: {candidate}")
            else:
                recorded_hash = str(item.get("sha256") or "")
                if recorded_hash and file_sha256(candidate) != recorded_hash:
                    errors.append(
                        f"{prefix}: local file SHA-256 does not match manifest"
                    )
    return errors


def command_validate(args: argparse.Namespace) -> int:
    manifest = args.manifest.expanduser().resolve()
    entries = read_entries(manifest)
    allowed = set(args.allowed.split(",")) if args.allowed else DEFAULT_ALLOWED
    allowed = {value.strip() for value in allowed if value.strip()}
    errors = validation_errors(entries, manifest, allowed)
    selected_count = sum(bool(item.get("selected", False)) for item in entries)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(
            f"Manifest validation failed: {len(errors)} error(s), "
            f"{len(entries)} entries, {selected_count} selected.",
            file=sys.stderr,
        )
        return 1
    print(
        f"Manifest OK: {len(entries)} entries, {selected_count} selected, "
        f"allowed rights={','.join(sorted(allowed))}."
    )
    return 0


def command_list(args: argparse.Namespace) -> int:
    manifest = args.manifest.expanduser().resolve()
    entries = read_entries(manifest)
    if args.selected:
        entries = [item for item in entries if bool(item.get("selected", False))]
    for item in entries:
        print(
            "\t".join(
                [
                    str(item.get("id", "")),
                    str(item.get("kind", "")),
                    str(item.get("rights_status", "")),
                    "selected" if item.get("selected") else "candidate",
                    str(item.get("title", "")),
                    str(item.get("local_path", "")),
                ]
            )
        )
    return 0


def add_common_manifest_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--manifest", type=Path, required=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    add = subparsers.add_parser(
        "add", help="Append one manifest entry and hash its local file."
    )
    add_common_manifest_argument(add)
    add.add_argument("--id", required=True)
    add.add_argument("--kind", choices=sorted(KNOWN_KINDS), required=True)
    add.add_argument("--local-path", default="")
    add.add_argument(
        "--source-url",
        default="",
        help="HTTPS origin page. Optional only for user-owned local assets.",
    )
    add.add_argument("--provider", default="")
    add.add_argument("--title", default="")
    add.add_argument("--creator", default="")
    add.add_argument("--license", required=True)
    add.add_argument("--license-url", default="")
    add.add_argument("--rights-status", choices=sorted(KNOWN_RIGHTS), required=True)
    add.add_argument("--attribution", default="")
    add.add_argument("--permission-note", default="")
    add.add_argument("--notes", default="")
    add.add_argument("--selected", action="store_true")
    add.set_defaults(func=command_add)

    validate = subparsers.add_parser(
        "validate", help="Block selected assets without traceable rights."
    )
    add_common_manifest_argument(validate)
    validate.add_argument(
        "--allowed",
        default=os.environ.get("WEB_MEDIA_ALLOWED_RIGHTS", ""),
        help="Comma-separated allowed rights statuses.",
    )
    validate.set_defaults(func=command_validate)

    listing = subparsers.add_parser(
        "list", help="Print a compact tab-separated manifest view."
    )
    add_common_manifest_argument(listing)
    listing.add_argument("--selected", action="store_true")
    listing.set_defaults(func=command_list)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        return int(args.func(args))
    except (ManifestError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
