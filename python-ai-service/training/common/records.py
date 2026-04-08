from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ImageManifestRecord:
    source_group: str
    path: str
    filename: str
    suffix: str
    size_bytes: int
    caption: str = ""
