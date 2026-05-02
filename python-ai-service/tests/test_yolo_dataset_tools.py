from __future__ import annotations

import csv
import json
from pathlib import Path

from PIL import Image


def _write_image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (64, 64), color=(128, 140, 152)).save(path)


def test_canonicalize_yolo_label_line_clips_boxes_and_rejects_zero_area() -> None:
    from training.scoring.yolo_dataset_tools import canonicalize_yolo_label_line

    clipped_line, clipped_meta = canonicalize_yolo_label_line("3 1.000000 0.500000 0.400000 0.400000")
    dropped_line, dropped_meta = canonicalize_yolo_label_line("4 0.500000 0.500000 0.100000 0.000000")

    assert clipped_line == "3 0.900000 0.500000 0.200000 0.400000"
    assert clipped_meta["boxes_clipped"] == 1
    assert clipped_meta["lines_kept"] == 1

    assert dropped_line is None
    assert dropped_meta["lines_dropped"] == 1
    assert dropped_meta["dropped_zero_area"] == 1


def test_clean_yolo_dataset_deduplicates_labels_and_removes_empty_examples(tmp_path: Path) -> None:
    from training.scoring.yolo_dataset_tools import clean_yolo_dataset

    merged_root = tmp_path / "yolo-merged"
    (merged_root / "images" / "train").mkdir(parents=True, exist_ok=True)
    (merged_root / "labels" / "train").mkdir(parents=True, exist_ok=True)

    kept_image = merged_root / "images" / "train" / "0_keep.jpg"
    kept_label = merged_root / "labels" / "train" / "0_keep.txt"
    _write_image(kept_image)
    kept_label.write_text(
        "\n".join(
            [
                "0 0.500000 0.500000 0.250000 0.250000",
                "0 0.500000 0.500000 0.250000 0.250000",
            ]
        ),
        encoding="utf-8",
    )

    removed_image = merged_root / "images" / "train" / "1_drop.jpg"
    removed_label = merged_root / "labels" / "train" / "1_drop.txt"
    _write_image(removed_image)
    removed_label.write_text(
        "\n".join(
            [
                "6 0.852480 0.223278 0.846231 0.177939 0.818111 0.123220",
                "4 0.500000 0.500000 0.100000 0.000000",
            ]
        ),
        encoding="utf-8",
    )

    report = clean_yolo_dataset(merged_root)

    assert report["files_changed"] == 2
    assert report["duplicates_removed"] == 1
    assert report["images_removed"] == 1
    assert kept_label.read_text(encoding="utf-8").splitlines() == ["0 0.500000 0.500000 0.250000 0.250000"]
    assert kept_image.exists() is True
    assert removed_label.exists() is False
    assert removed_image.exists() is False


