#!/usr/bin/env python3
"""Add, approve, list, hash, and validate research/video asset manifests."""

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


def write_entries(path: Path, entries: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temp.write_text(
        "".join(
            json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n"
            for entry in entries
        ),
        encoding="utf-8",
    )
    temp.replace(path)


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


def resolve_local_file(manifest: Path, value: str) -> Path:
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = (manifest.parent.parent / candidate).resolve()
    return candidate


def validate_selectable(item: dict[str, Any], manifest: Path, allowed: set[str]) -> None:
    asset_id = str(item.get("id") or "")
    rights = str(item.get("rights_status") or "unknown")
    source_url = str(item.get("source_url") or "")
    permission_note = str(item.get("permission_note") or "").strip()
    if rights not in allowed:
        raise ManifestError(
            f"{asset_id}: rights status {rights!r} is not allowed for selection"
        )
    if rights != "user-owned" and not source_url.startswith("https://"):
        raise ManifestError(f"{asset_id}: selected non-local asset requires an HTTPS source_url")
    if not str(item.get("license") or "").strip():
        raise ManifestError(f"{asset_id}: license information is missing")
    if rights in {"cc-by", "cc-by-sa"}:
        if not str(item.get("creator") or "").strip():
            raise ManifestError(f"{asset_id}: attribution license requires creator")
        if not str(item.get("license_url") or "").startswith("https://"):
            raise ManifestError(f"{asset_id}: attribution license requires license_url")
    if rights in {"permission-granted", "user-owned"} and not permission_note:
        raise ManifestError(f"{asset_id}: {rights} requires permission_note")
    local_path = str(item.get("local_path") or "")
    if not local_path:
        raise ManifestError(f"{asset_id}: selected asset has no local_path")
    candidate = resolve_local_file(manifest, local_path)
    if not candidate.is_file():
        raise ManifestError(f"{asset_id}: local file is missing: {candidate}")
    recorded_hash = str(item.get("sha256") or "")
    actual_hash = file_sha256(candidate)
    if recorded_hash and actual_hash != recorded_hash:
        raise ManifestError(f"{asset_id}: local file SHA-256 does not match manifest")
    if not recorded_hash:
        item["sha256"] = actual_hash
    item["size_bytes"] = candidate.stat().st_size


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
        candidate = resolve_local_file(manifest, local_path)
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
    if args.selected:
        validate_selectable(entry, manifest, DEFAULT_ALLOWED)
        entry["selected_at"] = datetime.now(timezone.utc).isoformat()
    append_entry(manifest, entry)
    print(f"Added {args.id} to {manifest}")
    return 0


def command_set_selected(args: argparse.Namespace) -> int:
    manifest = args.manifest.expanduser().resolve()
    entries = read_entries(manifest)
    requested_ids: list[str] = list(args.id or [])
    if args.ids_file:
        requested_ids.extend(
            line.strip()
            for line in args.ids_file.expanduser().read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
    requested_ids = list(dict.fromkeys(requested_ids))
    if not requested_ids:
        raise ManifestError("provide at least one --id or --ids-file")
    by_id = {str(item.get("id") or ""): item for item in entries}
    missing = [asset_id for asset_id in requested_ids if asset_id not in by_id]
    if missing:
        raise ManifestError(f"asset IDs not found: {', '.join(missing)}")
    allowed = set(args.allowed.split(",")) if args.allowed else DEFAULT_ALLOWED
    allowed = {value.strip() for value in allowed if value.strip()}
    selected = args.value == "true"
    for asset_id in requested_ids:
        item = by_id[asset_id]
        if selected:
            validate_selectable(item, manifest, allowed)
            item["selected"] = True
            item["selected_at"] = datetime.now(timezone.utc).isoformat()
            item["selection_note"] = args.note
        else:
            item["selected"] = False
            item["unselected_at"] = datetime.now(timezone.utc).isoformat()
            item["selection_note"] = args.note
    write_entries(manifest, entries)
    state = "selected" if selected else "unselected"
    print(f"Updated {len(requested_ids)} asset(s): {state}")
    return 0


def validation_errors(
    entries: list[dict[str, Any]], manifest: Path, allowed: set[str]
) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(entries, 1):
        asset_id = str(item.get("id") or "")
        prefix = asset_id or f"line {index}"
        if not asset_id:
            errors.append(f"line {index}: missing id")
        elif asset_id in seen:
            errors.append(f"{prefix}: duplicate id")
        else:
            seen.add(asset_id)
        if bool(item.get("selected", False)):
            try:
                validate_selectable(item, manifest, allowed)
            except ManifestError as exc:
                errors.append(str(exc))
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
    if args.candidates:
        entries = [item for item in entries if not bool(item.get("selected", False))]
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

    selection = subparsers.add_parser(
        "set-selected",
        help="Atomically approve or unapprove existing candidate assets by ID.",
    )
    add_common_manifest_argument(selection)
    selection.add_argument("--id", action="append")
    selection.add_argument("--ids-file", type=Path)
    selection.add_argument("--value", choices=["true", "false"], required=True)
    selection.add_argument("--note", default="Reviewed for relevance and rights.")
    selection.add_argument(
        "--allowed",
        default=os.environ.get("WEB_MEDIA_ALLOWED_RIGHTS", ""),
        help="Comma-separated allowed rights statuses.",
    )
    selection.set_defaults(func=command_set_selected)

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
    listing.add_argument("--candidates", action="store_true")
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
