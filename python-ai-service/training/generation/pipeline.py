from __future__ import annotations

import json
import re
import shutil
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Callable

from app.core.settings import Settings, get_settings
from training.common.jsonl import read_jsonl, write_jsonl
from training.common.paths import TrainingPaths
from training.generation.config import GenerationTrainingConfig
from training.generation.evaluate import evaluate_generation_model
from training.generation.merge_lora import merge_lora_weights
from training.generation.prepare_dataset import prepare_generation_dataset
from training.generation.train_lora import (
    build_lora_train_command,
    download_diffusers_lora_script,
    run_lora_training,
)


def _load_manifest_rows(manifest_path: Path) -> list[dict]:
    if not manifest_path.exists():
        raise FileNotFoundError(f"generation manifest not found: {manifest_path}")
    return list(read_jsonl(manifest_path))


def ensure_generation_dataset_ready(*, settings: Settings) -> dict[str, object]:
    paths = TrainingPaths.from_settings(settings)
    manifest_path = paths.generation_dataset_root / "manifests" / "raw_manifest.jsonl"
    if manifest_path.exists() and any(read_jsonl(manifest_path)):
        return {"manifest_path": str(manifest_path), "count": len(list(read_jsonl(manifest_path)))}
    return prepare_generation_dataset(
        settings=settings,
        public_roots=[],
        local_roots=[],
        external_roots=[],
        include_public_downloads=True,
    )


def _select_rows(rows: list[dict], max_samples: int | None) -> list[dict]:
    if max_samples is None or max_samples >= len(rows):
        return rows
    return rows[:max_samples]


def _export_curated_dataset(rows: list[dict], curated_root: Path) -> tuple[list[dict], Path]:
    images_dir = curated_root / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    metadata_rows: list[dict] = []
    for index, row in enumerate(rows):
        suffix = row.get("suffix", Path(row["path"]).suffix or ".png")
        fingerprint = row.get("fingerprint", f"sample{index:06d}")
        target_name = f"{index:06d}_{fingerprint[:12]}{suffix}"
        target_path = images_dir / target_name
        if not target_path.exists():
            shutil.copy2(row["path"], target_path)
        metadata_rows.append(
            {
                "file_name": f"images/{target_name}",
                "text": row["caption"],
                "source_group": row["source_group"],
                "original_path": row["path"],
            }
        )

    metadata_path = curated_root / "metadata.jsonl"
    write_jsonl(metadata_path, metadata_rows)
    return metadata_rows, metadata_path


def remove_obsolete_specialized_artifacts(settings: Settings) -> dict[str, object]:
    targets = [
        settings.runtime_root / "training" / "generation" / "sd15-electric-specialized",
        settings.generation_model_dir / "sd15-electric-specialized",
        settings.runtime_root / "generation" / "sd15-electric-specialized",
    ]
    removed_paths: list[str] = []
    for target in targets:
        if target.exists():
            shutil.rmtree(target)
            removed_paths.append(str(target))
    return {"removed_paths": removed_paths}


def select_best_generation_checkpoint(*, lora_output_dir: Path) -> Path:
    candidates: list[tuple[int, Path]] = []
    for path in lora_output_dir.glob("checkpoint-*"):
        match = re.fullmatch(r"checkpoint-(\d+)", path.name)
        if match and path.is_dir():
            candidates.append((int(match.group(1)), path))
    if not candidates:
        return lora_output_dir
    candidates.sort(key=lambda item: item[0])
    return candidates[-1][1]


def prepare_generation_training_workspace(
    *,
    settings: Settings | None = None,
    config: GenerationTrainingConfig | None = None,
    python_executable: str | None = None,
    download_script_fn: Callable[[Path], Path] | None = None,
    enable_validation: bool = True,
) -> dict[str, object]:
    runtime_settings = settings or get_settings()
    training_config = config or GenerationTrainingConfig()
    paths = TrainingPaths.from_settings(runtime_settings)
    paths.ensure_directories()

    ensure_generation_dataset_ready(settings=runtime_settings)
    manifest_path = paths.generation_dataset_root / "manifests" / "raw_manifest.jsonl"
    all_rows = _load_manifest_rows(manifest_path)
    selected_rows = _select_rows(all_rows, training_config.max_train_samples)

    curated_root = paths.generation_dataset_root / "curated"
    metadata_rows, metadata_path = _export_curated_dataset(selected_rows, curated_root)

    tools_dir = paths.generation_training_root / "tools"
    train_script_path = (
        download_script_fn(tools_dir)
        if download_script_fn is not None
        else download_diffusers_lora_script(tools_dir, training_config.diffusers_example_ref)
    )

    lora_output_dir = paths.generation_training_root / "lora-output"
    merged_model_dir = training_config.resolve_output_model_dir(runtime_settings)
    evaluation_dir = paths.generation_training_root / "evaluation"
    command = build_lora_train_command(
        config=training_config,
        train_script_path=train_script_path,
        curated_dataset_dir=curated_root,
        lora_output_dir=lora_output_dir,
        settings=runtime_settings,
        python_executable=python_executable or sys.executable,
        enable_validation=enable_validation,
    )

    plan_path = paths.generation_training_root / "training_plan.json"
    plan_payload = {
        "manifest_path": str(manifest_path),
        "curated_dataset_dir": str(curated_root),
        "metadata_path": str(metadata_path),
        "sample_count": len(metadata_rows),
        "train_script_path": str(train_script_path),
        "lora_output_dir": str(lora_output_dir),
        "merged_model_dir": str(merged_model_dir),
        "evaluation_dir": str(evaluation_dir),
        "train_command": command,
        "config": asdict(training_config),
    }
    plan_path.write_text(json.dumps(plan_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return plan_payload


def run_generation_training(
    *,
    settings: Settings | None = None,
    config: GenerationTrainingConfig | None = None,
    python_executable: str | None = None,
    download_script_fn: Callable[[Path], Path] | None = None,
    prepare_only: bool = False,
    skip_merge: bool = False,
    skip_eval: bool = False,
) -> dict[str, object]:
    runtime_settings = settings or get_settings()
    training_config = config or GenerationTrainingConfig()
    report = prepare_generation_training_workspace(
        settings=runtime_settings,
        config=training_config,
        python_executable=python_executable,
        download_script_fn=download_script_fn,
        enable_validation=not skip_eval,
    )

    if prepare_only:
        report["status"] = "prepared"
        return report

    cleanup_report = remove_obsolete_specialized_artifacts(runtime_settings)
    report["cleanup"] = cleanup_report

    run_lora_training(
        command=list(report["train_command"]),
        workdir=Path(report["lora_output_dir"]).parent,
        settings=runtime_settings,
    )
    report["status"] = "trained"
    best_lora_checkpoint_dir = select_best_generation_checkpoint(
        lora_output_dir=Path(report["lora_output_dir"]),
    )
    report["best_lora_checkpoint_dir"] = str(best_lora_checkpoint_dir)

    if not skip_merge:
        merged_model_dir = merge_lora_weights(
            base_model_name_or_path=training_config.resolve_base_model_source(runtime_settings),
            lora_output_dir=best_lora_checkpoint_dir,
            merged_model_dir=Path(report["merged_model_dir"]),
        )
        report["merged_model_dir"] = str(merged_model_dir)

    if not skip_eval and not skip_merge:
        evaluation = evaluate_generation_model(
            model_dir=Path(report["merged_model_dir"]),
            output_dir=Path(report["evaluation_dir"]),
            config=training_config,
        )
        report["evaluation"] = evaluation

    return report