def test_rebuild_yolo_merged_artifacts_filters_missing_rows_and_writes_current_summaries(tmp_path: Path) -> None:
    from training.scoring.yolo_dataset_tools import rebuild_yolo_merged_artifacts

    training_root = tmp_path / "electric-score-v2"
    merged_root = training_root / "yolo-merged"
    kept_image = merged_root / "images" / "train" / "0_keep.jpg"
    kept_label = merged_root / "labels" / "train" / "0_keep.txt"
    dropped_manifest_image = merged_root / "images" / "val" / "1_missing.jpg"
    orphan_image = merged_root / "images" / "train" / "1_powerline-components-and-faults_00001.jpg"
    orphan_label = merged_root / "labels" / "train" / "1_powerline-components-and-faults_00001.txt"
    _write_image(kept_image)
    kept_label.parent.mkdir(parents=True, exist_ok=True)
    kept_label.write_text("0 0.500000 0.500000 0.250000 0.250000", encoding="utf-8")
    _write_image(orphan_image)
    orphan_label.parent.mkdir(parents=True, exist_ok=True)
    orphan_label.write_text("1 0.400000 0.400000 0.200000 0.200000", encoding="utf-8")
    (merged_root / "dataset.yaml").write_text(
        "path: .\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n  - substation_primary\n  - transmission_tower\n",
        encoding="utf-8",
    )

    source_root = tmp_path / "raw" / "source-a"
    (source_root / "images" / "train").mkdir(parents=True, exist_ok=True)
    (source_root / "labels" / "train").mkdir(parents=True, exist_ok=True)
    (source_root / "dataset.yaml").write_text(
        f"path: {source_root}\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n  - substation_primary\n",
        encoding="utf-8",
    )
    original_image = source_root / "images" / "train" / "keep.jpg"
    original_label = source_root / "labels" / "train" / "keep.txt"
    _write_image(original_image)
    original_label.write_text("0 0.500000 0.500000 0.250000 0.250000", encoding="utf-8")

    manifest_csv = training_root / "yolo_merged_image_manifest.csv"
    exact_csv = training_root / "yolo_merged_exact_images_current_run.csv"
    for csv_path, has_dataset_index in ((manifest_csv, True), (exact_csv, False)):
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with csv_path.open("w", encoding="utf-8", newline="") as file:
            if has_dataset_index:
                writer = csv.DictWriter(
                    file,
                    fieldnames=["split", "merged_image", "dataset_index", "source_name", "original_image", "original_label"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "split": "train",
                        "merged_image": str(kept_image),
                        "dataset_index": "0",
                        "source_name": "source-a",
                        "original_image": str(original_image),
                        "original_label": str(original_label),
                    }
                )
                writer.writerow(
                    {
                        "split": "val",
                        "merged_image": str(dropped_manifest_image),
                        "dataset_index": "1",
                        "source_name": "source-b",
                        "original_image": str(tmp_path / "missing.jpg"),
                        "original_label": str(tmp_path / "missing.txt"),
                    }
                )
            else:
                writer = csv.DictWriter(
                    file,
                    fieldnames=["split", "merged_image", "prefix", "source_name", "original_image", "original_label"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "split": "train",
                        "merged_image": str(kept_image),
                        "prefix": "0",
                        "source_name": "source-a",
                        "original_image": str(original_image),
                        "original_label": str(original_label),
                    }
                )
                writer.writerow(
                    {
                        "split": "val",
                        "merged_image": str(dropped_manifest_image),
                        "prefix": "1",
                        "source_name": "source-b",
                        "original_image": str(tmp_path / "missing.jpg"),
                        "original_label": str(tmp_path / "missing.txt"),
                    }
                )

    report = rebuild_yolo_merged_artifacts(training_root)

    source_summary = json.loads((training_root / "yolo_merged_source_summary.json").read_text(encoding="utf-8"))
    exact_summary = json.loads((training_root / "yolo_merged_exact_images_current_run_summary.json").read_text(encoding="utf-8"))

    assert report["counts_total"] == {"train": 2, "val": 0, "test": 0}
    assert report["active_classes"] == ["substation_primary", "transmission_tower"]
    assert source_summary["counts_total"] == {"train": 2, "val": 0, "test": 0}
    assert source_summary["counts_by_source"]["source-a"] == {"train": 1, "val": 0, "test": 0}
    assert source_summary["counts_by_source"]["powerline-components-and-faults"] == {"train": 1, "val": 0, "test": 0}
    assert exact_summary["counts_by_source"]["source-a"] == {"train": 1, "val": 0, "test": 0}
    assert exact_summary["counts_by_source"]["powerline-components-and-faults"] == {"train": 1, "val": 0, "test": 0}
    assert exact_summary["total_rows"] == 2

    with manifest_csv.open("r", encoding="utf-8", newline="") as file:
        manifest_rows = list(csv.DictReader(file))
    with exact_csv.open("r", encoding="utf-8", newline="") as file:
        exact_rows = list(csv.DictReader(file))

    assert len(manifest_rows) == 2
    assert len(exact_rows) == 2
    assert manifest_rows[0]["source_name"] == "source-a"
    assert manifest_rows[1]["source_name"] == "powerline-components-and-faults"
    assert exact_rows[0]["source_name"] == "source-a"
    assert exact_rows[1]["source_name"] == "powerline-components-and-faults"


def test_build_high_map_variant_rebalances_without_extreme_repeats(tmp_path: Path) -> None:
    from training.scoring.yolo_dataset_tools import build_high_map_variant

    merged_root = tmp_path / "yolo-merged"
    for split in ("train", "val", "test"):
        (merged_root / "images" / split).mkdir(parents=True, exist_ok=True)
        (merged_root / "labels" / split).mkdir(parents=True, exist_ok=True)

    ppe_image = merged_root / "images" / "train" / "0_ppe.jpg"
    ppe_label = merged_root / "labels" / "train" / "0_ppe.txt"
    tower_image = merged_root / "images" / "train" / "1_tower.jpg"
    tower_label = merged_root / "labels" / "train" / "1_tower.txt"
    val_image = merged_root / "images" / "val" / "2_val.jpg"
    val_label = merged_root / "labels" / "val" / "2_val.txt"
    _write_image(ppe_image)
    _write_image(tower_image)
    _write_image(val_image)
    ppe_label.write_text("6 0.500000 0.500000 0.300000 0.300000", encoding="utf-8")
    tower_label.write_text("1 0.500000 0.500000 0.250000 0.250000", encoding="utf-8")
    val_label.write_text("6 0.500000 0.500000 0.300000 0.300000", encoding="utf-8")
    (merged_root / "dataset.yaml").write_text(
        "\n".join(
            [
                f"path: {merged_root}",
                "train: images/train",
                "val: images/val",
                "test: images/test",
                "names:",
                "  - substation_primary",
                "  - transmission_tower",
                "  - insulator_string",
                "  - wind_turbine",
                "  - solar_panel",
                "  - dam",
                "  - maintenance_ppe",
            ]
        ),
        encoding="utf-8",
    )

    variant_root = tmp_path / "yolo-merged-high-map-v1"
    report = build_high_map_variant(
        merged_root=merged_root,
        variant_root=variant_root,
        max_repeat_by_class={"maintenance_ppe": 3, "solar_panel": 3, "dam": 2},
        min_box_area=0.01,
    )

    assert report["variant_name"] == "high_map_v1"
    assert report["original_train_image_count"] == 2
    assert report["train_image_count"] == 4
    assert report["val_image_count"] == 1
    assert report["repeat_factors"]["maintenance_ppe"] <= 3
    assert len(list((variant_root / "images" / "train").glob("*.jpg"))) == 4
    assert len(list((variant_root / "images" / "val").glob("*.jpg"))) == 1
