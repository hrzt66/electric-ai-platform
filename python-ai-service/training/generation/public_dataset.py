from __future__ import annotations

import hashlib
import json
import re
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from PIL import Image, UnidentifiedImageError

from training.generation.captioning import build_caption_from_texts


OPENVERSE_ENDPOINT = "https://api.openverse.org/v1/images/"
WIKIMEDIA_ENDPOINT = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "electric-ai-platform/1.0 (+local training pipeline)"
ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_OPENVERSE_LICENSES = {"by", "by-sa", "cc0", "pdm"}

DEFAULT_PROVIDER_LIMITS = {
    "openverse": 80,
    "wikimedia": 80,
}

ELECTRIC_BUCKET_QUERIES = {
    "substation": [
        "electrical substation",
        "transformer yard",
        "switchgear",
        "circuit breaker substation",
    ],
    "transmission": [
        "transmission tower",
        "power line insulator",
        "utility pole power line",
        "line inspection",
    ],
    "wind": [
        "wind turbine",
        "wind farm",
    ],
    "solar": [
        "solar panel",
        "solar farm",
        "photovoltaic inverter station",
    ],
    "inspection": [
        "power equipment inspection",
        "industrial utility maintenance",
        "electric utility worker equipment",
    ],
}


def collect_public_generation_dataset(
    *,
    output_root: Path,
    provider_limits: dict[str, int] | None = None,
    min_width: int = 384,
    min_height: int = 384,
) -> dict[str, object]:
    limits = {**DEFAULT_PROVIDER_LIMITS, **(provider_limits or {})}
    output_root.mkdir(parents=True, exist_ok=True)

    openverse_rows, openverse_attr = _collect_openverse_rows(
        output_root=output_root / "openverse",
        limit=max(0, limits.get("openverse", 0)),
        min_width=min_width,
        min_height=min_height,
    )
    wikimedia_rows, wikimedia_attr = _collect_wikimedia_rows(
        output_root=output_root / "wikimedia",
        limit=max(0, limits.get("wikimedia", 0)),
        min_width=min_width,
        min_height=min_height,
    )

    return {
        "downloaded_rows": [*openverse_rows, *wikimedia_rows],
        "attribution_rows": [*openverse_attr, *wikimedia_attr],
        "provider_counts": {
            "openverse": len(openverse_rows),
            "wikimedia": len(wikimedia_rows),
        },
    }


