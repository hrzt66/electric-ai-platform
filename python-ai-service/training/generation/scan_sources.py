from __future__ import annotations

from pathlib import Path

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def scan_image_roots(source_group: str, roots: list[Path]) -> list[dict]:
    rows: list[dict] = []
    for root in roots:
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
                continue
            size_bytes = path.stat().st_size
            if size_bytes <= 0:
                continue
            rows.append(
                {
                    "source_group": source_group,
                    "path": str(path),
                    "filename": path.name,
                    "suffix": path.suffix.lower(),
                    "size_bytes": size_bytes,
                }
            )
    return rows
