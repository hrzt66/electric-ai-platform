from __future__ import annotations

from pathlib import Path

from training.generation.captioning import apply_stub_caption
from training.generation.dedupe import dedupe_rows_by_fingerprint
from training.generation.scan_sources import scan_image_roots


def build_generation_manifest(
    *,
    public_roots: list[Path],
    local_roots: list[Path],
    external_roots: list[Path],
    precomputed_rows: list[dict] | None = None,
) -> list[dict]:
    rows: list[dict] = list(precomputed_rows or [])
    rows.extend(scan_image_roots("public", public_roots))
    rows.extend(scan_image_roots("local", local_roots))
    rows.extend(scan_image_roots("external", external_roots))
    deduped_rows = dedupe_rows_by_fingerprint(sorted(rows, key=lambda item: item["path"]))
    return [apply_stub_caption(row) for row in deduped_rows]
