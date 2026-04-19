from __future__ import annotations

import argparse
import json

try:
    from scripts.bootstrap import ensure_project_root_on_path
except ImportError:  # pragma: no cover - direct script execution path
    from bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from training.scoring.config import ScoringTrainingConfig
from training.scoring.pipeline import run_scoring_training


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the electric four-dimension scoring model.")
    parser.add_argument("--epochs", type=int, default=None, help="Epochs for the main scoring model.")
    parser.add_argument("--yolo-epochs", type=int, default=None, help="Epochs for the YOLO auxiliary model.")
    parser.add_argument("--device", type=str, default=None, help="Preferred device: mps, cuda, or cpu.")
    parser.add_argument("--yolo-imgsz", type=int, default=None, help="YOLO image size.")
    parser.add_argument("--yolo-batch-size", type=int, default=None, help="YOLO batch size.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    config = ScoringTrainingConfig()
    if args.epochs is not None:
        config.epochs = args.epochs
    if args.yolo_epochs is not None:
        config.yolo_epochs = args.yolo_epochs
    if args.device is not None:
        config.device_preference = args.device
    if args.yolo_imgsz is not None:
        config.yolo_image_size = args.yolo_imgsz
    if args.yolo_batch_size is not None:
        config.yolo_batch_size = args.yolo_batch_size
    report = run_scoring_training(config=config)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
