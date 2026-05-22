from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_project_root_on_path
except ImportError:  # pragma: no cover - direct script execution path
    from bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from training.scoring.yolo_dataset_tools import import_external_image2_yolo_run_for_scoring


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import an external Image-2 YOLO run into the scoring 6-class dataset and bundle.")
    parser.add_argument("--source-run-dir", type=Path, required=True, help="External YOLO run directory containing best.pt and dataset.yaml.")
    parser.add_argument(
        "--dataset-target",
        type=Path,
        default=Path("datasets/yolo-image2-remapped-scoring-6class-v1"),
        help="Primary remapped 6-class dataset target root.",
    )
    parser.add_argument(
        "--training-target",
        type=Path,
        default=Path("model/training/scoring/electric-score-v2/yolo-image2-remapped-scoring-6class-v1"),
        help="Training-side remapped 6-class dataset target root.",
    )
    parser.add_argument(
        "--bundle-dir",
        type=Path,
        default=Path("model/scoring/electric-score-v2"),
        help="Scoring bundle directory that should receive yolo_aux.pt.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    report = import_external_image2_yolo_run_for_scoring(
        source_run_dir=args.source_run_dir,
        target_roots=[args.dataset_target, args.training_target],
        bundle_dir=args.bundle_dir,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
