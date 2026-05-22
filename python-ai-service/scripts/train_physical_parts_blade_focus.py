from __future__ import annotations

import json

try:
    from scripts.bootstrap import ensure_project_root_on_path
except ImportError:  # pragma: no cover
    from bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from app.core.settings import get_settings
from training.scoring.config import ScoringTrainingConfig
from training.scoring.pipeline import _train_physical_part_yolo_auxiliary
from training.scoring.modeling import choose_training_device
from training.common.paths import TrainingPaths


def main() -> int:
    settings = get_settings()
    paths = TrainingPaths.from_settings(settings)
    paths.ensure_directories()

    config = ScoringTrainingConfig(
        device_preference="mps",
        yolo_epochs=50,
        physical_part_yolo_dataset_yaml="datasets/yolo-physical-parts-v1/dataset.yaml",
        physical_part_yolo_profile="electric_physical_parts_wind_blade_only_v1",
        physical_part_yolo_train_variant="wind_blade_only_v1",
        reuse_existing_physical_part_yolo_aux=False,
    )
    device = choose_training_device(config.device_preference)
    bundle_dir = settings.scoring_model_dir / config.bundle_name
    bundle_dir.mkdir(parents=True, exist_ok=True)
    report = _train_physical_part_yolo_auxiliary(
        training_root=paths.scoring_training_root,
        bundle_dir=bundle_dir,
        config=config,
        device=device,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
