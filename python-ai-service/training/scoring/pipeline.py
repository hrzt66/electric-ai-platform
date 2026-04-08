from __future__ import annotations

import json
import shutil
from pathlib import Path

from app.core.settings import Settings, get_settings
from training.common.paths import TrainingPaths
from training.scoring.config import ScoringTrainingConfig


def run_scoring_training(
    *,
    settings: Settings | None = None,
    config: ScoringTrainingConfig | None = None,
) -> TrainingPaths:
    runtime_settings = settings or get_settings()
    training_config = config or ScoringTrainingConfig()
    paths = TrainingPaths.from_settings(runtime_settings)
    paths.ensure_directories()

    bundle_dir = runtime_settings.scoring_model_dir / training_config.bundle_name
    bundle_dir.mkdir(parents=True, exist_ok=True)

    yolo_source = _resolve_yolo_source(runtime_settings, training_config)
    if yolo_source is not None:
        shutil.copy2(yolo_source, bundle_dir / "yolo_aux.pt")

    _write_json(bundle_dir / "bundle_config.json", training_config.bundle_payload())
    _write_json(
        bundle_dir / "bundle_manifest.json",
        {
            "project_root": str(paths.scoring_training_root),
            "export_root": str(bundle_dir),
            "runtime_type": training_config.runtime_type,
            "source_detector_bundle": training_config.source_detector_bundle_name,
            "yolo_source": str(yolo_source) if yolo_source else "",
        },
    )
    _write_json(
        bundle_dir / "metrics.json",
        {
            "bundle_dir": str(bundle_dir),
            "runtime_type": training_config.runtime_type,
            "weights": training_config.total_weights,
            "teacher_models": training_config.bundle_payload()["teacher_models"],
        },
    )
    _write_json(
        paths.scoring_training_root / "training_plan.json",
        {
            "bundle_dir": str(bundle_dir),
            "runtime_type": training_config.runtime_type,
            "targets": training_config.targets,
            "classes": training_config.classes,
        },
    )
    return paths


def _resolve_yolo_source(settings: Settings, config: ScoringTrainingConfig) -> Path | None:
    candidates = [
        settings.scoring_model_dir / config.source_detector_bundle_name / "yolo_aux.pt",
        settings.runtime_root / "training" / "power-four-score" / "artifacts" / "yolo" / "electric-aux-detector" / "weights" / "best.pt",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
