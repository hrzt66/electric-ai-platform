from __future__ import annotations

import argparse
import json
import shutil
from collections import defaultdict
from pathlib import Path
import sys
from typing import Any

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from training.scoring.physical_parts import PHYSICAL_PART_CLASS_NAMES

SOURCE_CLASS_ID_TO_PARENT = {
    0: "substation_primary",
    1: "transmission_tower",
    2: "insulator_string",
    3: "wind_turbine",
    4: "solar_panel",
    5: "dam",
}

PHYSICAL_PART_CLASS_TO_INDEX = {
    class_name: index for index, class_name in enumerate(PHYSICAL_PART_CLASS_NAMES)
}


def _iter_source_label_files(source_root: Path):
    labels_root = source_root / "labels"
    for split in ("train", "val", "test"):
        split_dir = labels_root / split
        if not split_dir.exists():
            continue
        for label_path in sorted(split_dir.glob("*.txt")):
            yield split, label_path


def _source_image_for_label(source_root: Path, split: str, stem: str) -> Path | None:
    image_dir = source_root / "images" / split
    for suffix in (".png", ".jpg", ".jpeg", ".webp"):
        candidate = image_dir / f"{stem}{suffix}"
        if candidate.exists():
            return candidate
    return None


def _read_source_parent_classes(label_path: Path) -> set[str]:
    parents: set[str] = set()
    for line in label_path.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split()
        if len(parts) < 5:
            continue
        class_id = int(float(parts[0]))
        parent = SOURCE_CLASS_ID_TO_PARENT.get(class_id)
        if parent is not None:
            parents.add(parent)
    return parents


def export_source_images(*, source_root: Path, output_root: Path, per_class_limit: int = 40) -> dict[str, Any]:
    copied = 0
    per_parent_count: dict[str, int] = defaultdict(int)
    for split, label_path in _iter_source_label_files(source_root):
        parents = _read_source_parent_classes(label_path)
        if not parents:
            continue
        image_path = _source_image_for_label(source_root, split, label_path.stem)
        if image_path is None:
            continue
        dominant_parent = sorted(parents)[0]
        if per_parent_count[dominant_parent] >= per_class_limit:
            continue
        target_dir = output_root / "images" / split
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(image_path, target_dir / image_path.name)
        per_parent_count[dominant_parent] += 1
        copied += 1
    return {
        "copied_count": copied,
        "per_parent_count": dict(sorted(per_parent_count.items())),
    }


def _xyxy_to_yolo_bbox(*, bbox_xyxy: list[float], width: int, height: int) -> list[float]:
    x1, y1, x2, y2 = [float(value) for value in bbox_xyxy]
    cx = ((x1 + x2) / 2.0) / width
    cy = ((y1 + y2) / 2.0) / height
    bw = (x2 - x1) / width
    bh = (y2 - y1) / height
    return [cx, cy, bw, bh]


def _find_image_in_dataset(dataset_root: Path, image_name: str) -> tuple[str, Path] | None:
    for split in ("train", "val", "test"):
        candidate = dataset_root / "images" / split / image_name
        if candidate.exists():
            return split, candidate
    return None


def convert_annotations_to_yolo_labels(*, dataset_root: Path, annotation_path: Path) -> dict[str, Any]:
    written = 0
    for raw_line in annotation_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        row = json.loads(line)
        image_name = str(row["image_name"])
        located = _find_image_in_dataset(dataset_root, image_name)
        if located is None:
            continue
        split, image_path = located
        width, height = Image.open(image_path).size
        label_dir = dataset_root / "labels" / split
        label_dir.mkdir(parents=True, exist_ok=True)
        lines: list[str] = []
        for annotation in row.get("annotations", []):
            class_name = str(annotation["class_name"])
            if class_name not in PHYSICAL_PART_CLASS_TO_INDEX:
                raise ValueError(f"unknown physical part class in annotations: {class_name}")
            bbox = _xyxy_to_yolo_bbox(
                bbox_xyxy=list(annotation["bbox_xyxy"]),
                width=width,
                height=height,
            )
            lines.append(
                f"{PHYSICAL_PART_CLASS_TO_INDEX[class_name]} {bbox[0]:.6f} {bbox[1]:.6f} {bbox[2]:.6f} {bbox[3]:.6f}"
            )
        (label_dir / f"{Path(image_name).stem}.txt").write_text(
            "\n".join(lines) + ("\n" if lines else ""),
            encoding="utf-8",
        )
        written += 1
    return {
        "written_label_count": written,
        "annotation_path": str(annotation_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare YOLO physical parts dataset from existing 6-class source dataset.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export-images")
    export_parser.add_argument("--source-root", required=True)
    export_parser.add_argument("--output-root", required=True)
    export_parser.add_argument("--per-class-limit", type=int, default=40)

    convert_parser = subparsers.add_parser("convert-labels")
    convert_parser.add_argument("--dataset-root", required=True)
    convert_parser.add_argument("--annotation-path", required=True)

    args = parser.parse_args()
    if args.command == "export-images":
        summary = export_source_images(
            source_root=Path(args.source_root),
            output_root=Path(args.output_root),
            per_class_limit=args.per_class_limit,
        )
    else:
        summary = convert_annotations_to_yolo_labels(
            dataset_root=Path(args.dataset_root),
            annotation_path=Path(args.annotation_path),
        )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