def _collect_openverse_rows(*, output_root: Path, limit: int, min_width: int, min_height: int) -> tuple[list[dict], list[dict]]:
    if limit <= 0:
        return [], []

    rows: list[dict] = []
    attribution_rows: list[dict] = []
    seen_sources: set[str] = set()
    bucket_quota = max(1, limit // max(1, len(ELECTRIC_BUCKET_QUERIES)))

    for bucket, queries in ELECTRIC_BUCKET_QUERIES.items():
        bucket_count = 0
        for query in queries:
            if len(rows) >= limit or bucket_count >= bucket_quota:
                break

            page = 1
            while len(rows) < limit and bucket_count < bucket_quota:
                data = _fetch_openverse_page(query=query, page=page, page_size=20)
                results = data.get("results", [])
                if not results:
                    break

                accepted_this_page = 0
                for item in results:
                    source_url = str(item.get("foreign_landing_url") or item.get("url") or "").strip()
                    if not source_url or source_url in seen_sources:
                        continue
                    if not _openverse_result_is_allowed(item, min_width=min_width, min_height=min_height):
                        continue

                    downloaded = _download_provider_image(
                        image_url=str(item["url"]),
                        target_dir=output_root / bucket,
                        provider="openverse",
                        bucket=bucket,
                        slug_source=str(item.get("id") or source_url),
                    )
                    if downloaded is None:
                        continue

                    seen_sources.add(source_url)
                    caption = build_caption_from_texts(
                        bucket.replace("_", " "),
                        query,
                        str(item.get("title") or ""),
                        str(item.get("attribution") or ""),
                    )
                    rows.append(
                        {
                            "source_group": "public",
                            "provider": "openverse",
                            "bucket": bucket,
                            "query": query,
                            "path": str(downloaded),
                            "filename": downloaded.name,
                            "suffix": downloaded.suffix.lower(),
                            "size_bytes": downloaded.stat().st_size,
                            "caption": caption,
                            "source_url": source_url,
                            "license": str(item.get("license") or ""),
                            "license_url": str(item.get("license_url") or ""),
                            "author": str(item.get("creator") or ""),
                            "title": str(item.get("title") or ""),
                            "description": str(item.get("attribution") or ""),
                        }
                    )
                    attribution_row = {
                        "provider": "openverse",
                        "bucket": bucket,
                        "query": query,
                        "source_url": source_url,
                        "image_url": str(item.get("url") or ""),
                        "author": str(item.get("creator") or ""),
                        "license": str(item.get("license") or ""),
                        "license_url": str(item.get("license_url") or ""),
                        "title": str(item.get("title") or ""),
                        "detail_url": str(item.get("detail_url") or ""),
                        "path": str(downloaded),
                    }
                    attribution_rows.append(attribution_row)
                    _write_sidecar_json(downloaded, attribution_row)
                    bucket_count += 1
                    accepted_this_page += 1
                    if len(rows) >= limit or bucket_count >= bucket_quota:
                        break

                if accepted_this_page == 0 and page >= int(data.get("page_count") or 1):
                    break
                page += 1
                if page > int(data.get("page_count") or 1):
                    break

    return rows, attribution_rows


def _collect_wikimedia_rows(*, output_root: Path, limit: int, min_width: int, min_height: int) -> tuple[list[dict], list[dict]]:
    if limit <= 0:
        return [], []

    rows: list[dict] = []
    attribution_rows: list[dict] = []
    seen_sources: set[str] = set()
    bucket_quota = max(1, limit // max(1, len(ELECTRIC_BUCKET_QUERIES)))

    for bucket, queries in ELECTRIC_BUCKET_QUERIES.items():
        bucket_count = 0
        for query in queries:
            if len(rows) >= limit or bucket_count >= bucket_quota:
                break

            offset = 0
            while len(rows) < limit and bucket_count < bucket_quota:
                data = _fetch_wikimedia_page(query=query, offset=offset, page_size=20)
                pages = list((data.get("query") or {}).get("pages", {}).values())
                if not pages:
                    break

                accepted_this_page = 0
                for page in pages:
                    source_url = str(_first_imageinfo_value(page, "descriptionurl") or "").strip()
                    if not source_url or source_url in seen_sources:
                        continue
                    if not _wikimedia_page_is_allowed(page, min_width=min_width, min_height=min_height):
                        continue

                    image_url = str(_first_imageinfo_value(page, "url") or "")
                    if not image_url:
                        continue

                    downloaded = _download_provider_image(
                        image_url=image_url,
                        target_dir=output_root / bucket,
                        provider="wikimedia",
                        bucket=bucket,
                        slug_source=f"{page.get('pageid')}-{page.get('title')}",
                    )
                    if downloaded is None:
                        continue

                    title = str(page.get("title") or "")
                    description = _wikimedia_extmetadata(page, "ImageDescription")
                    caption = build_caption_from_texts(bucket.replace("_", " "), query, title, description)

                    seen_sources.add(source_url)
                    rows.append(
                        {
                            "source_group": "public",
                            "provider": "wikimedia",
                            "bucket": bucket,
                            "query": query,
                            "path": str(downloaded),
                            "filename": downloaded.name,
                            "suffix": downloaded.suffix.lower(),
                            "size_bytes": downloaded.stat().st_size,
                            "caption": caption,
                            "source_url": source_url,
                            "license": _wikimedia_extmetadata(page, "License"),
                            "license_url": _wikimedia_extmetadata(page, "LicenseUrl"),
                            "author": _wikimedia_extmetadata(page, "Artist"),
                            "title": title,
                            "description": description,
                        }
                    )
                    attribution_row = {
                        "provider": "wikimedia",
                        "bucket": bucket,
                        "query": query,
                        "source_url": source_url,
                        "image_url": image_url,
                        "author": _wikimedia_extmetadata(page, "Artist"),
                        "license": _wikimedia_extmetadata(page, "License"),
                        "license_url": _wikimedia_extmetadata(page, "LicenseUrl"),
                        "title": title,
                        "detail_url": source_url,
                        "path": str(downloaded),
                    }
                    attribution_rows.append(attribution_row)
                    _write_sidecar_json(downloaded, attribution_row)
                    bucket_count += 1
                    accepted_this_page += 1
                    if len(rows) >= limit or bucket_count >= bucket_quota:
                        break

                if accepted_this_page == 0 and "continue" not in data:
                    break
                if "continue" not in data:
                    break
                offset = int((data["continue"] or {}).get("gsroffset") or 0)
                if offset <= 0:
                    break

    return rows, attribution_rows


def _fetch_openverse_page(*, query: str, page: int, page_size: int) -> dict[str, Any]:
    params = {
        "q": query,
        "page": str(page),
        "page_size": str(page_size),
        "license": ",".join(sorted(ALLOWED_OPENVERSE_LICENSES)),
    }
    return _fetch_json(f"{OPENVERSE_ENDPOINT}?{urlencode(params)}")


def _fetch_wikimedia_page(*, query: str, offset: int, page_size: int) -> dict[str, Any]:
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": "6",
        "gsroffset": str(offset),
        "gsrlimit": str(page_size),
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "format": "json",
    }
    return _fetch_json(f"{WIKIMEDIA_ENDPOINT}?{urlencode(params)}")


def _fetch_json(url: str) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=15) as response:
        return json.load(response)


