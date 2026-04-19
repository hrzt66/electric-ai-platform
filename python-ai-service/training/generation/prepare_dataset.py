from __future__ import annotations

from pathlib import Path

from app.core.settings import Settings, get_settings
from training.common.jsonl import write_jsonl
from training.common.paths import TrainingPaths
from training.generation.build_manifest import build_generation_manifest
from training.generation.public_dataset import collect_public_generation_dataset


def prepare_generation_dataset(
    *,
    settings: Settings | None = None,
    public_roots: list[Path] | None = None,
    local_roots: list[Path] | None = None,
    external_roots: list[Path] | None = None,
    include_public_downloads: bool = False,
    provider_limits: dict[str, int] | None = None,
) -> dict[str, object]:
    runtime_settings = settings or get_settings()
    paths = TrainingPaths.from_settings(runtime_settings)
    paths.ensure_directories()

    downloaded_rows: list[dict] = []
    attribution_rows: list[dict] = []
    provider_counts: dict[str, int] = {}
    if include_public_downloads:
        public_report = collect_public_generation_dataset(
            output_root=paths.generation_dataset_root / "raw",
            provider_limits=provider_limits,
        )
        downloaded_rows = list(public_report["downloaded_rows"])
        attribution_rows = list(public_report["attribution_rows"])
        provider_counts = dict(public_report["provider_counts"])

    manifest_rows = build_generation_manifest(
        public_roots=public_roots or [],
        local_roots=local_roots or [],
        external_roots=external_roots or [],
        precomputed_rows=downloaded_rows,
    )

    manifest_path = paths.generation_dataset_root / "manifests" / "raw_manifest.jsonl"
    attribution_manifest_path = paths.generation_dataset_root / "manifests" / "attribution_manifest.jsonl"
    write_jsonl(manifest_path, manifest_rows)
    write_jsonl(attribution_manifest_path, attribution_rows)

    return {
        "manifest_path": str(manifest_path),
        "attribution_manifest_path": str(attribution_manifest_path),
        "count": len(manifest_rows),
        "public_download_count": len(downloaded_rows),
        "attribution_count": len(attribution_rows),
        "provider_counts": provider_counts,
    }
