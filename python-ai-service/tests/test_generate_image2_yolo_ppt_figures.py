from __future__ import annotations

import csv
from pathlib import Path

import yaml

from scripts.generate_image2_yolo_ppt_figures import (
    summarize_all_results_context,
    summarize_all_results_epoch_runs,
    summarize_reference_training_context,
    summarize_dataset_cleanup,
    summarize_training_run,
    summarize_training_run_from_all_results,
)


def _write_csv(path: Path, header: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def test_summarize_training_run_extracts_best_epoch_and_final_metrics(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    run_root.mkdir(parents=True, exist_ok=True)
    (run_root / "dataset.yaml").write_text(
        yaml.safe_dump(
            {
                "path": str(tmp_path / "dataset"),
                "train": "images/train",
                "val": "images/val",
                "test": "images/test",
                "names": ["tower", "wind"],
            },
        ),
        encoding="utf-8",
    )
    (run_root / "args.yaml").write_text(
        yaml.safe_dump(
            {
                "model": "yolo11s.pt",
                "data": str(run_root / "dataset.yaml"),
                "epochs": 3,
                "imgsz": 640,
                "batch": 8,
            },
        ),
        encoding="utf-8",
    )
    _write_csv(
        run_root / "results.csv",
        [
            "epoch",
            "time",
            "train/box_loss",
            "train/cls_loss",
            "train/dfl_loss",
            "metrics/precision(B)",
            "metrics/recall(B)",
            "metrics/mAP50(B)",
            "metrics/mAP50-95(B)",
            "val/box_loss",
            "val/cls_loss",
            "val/dfl_loss",
            "lr/pg0",
            "lr/pg1",
            "lr/pg2",
        ],
        [
            [1, 11.0, 1.2, 0.9, 1.1, 0.70, 0.60, 0.66, 0.40, 1.3, 1.0, 1.2, 0.01, 0.01, 0.01],
            [2, 22.5, 0.9, 0.6, 0.8, 0.82, 0.72, 0.79, 0.55, 1.0, 0.8, 0.9, 0.008, 0.008, 0.008],
            [3, 34.0, 0.8, 0.5, 0.7, 0.80, 0.75, 0.81, 0.53, 0.9, 0.7, 0.8, 0.006, 0.006, 0.006],
        ],
    )
    _write_csv(
        run_root / "val_error_audit_hardcleanr2.csv",
        ["image_name", "source_family", "class_name", "gt", "tp", "fn", "fp"],
        [
            ["a.png", "sd15", "wind_turbine", 3, 2, 1, 0],
            ["b.png", "ssd1b", "transmission_tower", 4, 3, 1, 2],
        ],
    )

    summary = summarize_training_run(run_root)

    assert summary["epoch_count"] == 3
    assert summary["best_epoch"] == 2
    assert summary["best_map50_95"] == 0.55
    assert summary["final_metrics"]["precision"] == 0.80
    assert summary["final_metrics"]["recall"] == 0.75
    assert summary["error_totals"] == {"tp": 5, "fn": 2, "fp": 2, "gt": 7}


def test_summarize_training_run_from_all_results_extracts_curve_for_single_run(tmp_path: Path) -> None:
    run_root = tmp_path / "hqv2_demo_run"
    run_root.mkdir(parents=True, exist_ok=True)
    dataset_yaml = tmp_path / "dataset" / "dataset.yaml"
    dataset_yaml.parent.mkdir(parents=True, exist_ok=True)
    dataset_yaml.write_text(
        yaml.safe_dump(
            {
                "path": str(dataset_yaml.parent),
                "train": "images/train",
                "val": "images/val",
                "test": "images/test",
                "names": ["tower", "wind"],
            },
        ),
        encoding="utf-8",
    )
    (run_root / "args.yaml").write_text(
        yaml.safe_dump(
            {
                "model": "yolo11s.pt",
                "data": str(dataset_yaml),
                "epochs": 3,
                "imgsz": 640,
                "batch": 8,
            },
        ),
        encoding="utf-8",
    )
    _write_csv(
        tmp_path / "all_results_summary.csv",
        [
            "run_name",
            "run_dir",
            "results_csv",
            "epoch",
            "train_box_loss",
            "train_cls_loss",
            "train_dfl_loss",
            "val_box_loss",
            "val_cls_loss",
            "val_dfl_loss",
            "precision",
            "recall",
            "map50",
            "map5095",
            "lr_pg0",
            "lr_pg1",
            "lr_pg2",
            "data_yaml",
            "init_model",
        ],
        [
            ["hqv2_demo_run", str(run_root), "/tmp/results.csv", 1, 1.2, 0.9, 1.1, 1.3, 1.0, 1.2, 0.70, 0.60, 0.66, 0.40, 0.01, 0.01, 0.01, str(dataset_yaml), "/tmp/yolo11s.pt"],
            ["hqv2_demo_run", str(run_root), "/tmp/results.csv", 2, 0.9, 0.6, 0.8, 1.0, 0.8, 0.9, 0.82, 0.72, 0.79, 0.55, 0.008, 0.008, 0.008, str(dataset_yaml), "/tmp/yolo11s.pt"],
            ["hqv2_demo_run", str(run_root), "/tmp/results.csv", 3, 0.8, 0.5, 0.7, 0.9, 0.7, 0.8, 0.80, 0.75, 0.81, 0.53, 0.006, 0.006, 0.006, str(dataset_yaml), "/tmp/yolo11s.pt"],
            ["other_run", "/tmp/other", "/tmp/other.csv", 1, 9, 9, 9, 9, 9, 9, 0.1, 0.1, 0.1, 0.1, 0, 0, 0, str(dataset_yaml), "/tmp/yolo11s.pt"],
        ],
    )

    summary = summarize_training_run_from_all_results(run_root, tmp_path / "all_results_summary.csv")

    assert summary["epoch_count"] == 3
    assert summary["epochs"] == [1, 2, 3]
    assert summary["best_epoch"] == 2
    assert summary["best_map50_95"] == 0.55
    assert summary["final_metrics"]["mAP50"] == 0.81


def test_summarize_training_run_from_all_results_matches_run_dir_when_run_name_is_display_text(tmp_path: Path) -> None:
    run_root = tmp_path / "hqv2_real_dir"
    run_root.mkdir(parents=True, exist_ok=True)
    dataset_yaml = tmp_path / "dataset" / "dataset.yaml"
    dataset_yaml.parent.mkdir(parents=True, exist_ok=True)
    dataset_yaml.write_text(
        yaml.safe_dump({"names": ["tower"]}),
        encoding="utf-8",
    )
    (run_root / "args.yaml").write_text(
        yaml.safe_dump({"data": str(dataset_yaml), "epochs": 2, "imgsz": 640, "batch": 4, "model": "yolo11s.pt"}),
        encoding="utf-8",
    )
    _write_csv(
        tmp_path / "all_results_summary.csv",
        [
            "run_name","run_dir","results_csv","epoch","train_box_loss","train_cls_loss","train_dfl_loss",
            "val_box_loss","val_cls_loss","val_dfl_loss","precision","recall","map50","map5095",
            "lr_pg0","lr_pg1","lr_pg2","data_yaml","init_model",
        ],
        [
            ["中文展示名", str(run_root), "/tmp/results.csv", 1, 1.0, 0.9, 1.2, 1.8, 1.7, 2.0, 0.5, 0.4, 0.55, 0.25, 0, 0, 0, str(dataset_yaml), "/tmp/model.pt"],
            ["中文展示名", str(run_root), "/tmp/results.csv", 2, 0.8, 0.7, 1.0, 1.7, 1.6, 1.9, 0.6, 0.5, 0.66, 0.31, 0, 0, 0, str(dataset_yaml), "/tmp/model.pt"],
        ],
    )

    summary = summarize_training_run_from_all_results(run_root, tmp_path / "all_results_summary.csv")

    assert summary["epochs"] == [1, 2]
    assert summary["final_metrics"]["mAP50"] == 0.66


def test_summarize_dataset_cleanup_counts_split_sizes_and_cleaning_rounds(tmp_path: Path) -> None:
    dataset_root = tmp_path / "dataset"
    dataset_root.mkdir(parents=True, exist_ok=True)
    (dataset_root / "dataset.yaml").write_text(
        yaml.safe_dump(
            {
                "path": str(dataset_root),
                "train": "images/train",
                "val": "images/val",
                "test": "images/test",
                "names": ["tower", "wind", "substation"],
            },
        ),
        encoding="utf-8",
    )
    _write_csv(
        dataset_root / "split_manifest.csv",
        ["split", "category", "model_name", "source_image", "target_image", "target_label"],
        [
            ["train", "wind_turbine", "sd15", "a", "b", "c"],
            ["train", "wind_turbine", "sd15", "a2", "b2", "c2"],
            ["val", "transmission_tower", "ssd1b", "d", "e", "f"],
            ["test", "substation", "gpt", "g", "h", "i"],
        ],
    )
    _write_csv(
        dataset_root / "clean_manifest.csv",
        ["split", "image_name", "status"],
        [
            ["train", "x.png", "dropped"],
            ["train", "y.png", "dropped"],
            ["val", "z.png", "kept"],
        ],
    )
    _write_csv(
        dataset_root / "tower_clean_manifest.csv",
        ["image_name", "label_name", "issue_score", "category"],
        [
            ["a.png", "a.txt", 8, "transmission_tower"],
            ["b.png", "b.txt", 7, "transmission_tower"],
        ],
    )
    _write_csv(
        dataset_root / "hard_clean_manifest.csv",
        ["image_name", "label_name"],
        [["c.png", "c.txt"], ["d.png", "d.txt"]],
    )
    _write_csv(
        dataset_root / "hard_clean_manifest_r2.csv",
        ["image_name", "label_name"],
        [["e.png", "e.txt"]],
    )
    _write_csv(
        dataset_root / "boost_manifest.csv",
        ["source_image", "source_label", "boost_image", "boost_label", "category", "issue_score"],
        [
            ["s1", "l1", "b1", "bl1", "wind_turbine", 4],
            ["s2", "l2", "b2", "bl2", "wind_turbine", 3],
            ["s3", "l3", "b3", "bl3", "transmission_tower", 5],
        ],
    )
    _write_csv(
        dataset_root / "issue_audit.csv",
        ["split", "category", "image_path", "label_path", "instance_count", "min_area", "median_area", "max_area", "median_aspect_ratio", "max_aspect_ratio", "total_area", "issue_score", "flags"],
        [
            ["train", "wind_turbine", "i1", "l1", 6, 0.01, 0.02, 0.03, 2.0, 3.0, 0.2, 12, "tiny_targets;thin_structures"],
            ["val", "transmission_tower", "i2", "l2", 4, 0.02, 0.03, 0.04, 4.0, 5.0, 0.3, 9, "thin_structures"],
        ],
    )

    summary = summarize_dataset_cleanup(dataset_root)

    assert summary["split_counts"] == {"train": 2, "val": 1, "test": 1}
    assert summary["category_counts"] == {
        "wind_turbine": 2,
        "transmission_tower": 1,
        "substation": 1,
    }
    assert summary["cleaning_rounds"] == {
        "r1_general_drop": 2,
        "tower_clean_drop": 2,
        "hard_clean_r1_drop": 2,
        "hard_clean_r2_drop": 1,
        "boost_copies": 3,
    }
    assert summary["issue_top_flags"] == {
        "thin_structures": 2,
        "tiny_targets": 1,
    }


def test_summarize_reference_training_context_marks_global_best_and_current_rank(tmp_path: Path) -> None:
    run_root = tmp_path / "hqv2_windgood1x_towerclean8_yolo11s_640_ft1"
    dataset_root = tmp_path / "highquality-v2-pure-yolo-clean-r1-windgood1x-towerclean8"
    run_root.mkdir(parents=True, exist_ok=True)
    dataset_root.mkdir(parents=True, exist_ok=True)
    summary_csv = tmp_path / "all_results_summary.csv"
    _write_csv(
        summary_csv,
        [
            "run_name",
            "run_dir",
            "results_csv",
            "epoch",
            "train_box_loss",
            "train_cls_loss",
            "train_dfl_loss",
            "val_box_loss",
            "val_cls_loss",
            "val_dfl_loss",
            "precision",
            "recall",
            "map50",
            "map5095",
            "lr_pg0",
            "lr_pg1",
            "lr_pg2",
            "data_yaml",
            "init_model",
        ],
        [
            ["hqv2_cleanr1_yolo11s_r1_fixpath", "/tmp/a", "/tmp/a/results.csv", 1, 1, 1, 1, 1, 1, 1, 0.7, 0.6, 0.69, 0.35, 0, 0, 0, "/tmp/highquality-v2-pure-yolo-clean-r1/dataset.yaml", "/tmp/yolo11s.pt"],
            ["hqv2_windgood1x_towerclean8_yolo11s_640_ft1", "/tmp/b", "/tmp/b/results.csv", 8, 1, 1, 1, 1, 1, 1, 0.77, 0.62, 0.71885, 0.36486, 0, 0, 0, "/tmp/highquality-v2-pure-yolo-clean-r1-windgood1x-towerclean8/dataset.yaml", "/tmp/yolo11s.pt"],
            ["hqv2_yolo11s_r4_boosted_frombest", "/tmp/c", "/tmp/c/results.csv", 5, 1, 1, 1, 1, 1, 1, 0.66, 0.58, 0.66177, 0.33789, 0, 0, 0, "dataset.yaml", "/tmp/yolo11s.pt"],
        ],
    )

    summary = summarize_all_results_context(
        current_run_root=run_root,
        current_dataset_root=dataset_root,
        summary_csv=summary_csv,
    )

    assert summary["top_entry"]["run_name"] == "hqv2_windgood1x_towerclean8_yolo11s_640_ft1"
    assert summary["top_entry"]["mAP50"] == 0.71885
    assert summary["current_rank"] == 1
    assert summary["current_entry"]["dataset_name"] == "highquality-v2-pure-yolo-clean-r1-windgood1x-towerclean8"
    assert len(summary["relative_dataset_runs"]) == 1
    assert summary["relative_dataset_runs"][0]["run_name"] == "hqv2_yolo11s_r4_boosted_frombest"


def test_summarize_all_results_epoch_runs_groups_epochs_per_run_and_sorts_by_best_map50(tmp_path: Path) -> None:
    summary_csv = tmp_path / "all_results_summary.csv"
    _write_csv(
        summary_csv,
        [
            "run_name",
            "run_dir",
            "results_csv",
            "epoch",
            "train_box_loss",
            "train_cls_loss",
            "train_dfl_loss",
            "val_box_loss",
            "val_cls_loss",
            "val_dfl_loss",
            "precision",
            "recall",
            "map50",
            "map5095",
            "lr_pg0",
            "lr_pg1",
            "lr_pg2",
            "data_yaml",
            "init_model",
        ],
        [
            ["run_b", "/tmp/b", "/tmp/b.csv", 2, 0.9, 0.8, 1.1, 1.8, 1.7, 2.1, 0.6, 0.5, 0.62, 0.31, 0, 0, 0, "/tmp/ds_b/dataset.yaml", "/tmp/model.pt"],
            ["run_a", "/tmp/a", "/tmp/a.csv", 2, 0.8, 0.7, 1.0, 1.7, 1.6, 2.0, 0.7, 0.6, 0.75, 0.36, 0, 0, 0, "/tmp/ds_a/dataset.yaml", "/tmp/model.pt"],
            ["run_a", "/tmp/a", "/tmp/a.csv", 1, 1.0, 0.9, 1.2, 1.9, 1.8, 2.2, 0.5, 0.4, 0.50, 0.22, 0, 0, 0, "/tmp/ds_a/dataset.yaml", "/tmp/model.pt"],
            ["run_b", "/tmp/b", "/tmp/b.csv", 1, 1.1, 1.0, 1.3, 2.0, 1.9, 2.3, 0.4, 0.3, 0.41, 0.19, 0, 0, 0, "/tmp/ds_b/dataset.yaml", "/tmp/model.pt"],
        ],
    )

    summary = summarize_all_results_epoch_runs(summary_csv, top_k=2)

    assert summary["runs"][0]["run_name"] == "run_a"
    assert summary["runs"][0]["epochs"] == [1, 2]
    assert summary["runs"][0]["best_map50"] == 0.75
    assert summary["runs"][1]["run_name"] == "run_b"
