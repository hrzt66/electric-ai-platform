from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_project_root_on_path
except ImportError:  # pragma: no cover - direct script execution path
    from bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from training.scoring.yolo_dataset_tools import build_high_map_variant, clean_yolo_dataset, rebuild_yolo_merged_artifacts


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean merged YOLO labels and rebuild manifest/summary artifacts.")
    parser.add_argument("--training-root", type=Path, required=True, help="Path like model/training/scoring/electric-score-v2.")
    parser.add_argument(
        "--variant",
        type=str,
        choices=("none", "high_map_v1"),
        default="none",
        help="Optional merged-dataset variant to build after cleaning.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    merged_root = args.training_root / "yolo-merged"
    cleanup = clean_yolo_dataset(merged_root)
    summary = rebuild_yolo_merged_artifacts(args.training_root)
    payload: dict[str, object] = {"cleanup": cleanup, "summary": summary}
    if args.variant == "high_map_v1":
        payload["variant"] = build_high_map_variant(
            merged_root=merged_root,
            variant_root=args.training_root / "yolo-merged-high-map-v1",
            max_repeat_by_class={
                "substation_primary": 2,
                "solar_panel": 3,
                "dam": 2,
            },
            min_box_area=0.0004,
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