def _download_provider_image(*, image_url: str, target_dir: Path, provider: str, bucket: str, slug_source: str) -> Path | None:
    suffix = _resolve_suffix(image_url)
    if suffix not in ALLOWED_SUFFIXES:
        return None

    target_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha1(slug_source.encode("utf-8")).hexdigest()[:16]
    target_path = target_dir / f"{provider}_{bucket}_{digest}{suffix}"
    if target_path.exists():
        return target_path

    request = Request(image_url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=15) as response:
            payload = response.read()
    except Exception:
        return None

    if not payload:
        return None
    target_path.write_bytes(payload)
    if not _validate_downloaded_image(target_path):
        return None
    return target_path


def _validate_downloaded_image(path: Path, *, min_width: int = 384, min_height: int = 384) -> bool:
    try:
        with Image.open(path) as image:
            width, height = image.size
            image.verify()
        if width < min_width or height < min_height:
            path.unlink(missing_ok=True)
            return False
    except (UnidentifiedImageError, OSError):
        path.unlink(missing_ok=True)
        return False
    return True


def _write_sidecar_json(path: Path, payload: dict[str, Any]) -> None:
    sidecar_path = path.with_suffix(f"{path.suffix}.json")
    sidecar_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _resolve_suffix(url: str) -> str:
    path = urlparse(url).path.lower()
    suffix = Path(path).suffix
    return suffix if suffix in ALLOWED_SUFFIXES else ""


def _openverse_result_is_allowed(item: dict[str, Any], *, min_width: int, min_height: int) -> bool:
    license_name = str(item.get("license") or "").strip().lower()
    if license_name not in ALLOWED_OPENVERSE_LICENSES:
        return False
    width = int(item.get("width") or 0)
    height = int(item.get("height") or 0)
    if width < min_width or height < min_height:
        return False
    image_url = str(item.get("url") or "")
    return _resolve_suffix(image_url) in ALLOWED_SUFFIXES


def _wikimedia_page_is_allowed(page: dict[str, Any], *, min_width: int, min_height: int) -> bool:
    image_url = str(_first_imageinfo_value(page, "url") or "")
    if _resolve_suffix(image_url) not in ALLOWED_SUFFIXES:
        return False
    license_name = _wikimedia_extmetadata(page, "License").lower()
    if not _wikimedia_license_allowed(license_name):
        return False

    extmetadata = _first_imageinfo_value(page, "extmetadata") or {}
    width = int(extmetadata.get("ImageWidth", {}).get("value") or 0)
    height = int(extmetadata.get("ImageHeight", {}).get("value") or 0)
    if width and height:
        return width >= min_width and height >= min_height
    return True


def _wikimedia_license_allowed(license_name: str) -> bool:
    if not license_name:
        return False
    normalized = license_name.lower()
    return normalized.startswith("cc-by") or normalized.startswith("cc0") or normalized.startswith("pd")


def _first_imageinfo_value(page: dict[str, Any], key: str) -> Any:
    imageinfo = page.get("imageinfo") or []
    if not imageinfo:
        return None
    return imageinfo[0].get(key)


def _wikimedia_extmetadata(page: dict[str, Any], key: str) -> str:
    extmetadata = _first_imageinfo_value(page, "extmetadata") or {}
    raw_value = str((extmetadata.get(key) or {}).get("value") or "")
    return _strip_html(raw_value)


def _strip_html(value: str) -> str:
    return unescape(re.sub(r"<[^>]+>", " ", value)).replace("\n", " ").strip()
