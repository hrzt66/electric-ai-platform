from __future__ import annotations

from pathlib import Path

from app.core.settings import Settings, get_settings
from training.common.jsonl import write_jsonl
from training.common.paths import TrainingPaths
from training.generation.build_manifest import build_generation_manifest


def prepare_generation_dataset(
    *,
    settings: Settings | None = None,
    public_roots: list[Path] | None = None,
    local_roots: list[Path] | None = None,
    external_roots: list[Path] | None = None,
) -> dict[str, object]:
    runtime_settings = settings or get_settings()
    paths = TrainingPaths.from_settings(runtime_settings)
    paths.ensure_directories()

    manifest_rows = build_generation_manifest(
        public_roots=public_roots or [],
        local_roots=local_roots or [],
        external_roots=external_roots or [],
    )

    manifest_path = paths.generation_dataset_root / "manifests" / "raw_manifest.jsonl"
    write_jsonl(manifest_path, manifest_rows)

    return {
        "manifest_path": str(manifest_path),
        "count": len(manifest_rows),
    }
