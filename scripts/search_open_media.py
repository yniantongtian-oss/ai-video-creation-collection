#!/usr/bin/env python3
"""Search open/licensed media providers and optionally download candidates.

Supported providers:
- Wikimedia Commons: images, video, and audio with file-page license metadata.
- Openverse: images and audio under Creative Commons/public-domain metadata.
- Pexels: photos and videos under the Pexels license (API key required).
- Pixabay: images and videos under the Pixabay Content License (API key required).

Search results are candidates only. They are appended with selected=false and
must pass scripts/media_asset_manifest.py validate before final rendering.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import mimetypes
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV = ROOT / "tools" / "web-media" / ".env"
USER_AGENT = "ai-video-creation-collection-open-media/1.0"
PEXELS_LICENSE = "https://www.pexels.com/license/"
PIXABAY_LICENSE = "https://pixabay.com/service/license-summary/"


class SearchError(RuntimeError):
    pass


def load_dotenv(path: Path) -> None:
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


def request_json(
    url: str, *, headers: dict[str, str] | None = None, timeout: int = 30
) -> dict[str, Any]:
    request_headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(url, headers=request_headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise SearchError(f"HTTP {exc.code} from provider: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SearchError(f"provider request failed: {exc.reason}") from exc
    if not isinstance(payload, dict):
        raise SearchError("provider returned a non-object JSON response")
    return payload


def strip_html(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def metadata_value(metadata: dict[str, Any], key: str) -> str:
    raw = metadata.get(key, {})
    if isinstance(raw, dict):
        raw = raw.get("value", "")
    return strip_html(raw)


def rights_from_license(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if "public-domain" in normalized or normalized in {"pd", "pdm"}:
        return "public-domain"
    if "cc0" in normalized:
        return "cc0"
    if "cc-by-sa" in normalized or "by-sa" in normalized:
        return "cc-by-sa"
    if "cc-by" in normalized or normalized.startswith("by-"):
        return "cc-by"
    return "unknown"


def media_kind_from_mime(mime: str) -> str:
    if mime.startswith("image/"):
        return "image"
    if mime.startswith("video/"):
        return "video"
    if mime.startswith("audio/"):
        return "audio"
    return "other"


def search_commons(query: str, media_type: str, limit: int) -> list[dict[str, Any]]:
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": "6",
        "gsrlimit": str(min(limit * 3, 50)),
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|mime|size",
        "format": "json",
        "formatversion": "2",
        "origin": "*",
    }
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    payload = request_json(url)
    pages = payload.get("query", {}).get("pages", [])
    results: list[dict[str, Any]] = []
    for page in pages if isinstance(pages, list) else []:
        infos = page.get("imageinfo") or []
        if not infos:
            continue
        info = infos[0]
        mime = str(info.get("mime") or "")
        kind = media_kind_from_mime(mime)
        if media_type != "any" and kind != media_type:
            continue
        metadata = info.get("extmetadata") or {}
        license_name = metadata_value(metadata, "LicenseShortName") or metadata_value(
            metadata, "UsageTerms"
        )
        creator = metadata_value(metadata, "Artist")
        description_url = str(info.get("descriptionurl") or "")
        results.append(
            {
                "provider": "Wikimedia Commons",
                "provider_id": str(page.get("pageid") or page.get("title") or ""),
                "kind": kind,
                "title": str(page.get("title") or "").removeprefix("File:"),
                "creator": creator,
                "license": license_name,
                "license_url": metadata_value(metadata, "LicenseUrl"),
                "rights_status": rights_from_license(license_name),
                "source_url": description_url,
                "direct_url": str(info.get("url") or ""),
                "thumbnail_url": str(info.get("thumburl") or info.get("url") or ""),
                "attribution": metadata_value(metadata, "Credit")
                or f"{creator} / Wikimedia Commons",
                "mime": mime,
            }
        )
        if len(results) >= limit:
            break
    return results


def search_openverse(query: str, media_type: str, limit: int) -> list[dict[str, Any]]:
    if media_type not in {"image", "audio"}:
        raise SearchError("Openverse supports --media-type image or audio in this script")
    endpoint = "images" if media_type == "image" else "audio"
    params = urllib.parse.urlencode({"q": query, "page_size": min(limit, 50)})
    payload = request_json(f"https://api.openverse.org/v1/{endpoint}/?{params}")
    raw_results = payload.get("results") or []
    results: list[dict[str, Any]] = []
    for item in raw_results if isinstance(raw_results, list) else []:
        license_code = str(item.get("license") or "")
        license_version = str(item.get("license_version") or "")
        license_name = " ".join(part for part in [license_code.upper(), license_version] if part)
        results.append(
            {
                "provider": "Openverse",
                "provider_id": str(item.get("id") or ""),
                "kind": media_type,
                "title": str(item.get("title") or ""),
                "creator": str(item.get("creator") or ""),
                "license": license_name,
                "license_url": str(item.get("license_url") or ""),
                "rights_status": rights_from_license(license_name),
                "source_url": str(item.get("foreign_landing_url") or item.get("detail_url") or ""),
                "direct_url": str(item.get("url") or ""),
                "thumbnail_url": str(item.get("thumbnail") or ""),
                "attribution": str(item.get("attribution") or ""),
                "mime": str(item.get("filetype") or ""),
            }
        )
    return results[:limit]


def choose_pexels_video_file(files: list[dict[str, Any]]) -> dict[str, Any]:
    usable = [item for item in files if str(item.get("link") or "").startswith("https://")]
    if not usable:
        return {}
    return max(
        usable,
        key=lambda item: (
            1 if item.get("quality") == "hd" else 0,
            int(item.get("width") or 0) * int(item.get("height") or 0),
        ),
    )


def search_pexels(query: str, media_type: str, limit: int) -> list[dict[str, Any]]:
    key = os.environ.get("PEXELS_API_KEY") or os.environ.get("MPT_PEXELS_API_KEY")
    if not key:
        raise SearchError("Pexels requires PEXELS_API_KEY or MPT_PEXELS_API_KEY")
    if media_type == "image":
        endpoint = "https://api.pexels.com/v1/search"
    elif media_type == "video":
        endpoint = "https://api.pexels.com/v1/videos/search"
    else:
        raise SearchError("Pexels supports --media-type image or video")
    params = urllib.parse.urlencode({"query": query, "per_page": min(limit, 80)})
    payload = request_json(f"{endpoint}?{params}", headers={"Authorization": key})
    raw_results = payload.get("photos" if media_type == "image" else "videos") or []
    results: list[dict[str, Any]] = []
    for item in raw_results if isinstance(raw_results, list) else []:
        creator = str(item.get("photographer") or item.get("user", {}).get("name") or "")
        creator_url = str(item.get("photographer_url") or item.get("user", {}).get("url") or "")
        if media_type == "image":
            direct_url = str((item.get("src") or {}).get("large2x") or (item.get("src") or {}).get("original") or "")
            thumbnail = str((item.get("src") or {}).get("medium") or "")
            mime = "image/jpeg"
        else:
            selected_file = choose_pexels_video_file(item.get("video_files") or [])
            direct_url = str(selected_file.get("link") or "")
            pictures = item.get("video_pictures") or []
            thumbnail = str(pictures[0].get("picture") if pictures else "")
            mime = str(selected_file.get("file_type") or "video/mp4")
        source_url = str(item.get("url") or "")
        results.append(
            {
                "provider": "Pexels",
                "provider_id": str(item.get("id") or ""),
                "kind": media_type,
                "title": str(item.get("alt") or f"Pexels {media_type} {item.get('id', '')}"),
                "creator": creator,
                "creator_url": creator_url,
                "license": "Pexels License",
                "license_url": PEXELS_LICENSE,
                "rights_status": "provider-licensed",
                "source_url": source_url,
                "direct_url": direct_url,
                "thumbnail_url": thumbnail,
                "attribution": f"{creator} / Pexels" if creator else "Pexels",
                "mime": mime,
            }
        )
    return results[:limit]


def choose_pixabay_video_file(videos: dict[str, Any]) -> dict[str, Any]:
    for key in ("large", "medium", "small", "tiny"):
        item = videos.get(key) or {}
        if str(item.get("url") or "").startswith("https://"):
            return item
    return {}


def search_pixabay(query: str, media_type: str, limit: int) -> list[dict[str, Any]]:
    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        raise SearchError("Pixabay requires PIXABAY_API_KEY")
    if media_type == "image":
        endpoint = "https://pixabay.com/api/"
    elif media_type == "video":
        endpoint = "https://pixabay.com/api/videos/"
    else:
        raise SearchError("Pixabay supports --media-type image or video")
    params = urllib.parse.urlencode(
        {"key": key, "q": query, "per_page": min(max(limit, 3), 200), "safesearch": "true"}
    )
    payload = request_json(f"{endpoint}?{params}")
    raw_results = payload.get("hits") or []
    results: list[dict[str, Any]] = []
    for item in raw_results if isinstance(raw_results, list) else []:
        if media_type == "image":
            direct_url = str(item.get("largeImageURL") or item.get("webformatURL") or "")
            thumbnail = str(item.get("previewURL") or "")
            mime = "image/jpeg"
        else:
            selected_file = choose_pixabay_video_file(item.get("videos") or {})
            direct_url = str(selected_file.get("url") or "")
            thumbnail = str(selected_file.get("thumbnail") or "")
            mime = "video/mp4"
        creator = str(item.get("user") or "")
        creator_url = ""
        if creator and item.get("user_id"):
            creator_url = f"https://pixabay.com/users/{urllib.parse.quote(creator)}-{item['user_id']}/"
        results.append(
            {
                "provider": "Pixabay",
                "provider_id": str(item.get("id") or ""),
                "kind": media_type,
                "title": str(item.get("tags") or f"Pixabay {media_type} {item.get('id', '')}"),
                "creator": creator,
                "creator_url": creator_url,
                "license": "Pixabay Content License",
                "license_url": PIXABAY_LICENSE,
                "rights_status": "provider-licensed",
                "source_url": str(item.get("pageURL") or ""),
                "direct_url": direct_url,
                "thumbnail_url": thumbnail,
                "attribution": f"{creator} / Pixabay" if creator else "Pixabay",
                "mime": mime,
            }
        )
    return results[:limit]


def safe_filename(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip(".-")
    return value[:120] or "asset"


def extension_for(item: dict[str, Any]) -> str:
    url_path = urllib.parse.urlparse(str(item.get("direct_url") or "")).path
    suffix = Path(url_path).suffix.lower()
    if 1 < len(suffix) <= 8:
        return suffix
    mime = str(item.get("mime") or "").split(";", 1)[0]
    return mimetypes.guess_extension(mime) or {
        "image": ".jpg",
        "video": ".mp4",
        "audio": ".mp3",
    }.get(str(item.get("kind")), ".bin")


def download_item(item: dict[str, Any], directory: Path, max_bytes: int) -> Path:
    url = str(item.get("direct_url") or "")
    if not url.startswith("https://"):
        raise SearchError(f"candidate has no HTTPS download URL: {item.get('source_url')}")
    filename = safe_filename(f"{item.get('provider')}-{item.get('provider_id')}") + extension_for(item)
    destination = directory / filename
    directory.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    temp = destination.with_suffix(destination.suffix + ".part")
    downloaded = 0
    try:
        with urllib.request.urlopen(request, timeout=90) as response, temp.open("wb") as handle:
            length = response.headers.get("Content-Length")
            if length and int(length) > max_bytes:
                raise SearchError(f"asset exceeds --max-bytes: {length} > {max_bytes}")
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                downloaded += len(block)
                if downloaded > max_bytes:
                    raise SearchError(f"asset exceeded --max-bytes while downloading: {max_bytes}")
                handle.write(block)
        temp.replace(destination)
    finally:
        if temp.exists():
            temp.unlink()
    return destination


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def append_manifest(manifest: Path, item: dict[str, Any], local_path: Path) -> None:
    project_root = manifest.parent.parent
    try:
        relative = local_path.resolve().relative_to(project_root.resolve())
        path_value = relative.as_posix()
    except ValueError:
        path_value = str(local_path.resolve())
    entry = {
        "id": safe_filename(f"{item.get('provider')}-{item.get('provider_id')}"),
        "kind": item.get("kind"),
        "local_path": path_value,
        "source_url": item.get("source_url"),
        "provider": item.get("provider"),
        "title": item.get("title"),
        "creator": item.get("creator"),
        "creator_url": item.get("creator_url", ""),
        "license": item.get("license"),
        "license_url": item.get("license_url"),
        "rights_status": item.get("rights_status"),
        "attribution": item.get("attribution"),
        "selected": False,
        "sha256": sha256(local_path),
        "size_bytes": local_path.stat().st_size,
        "acquired_at": datetime.now(timezone.utc).isoformat(),
        "notes": "Downloaded as a candidate; Codex must review relevance and rights before setting selected=true.",
    }
    manifest.parent.mkdir(parents=True, exist_ok=True)
    with manifest.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=["commons", "openverse", "pexels", "pixabay"], required=True)
    parser.add_argument("--media-type", choices=["image", "video", "audio", "any"], required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--output", type=Path, help="Write normalized search results as JSON.")
    parser.add_argument("--download-dir", type=Path)
    parser.add_argument("--download-first", type=int, default=0)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--max-bytes", type=int, default=500 * 1024 * 1024)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    args = parser.parse_args()
    if not 1 <= args.limit <= 200:
        parser.error("--limit must be between 1 and 200")
    if args.download_first < 0 or args.download_first > args.limit:
        parser.error("--download-first must be between 0 and --limit")
    if args.download_first and not args.download_dir:
        parser.error("--download-first requires --download-dir")
    if args.manifest and not args.download_first:
        parser.error("--manifest requires --download-first")
    return args


def main() -> int:
    args = parse_args()
    load_dotenv(args.env_file.expanduser().resolve())
    searchers = {
        "commons": search_commons,
        "openverse": search_openverse,
        "pexels": search_pexels,
        "pixabay": search_pixabay,
    }
    try:
        results = searchers[args.provider](args.query, args.media_type, args.limit)
        payload = {
            "provider": args.provider,
            "media_type": args.media_type,
            "query": args.query,
            "searched_at": datetime.now(timezone.utc).isoformat(),
            "count": len(results),
            "results": results,
        }
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        if args.output:
            output = args.output.expanduser().resolve()
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(text + "\n", encoding="utf-8")
            print(f"Search results: {output}")
        else:
            print(text)

        for item in results[: args.download_first]:
            local_path = download_item(
                item, args.download_dir.expanduser().resolve(), args.max_bytes
            )
            print(f"Downloaded: {local_path}")
            if args.manifest:
                append_manifest(args.manifest.expanduser().resolve(), item, local_path)
        return 0
    except (SearchError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
