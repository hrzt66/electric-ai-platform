from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import yaml

try:
    from scripts.bootstrap import ensure_project_root_on_path
except ImportError:  # pragma: no cover
    from bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()


DEFAULT_DATASET_ROOT = Path(
    "/Users/hrzt/code/vibe coding/codex/毕业设计/image-2/datasets/highquality-v2-pure-yolo-clean-r1-windgood1x-towerclean8-hardclean-r2"
)
DEFAULT_RUN_ROOT = Path(
    "/Users/hrzt/code/vibe coding/codex/毕业设计/image-2/final_best_hqv2_hardcleanr2_yolo11s"
)
DEFAULT_OUTPUT_DIR = Path("/Users/hrzt/code/vibe coding/codex/毕业设计/ppt")
DEFAULT_ALL_RESULTS_SUMMARY_CSV = Path("/Users/hrzt/code/vibe coding/codex/毕业设计/image-2/all_results_summary.csv")

CORE_DATASET_VERSIONS = [
    "highquality-v2-pure-yolo-clean-r1",
    "highquality-v2-pure-yolo-clean-r1-boosted-wind-good1x",
    "highquality-v2-pure-yolo-clean-r1-windgood1x-towerclean8",
    "highquality-v2-pure-yolo-clean-r1-windgood1x-towerclean8-hardclean-r1",
    "highquality-v2-pure-yolo-clean-r1-windgood1x-towerclean8-hardclean-r2",
    "highquality-v2-pure-yolo-clean-r1-windgood1x-towerclean8-hardclean-r3",
]


def _configure_matplotlib() -> None:
    plt.rcParams["font.sans-serif"] = [
        "PingFang SC",
        "Heiti SC",
        "STHeiti",
        "Arial Unicode MS",
        "Noto Sans CJK SC",
        "SimHei",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 220
    plt.rcParams["savefig.dpi"] = 220
    plt.rcParams["axes.facecolor"] = "#ffffff"
    plt.rcParams["figure.facecolor"] = "#ffffff"


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _to_float(value: str | float | int | None) -> float:
    if value is None or value == "":
        return 0.0
    return float(value)


def _to_int(value: str | float | int | None) -> int:
    if value is None or value == "":
        return 0
    return int(float(value))


def summarize_reference_training_context(current_run_root: Path, current_dataset_root: Path) -> dict[str, Any]:
    return summarize_all_results_context(
        current_run_root=current_run_root,
        current_dataset_root=current_dataset_root,
        summary_csv=DEFAULT_ALL_RESULTS_SUMMARY_CSV,
    )


def summarize_all_results_context(
    *,
    current_run_root: Path,
    current_dataset_root: Path,
    summary_csv: Path,
) -> dict[str, Any]:
    rows = _read_csv_rows(summary_csv)
    if not rows:
        raise FileNotFoundError(f"Missing or empty all_results_summary csv: {summary_csv}")

    by_run: dict[str, dict[str, Any]] = {}
    for row in rows:
        run_name = row["run_name"]
        data_yaml = row.get("data_yaml", "")
        if data_yaml:
            yaml_path = Path(data_yaml)
            dataset_name = yaml_path.parent.name or yaml_path.name
        else:
            dataset_name = "dataset.yaml"
        entry = {
            "run_name": run_name,
            "run_dir": row.get("run_dir", ""),
            "dataset_name": dataset_name,
            "epoch": _to_int(row.get("epoch")),
            "mAP50": _to_float(row.get("map50")),
            "mAP50_95": _to_float(row.get("map5095")),
            "precision": _to_float(row.get("precision")),
            "recall": _to_float(row.get("recall")),
            "data_yaml": row.get("data_yaml", ""),
        }
        group_key = row.get("run_dir", "") or run_name
        previous = by_run.get(group_key)
        if previous is None:
            by_run[group_key] = entry
            continue
        if entry["mAP50"] > previous["mAP50"]:
            previous.update(
                {
                    "epoch": entry["epoch"],
                    "mAP50": entry["mAP50"],
                    "precision": entry["precision"],
                    "recall": entry["recall"],
                }
            )
        if entry["mAP50_95"] > previous["mAP50_95"]:
            previous["mAP50_95"] = entry["mAP50_95"]

    leaderboard = sorted(by_run.values(), key=lambda item: item["mAP50"], reverse=True)
    top_entry = leaderboard[0]
    current_run_name = current_run_root.name
    current_dataset_name = current_dataset_root.name
    current_run_path = str(current_run_root)
    matched_entry = next(
        (item for item in leaderboard if item.get("run_dir") == current_run_path),
        next((item for item in leaderboard if item["run_name"] == current_run_name), None),
    )
    relative_dataset_runs = [item for item in leaderboard if item["dataset_name"] == "dataset.yaml"]
    core_dataset_best = []
    for dataset_name in CORE_DATASET_VERSIONS:
        candidates = [item for item in leaderboard if item["dataset_name"] == dataset_name]
        if candidates:
            core_dataset_best.append(max(candidates, key=lambda item: item["mAP50"]))
    return {
        "summary_csv": str(summary_csv),
        "top_entry": top_entry,
        "leaderboard": leaderboard,
        "relative_dataset_runs": relative_dataset_runs,
        "core_dataset_versions": list(CORE_DATASET_VERSIONS),
        "core_dataset_best": core_dataset_best,
        "current_run_name": current_run_name,
        "current_dataset_name": current_dataset_name,
        "current_rank": next(
            (
                index + 1
                for index, item in enumerate(leaderboard)
                if item.get("run_dir") == current_run_path or item["run_name"] == current_run_name
            ),
            None,
        ),
        "current_entry": matched_entry,
    }


def summarize_all_results_epoch_runs(summary_csv: Path, *, top_k: int = 8) -> dict[str, Any]:
    rows = _read_csv_rows(summary_csv)
    if not rows:
        raise FileNotFoundError(f"Missing or empty all_results_summary csv: {summary_csv}")

    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        run_name = row["run_name"]
        data_yaml = row.get("data_yaml", "")
        if data_yaml:
            yaml_path = Path(data_yaml)
            dataset_name = yaml_path.parent.name or yaml_path.name
        else:
            dataset_name = "dataset.yaml"
        group_key = row.get("run_dir", "") or run_name
        run = grouped.setdefault(
            group_key,
            {
                "run_name": run_name,
                "run_dir": row.get("run_dir", ""),
                "dataset_name": dataset_name,
                "epochs": [],
                "train_box_loss": [],
                "train_cls_loss": [],
                "train_dfl_loss": [],
                "val_box_loss": [],
                "val_cls_loss": [],
                "val_dfl_loss": [],
                "precision": [],
                "recall": [],
                "map50": [],
                "map5095": [],
            },
        )
        run["epochs"].append(_to_int(row.get("epoch")))
        run["train_box_loss"].append(_to_float(row.get("train_box_loss")))
        run["train_cls_loss"].append(_to_float(row.get("train_cls_loss")))
        run["train_dfl_loss"].append(_to_float(row.get("train_dfl_loss")))
        run["val_box_loss"].append(_to_float(row.get("val_box_loss")))
        run["val_cls_loss"].append(_to_float(row.get("val_cls_loss")))
        run["val_dfl_loss"].append(_to_float(row.get("val_dfl_loss")))
        run["precision"].append(_to_float(row.get("precision")))
        run["recall"].append(_to_float(row.get("recall")))
        run["map50"].append(_to_float(row.get("map50")))
        run["map5095"].append(_to_float(row.get("map5095")))

    runs = list(grouped.values())
    for run in runs:
        ordered = sorted(
            zip(
                run["epochs"],
                run["train_box_loss"],
                run["train_cls_loss"],
                run["train_dfl_loss"],
                run["val_box_loss"],
                run["val_cls_loss"],
                run["val_dfl_loss"],
                run["precision"],
                run["recall"],
                run["map50"],
                run["map5095"],
                strict=False,
            ),
            key=lambda item: item[0],
        )
        (
            run["epochs"],
            run["train_box_loss"],
            run["train_cls_loss"],
            run["train_dfl_loss"],
            run["val_box_loss"],
            run["val_cls_loss"],
            run["val_dfl_loss"],
            run["precision"],
            run["recall"],
            run["map50"],
            run["map5095"],
        ) = [list(items) for items in zip(*ordered, strict=False)]
        run["best_map50"] = max(run["map50"])
        run["best_map5095"] = max(run["map5095"])

    top_runs = sorted(runs, key=lambda item: item["best_map50"], reverse=True)[:top_k]
    return {
        "summary_csv": str(summary_csv),
        "runs": top_runs,
    }


def summarize_training_run(run_root: Path) -> dict[str, Any]:
    args = _read_yaml(run_root / "args.yaml")
    dataset = _read_yaml(run_root / "dataset.yaml")
    rows = _read_csv_rows(run_root / "results.csv")
    if not rows:
        raise FileNotFoundError(f"Missing results.csv under {run_root}")

    epochs = [_to_int(row["epoch"]) for row in rows]
    metrics_map50_95 = [_to_float(row["metrics/mAP50-95(B)"]) for row in rows]
    best_index = max(range(len(rows)), key=lambda idx: metrics_map50_95[idx])
    final_row = rows[-1]

    error_rows = _read_csv_rows(run_root / "val_error_audit_hardcleanr2.csv")
    error_totals = {
        "gt": sum(_to_int(row.get("gt")) for row in error_rows),
        "tp": sum(_to_int(row.get("tp")) for row in error_rows),
        "fn": sum(_to_int(row.get("fn")) for row in error_rows),
        "fp": sum(_to_int(row.get("fp")) for row in error_rows),
    }
    error_by_class = Counter(row.get("class_name", "unknown") for row in error_rows)
    error_by_source = Counter(row.get("source_family", "unknown") for row in error_rows)

    return {
        "run_root": str(run_root),
        "model": args.get("model", ""),
        "epochs_requested": _to_int(args.get("epochs")),
        "batch": _to_int(args.get("batch")),
        "imgsz": _to_int(args.get("imgsz")),
        "dataset_yaml": args.get("data", ""),
        "dataset_names": dataset.get("names", []),
        "epochs": epochs,
        "epoch_count": len(rows),
        "time_seconds": [_to_float(row["time"]) for row in rows],
        "train_losses": {
            "box": [_to_float(row["train/box_loss"]) for row in rows],
            "cls": [_to_float(row["train/cls_loss"]) for row in rows],
            "dfl": [_to_float(row["train/dfl_loss"]) for row in rows],
        },
        "val_losses": {
            "box": [_to_float(row["val/box_loss"]) for row in rows],
            "cls": [_to_float(row["val/cls_loss"]) for row in rows],
            "dfl": [_to_float(row["val/dfl_loss"]) for row in rows],
        },
        "metrics": {
            "precision": [_to_float(row["metrics/precision(B)"]) for row in rows],
            "recall": [_to_float(row["metrics/recall(B)"]) for row in rows],
            "mAP50": [_to_float(row["metrics/mAP50(B)"]) for row in rows],
            "mAP50_95": metrics_map50_95,
        },
        "learning_rates": {
            "pg0": [_to_float(row["lr/pg0"]) for row in rows],
            "pg1": [_to_float(row["lr/pg1"]) for row in rows],
            "pg2": [_to_float(row["lr/pg2"]) for row in rows],
        },
        "best_epoch": epochs[best_index],
        "best_map50_95": round(metrics_map50_95[best_index], 4),
        "best_metrics": {
            "precision": round(_to_float(rows[best_index]["metrics/precision(B)"]), 4),
            "recall": round(_to_float(rows[best_index]["metrics/recall(B)"]), 4),
            "mAP50": round(_to_float(rows[best_index]["metrics/mAP50(B)"]), 4),
            "mAP50_95": round(_to_float(rows[best_index]["metrics/mAP50-95(B)"]), 4),
        },
        "final_metrics": {
            "precision": round(_to_float(final_row["metrics/precision(B)"]), 4),
            "recall": round(_to_float(final_row["metrics/recall(B)"]), 4),
            "mAP50": round(_to_float(final_row["metrics/mAP50(B)"]), 4),
            "mAP50_95": round(_to_float(final_row["metrics/mAP50-95(B)"]), 4),
        },
        "error_totals": error_totals,
        "error_class_counts": dict(error_by_class.most_common()),
        "error_source_counts": dict(error_by_source.most_common()),
    }


def summarize_training_run_from_all_results(run_root: Path, summary_csv: Path) -> dict[str, Any]:
    args = _read_yaml(run_root / "args.yaml")
    dataset_yaml_path = Path(args.get("data", ""))
    dataset = _read_yaml(dataset_yaml_path) if dataset_yaml_path else _read_yaml(run_root / "dataset.yaml")
    run_root_str = str(run_root)
    all_rows = _read_csv_rows(summary_csv)
    rows = [row for row in all_rows if row.get("run_dir") == run_root_str]
    if not rows:
        rows = [row for row in all_rows if row.get("run_name") == run_root.name]
    if not rows:
        raise FileNotFoundError(f"No rows for run {run_root.name} in {summary_csv}")

    rows.sort(key=lambda row: _to_int(row.get("epoch")))
    epochs = [_to_int(row["epoch"]) for row in rows]
    metrics_map50_95 = [_to_float(row["map5095"]) for row in rows]
    best_index = max(range(len(rows)), key=lambda idx: metrics_map50_95[idx])
    final_row = rows[-1]

    error_rows = _read_csv_rows(run_root / "val_error_audit_hardcleanr2.csv")
    error_totals = {
        "gt": sum(_to_int(row.get("gt")) for row in error_rows),
        "tp": sum(_to_int(row.get("tp")) for row in error_rows),
        "fn": sum(_to_int(row.get("fn")) for row in error_rows),
        "fp": sum(_to_int(row.get("fp")) for row in error_rows),
    }
    error_by_class = Counter(row.get("class_name", "unknown") for row in error_rows)
    error_by_source = Counter(row.get("source_family", "unknown") for row in error_rows)

    return {
        "run_root": str(run_root),
        "summary_csv": str(summary_csv),
        "model": args.get("model", ""),
        "epochs_requested": _to_int(args.get("epochs")),
        "batch": _to_int(args.get("batch")),
        "imgsz": _to_int(args.get("imgsz")),
        "dataset_yaml": args.get("data", ""),
        "dataset_names": dataset.get("names", []),
        "epochs": epochs,
        "epoch_count": len(rows),
        "time_seconds": list(range(1, len(rows) + 1)),
        "train_losses": {
            "box": [_to_float(row["train_box_loss"]) for row in rows],
            "cls": [_to_float(row["train_cls_loss"]) for row in rows],
            "dfl": [_to_float(row["train_dfl_loss"]) for row in rows],
        },
        "val_losses": {
            "box": [_to_float(row["val_box_loss"]) for row in rows],
            "cls": [_to_float(row["val_cls_loss"]) for row in rows],
            "dfl": [_to_float(row["val_dfl_loss"]) for row in rows],
        },
        "metrics": {
            "precision": [_to_float(row["precision"]) for row in rows],
            "recall": [_to_float(row["recall"]) for row in rows],
            "mAP50": [_to_float(row["map50"]) for row in rows],
            "mAP50_95": metrics_map50_95,
        },
        "learning_rates": {
            "pg0": [_to_float(row["lr_pg0"]) for row in rows],
            "pg1": [_to_float(row["lr_pg1"]) for row in rows],
            "pg2": [_to_float(row["lr_pg2"]) for row in rows],
        },
        "best_epoch": epochs[best_index],
        "best_map50_95": round(metrics_map50_95[best_index], 4),
        "best_metrics": {
            "precision": round(_to_float(rows[best_index]["precision"]), 4),
            "recall": round(_to_float(rows[best_index]["recall"]), 4),
            "mAP50": round(_to_float(rows[best_index]["map50"]), 4),
            "mAP50_95": round(_to_float(rows[best_index]["map5095"]), 4),
        },
        "final_metrics": {
            "precision": round(_to_float(final_row["precision"]), 4),
            "recall": round(_to_float(final_row["recall"]), 4),
            "mAP50": round(_to_float(final_row["map50"]), 4),
            "mAP50_95": round(_to_float(final_row["map5095"]), 4),
        },
        "error_totals": error_totals,
        "error_class_counts": dict(error_by_class.most_common()),
        "error_source_counts": dict(error_by_source.most_common()),
    }


def summarize_dataset_cleanup(dataset_root: Path) -> dict[str, Any]:
    dataset = _read_yaml(dataset_root / "dataset.yaml")
    split_rows = _read_csv_rows(dataset_root / "split_manifest.csv")
    clean_rows = _read_csv_rows(dataset_root / "clean_manifest.csv")
    tower_clean_rows = _read_csv_rows(dataset_root / "tower_clean_manifest.csv")
    hard_clean_r1_rows = _read_csv_rows(dataset_root / "hard_clean_manifest.csv")
    hard_clean_r2_rows = _read_csv_rows(dataset_root / "hard_clean_manifest_r2.csv")
    boost_rows = _read_csv_rows(dataset_root / "boost_manifest.csv")
    issue_rows = _read_csv_rows(dataset_root / "issue_audit.csv")

    split_counts = Counter(row.get("split", "unknown") for row in split_rows)
    category_counts = Counter(row.get("category", "unknown") for row in split_rows)
    source_model_counts = Counter(row.get("model_name", "unknown") for row in split_rows)

    clean_status = Counter(row.get("status", "unknown") for row in clean_rows)
    issue_flag_counts: Counter[str] = Counter()
    issue_category_counts = Counter(row.get("category", "unknown") for row in issue_rows)
    issue_scores = [_to_float(row.get("issue_score")) for row in issue_rows]
    for row in issue_rows:
        for flag in str(row.get("flags", "")).split(";"):
            normalized = flag.strip()
            if normalized:
                issue_flag_counts[normalized] += 1

    boost_category_counts = Counter(row.get("category", "unknown") for row in boost_rows)

    return {
        "dataset_root": str(dataset_root),
        "class_names": dataset.get("names", []),
        "class_count": len(dataset.get("names", [])),
        "split_counts": dict(split_counts),
        "category_counts": dict(category_counts),
        "source_model_counts": dict(source_model_counts),
        "clean_status_counts": dict(clean_status),
        "cleaning_rounds": {
            "r1_general_drop": sum(1 for row in clean_rows if row.get("status") == "dropped"),
            "tower_clean_drop": len(tower_clean_rows),
            "hard_clean_r1_drop": len(hard_clean_r1_rows),
            "hard_clean_r2_drop": len(hard_clean_r2_rows),
            "boost_copies": len(boost_rows),
        },
        "boost_category_counts": dict(boost_category_counts),
        "issue_count": len(issue_rows),
        "issue_avg_score": round(sum(issue_scores) / len(issue_scores), 4) if issue_scores else 0.0,
        "issue_top_flags": dict(issue_flag_counts.most_common(6)),
        "issue_category_counts": dict(issue_category_counts),
    }


def _save(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def _plot_loss_curve(summary: dict[str, Any], all_runs_summary: dict[str, Any], output_path: Path) -> None:
    current_run_name = Path(summary["run_root"]).name
    current_run_dir = summary["run_root"]
    fig, axes = plt.subplots(1, 2, figsize=(14.8, 5.8), sharex=False)
    current_color = "#dc2626"
    background_color = "#94a3b8"

    for run in all_runs_summary["runs"]:
        is_current = run.get("run_dir") == current_run_dir or run["run_name"] == current_run_name
        color = current_color if is_current else background_color
        alpha = 0.95 if is_current else 0.45
        linewidth = 2.8 if is_current else 1.4
        label = run["run_name"] if is_current else None
        axes[0].plot(run["epochs"], run["train_box_loss"], color=color, alpha=alpha, linewidth=linewidth, label=label)
        axes[1].plot(run["epochs"], run["val_box_loss"], color=color, alpha=alpha, linewidth=linewidth, label=label)

    axes[0].set_title("全部训练路径 Train Box Loss 对比")
    axes[1].set_title("全部训练路径 Val Box Loss 对比")
    for axis in axes:
        axis.set_xlabel("Epoch")
        axis.set_ylabel("Loss")
        axis.grid(alpha=0.25)
    axes[0].legend(loc="upper right")

    fig.suptitle("YOLOv11辅助检测训练损失曲线", fontsize=16, fontweight="bold")
    fig.text(0.5, 0.04, f"高亮训练路径：{current_run_name}", ha="center", fontsize=10)
    fig.text(
        0.5,
        0.02,
        f"数据来源：{Path(all_runs_summary['summary_csv']).name} | 当前路径最佳 Epoch={summary['best_epoch']} | 当前路径最佳 mAP50-95={summary['best_map50_95']:.4f}",
        ha="center",
        fontsize=10,
    )
    fig.tight_layout(rect=(0, 0.05, 1, 0.95))
    _save(fig, output_path)


def _plot_metrics_curve(summary: dict[str, Any], all_runs_summary: dict[str, Any], output_path: Path) -> None:
    current_run_name = Path(summary["run_root"]).name
    current_run_dir = summary["run_root"]
    fig, axes = plt.subplots(1, 2, figsize=(14.8, 5.8), sharex=False, sharey=True)
    current_color = "#dc2626"
    background_color = "#94a3b8"

    for run in all_runs_summary["runs"]:
        is_current = run.get("run_dir") == current_run_dir or run["run_name"] == current_run_name
        color = current_color if is_current else background_color
        alpha = 0.95 if is_current else 0.45
        linewidth = 2.8 if is_current else 1.4
        label = run["run_name"] if is_current else None
        axes[0].plot(run["epochs"], run["map50"], color=color, alpha=alpha, linewidth=linewidth, label=label)
        axes[1].plot(run["epochs"], run["map5095"], color=color, alpha=alpha, linewidth=linewidth, label=label)

    axes[0].set_title("全部训练路径 mAP50 对比")
    axes[1].set_title("全部训练路径 mAP50-95 对比")
    for axis in axes:
        axis.set_xlabel("Epoch")
        axis.set_ylabel("Metric")
        axis.set_ylim(0, 1.0)
        axis.grid(alpha=0.25)
    axes[0].legend(loc="lower right")

    final_metrics = summary["final_metrics"]
    footer = (
        f"当前路径最终 Precision={final_metrics['precision']:.4f}  "
        f"Recall={final_metrics['recall']:.4f}  "
        f"mAP50={final_metrics['mAP50']:.4f}  "
        f"mAP50-95={final_metrics['mAP50_95']:.4f}"
    )
    fig.suptitle("YOLOv11辅助检测指标图", fontsize=16, fontweight="bold")
    fig.text(0.5, 0.04, f"高亮训练路径：{current_run_name}", ha="center", fontsize=10)
    fig.text(
        0.5,
        0.02,
        f"数据来源：{Path(all_runs_summary['summary_csv']).name} | {footer}",
        ha="center",
        fontsize=10,
    )
    fig.tight_layout(rect=(0, 0.05, 1, 0.95))
    _save(fig, output_path)


def _plot_cleanup_overview(
    training_summary: dict[str, Any],
    dataset_summary: dict[str, Any],
    reference_summary: dict[str, Any],
    output_path: Path,
) -> None:
    fig = plt.figure(figsize=(14.5, 9))
    grid = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.15], hspace=0.35, wspace=0.28)
    ax_split = fig.add_subplot(grid[0, 0])
    ax_clean = fig.add_subplot(grid[0, 1])
    ax_rank = fig.add_subplot(grid[1, 0])
    ax_text = fig.add_subplot(grid[1, 1])

    split_counts = dataset_summary["split_counts"]
    split_labels = list(split_counts.keys())
    split_values = [split_counts[label] for label in split_labels]
    ax_split.bar(split_labels, split_values, color=["#2563eb", "#0f766e", "#d97706"][: len(split_labels)])
    ax_split.set_title("数据集划分规模")
    ax_split.set_ylabel("图像数量")
    ax_split.grid(axis="y", alpha=0.25)

    clean_rounds = dataset_summary["cleaning_rounds"]
    clean_labels = list(clean_rounds.keys())
    clean_values = [clean_rounds[label] for label in clean_labels]
    ax_clean.barh(clean_labels, clean_values, color=["#ef4444", "#f97316", "#dc2626", "#b91c1c", "#22c55e"])
    ax_clean.set_title("历轮清洗与增强汇总")
    ax_clean.set_xlabel("样本数量")
    ax_clean.grid(axis="x", alpha=0.25)

    leaderboard = reference_summary["leaderboard"][:8]
    run_labels = [item["run_name"].replace("hqv2_", "", 1)[:28] for item in leaderboard]
    map50_values = [item["mAP50"] for item in leaderboard]
    rank_colors = ["#16a34a" if item["run_name"] == reference_summary["current_run_name"] else "#475569" for item in leaderboard]
    ax_rank.barh(run_labels, map50_values, color=rank_colors)
    ax_rank.invert_yaxis()
    ax_rank.set_title("全局训练目录 mAP50 排名（Top 8）")
    ax_rank.set_xlabel("mAP50")
    ax_rank.grid(axis="x", alpha=0.25)
    top_map50 = reference_summary["top_entry"]["mAP50"]
    ax_rank.axvline(top_map50, linestyle="--", linewidth=1.2, color="#16a34a", alpha=0.75)

    ax_text.axis("off")
    final_metrics = training_summary["final_metrics"]
    error_totals = training_summary["error_totals"]
    top_flags = dataset_summary["issue_top_flags"]
    error_classes = training_summary["error_class_counts"]
    boost_categories = dataset_summary["boost_category_counts"]
    current_entry = reference_summary["current_entry"]
    current_rank = reference_summary["current_rank"]
    core_versions = reference_summary["core_dataset_versions"]
    relative_runs = reference_summary["relative_dataset_runs"]

    summary_lines = [
        "训练与清洗摘要",
        f"当前训练目录: {reference_summary['current_run_name']}",
        f"当前清洗版本: {reference_summary['current_dataset_name']}",
        f"模型权重: {Path(training_summary['model']).name or training_summary['model']}",
        f"训练轮次: {training_summary['epoch_count']} / 设定 {training_summary['epochs_requested']}",
        f"输入尺寸: {training_summary['imgsz']}    Batch: {training_summary['batch']}",
        f"类别数: {dataset_summary['class_count']}    数据总量: {sum(split_values)}",
        f"全局最高目录: {reference_summary['top_entry']['run_name']}",
        f"全局最高 mAP50 / mAP50-95: {reference_summary['top_entry']['mAP50']:.5f} / {reference_summary['top_entry']['mAP50_95']:.5f}",
        (
            f"当前目录排名: Top {current_rank}，mAP50 / mAP50-95 = "
            f"{current_entry['mAP50']:.5f} / {current_entry['mAP50_95']:.5f}"
            if current_entry and current_rank is not None
            else "当前目录未出现在显式 leaderboard 清单中"
        ),
        f"最佳 Epoch: {training_summary['best_epoch']}    最佳 mAP50-95: {training_summary['best_map50_95']:.4f}",
        f"最终 Precision / Recall: {final_metrics['precision']:.4f} / {final_metrics['recall']:.4f}",
        f"最终 mAP50 / mAP50-95: {final_metrics['mAP50']:.4f} / {final_metrics['mAP50_95']:.4f}",
        f"验证审计 TP / FN / FP: {error_totals['tp']} / {error_totals['fn']} / {error_totals['fp']}",
        f"高频问题标记: {', '.join(f'{k}={v}' for k, v in top_flags.items()) or '无'}",
        f"误差类别分布: {', '.join(f'{k}={v}' for k, v in list(error_classes.items())[:4]) or '无'}",
        f"Boost 来源分布: {', '.join(f'{k}={v}' for k, v in boost_categories.items()) or '无'}",
        f"困难样本审计数: {dataset_summary['issue_count']}    平均问题分: {dataset_summary['issue_avg_score']:.2f}",
        f"核心清洗主线: {' -> '.join(core_versions[:4])} -> ...",
        f"相对 dataset.yaml 训练目录数: {len(relative_runs)}",
    ]
    ax_text.text(
        0.02,
        0.98,
        "\n".join(summary_lines),
        va="top",
        fontsize=10.5,
        linespacing=1.55,
        bbox={"boxstyle": "round,pad=0.6", "fc": "#f8fafc", "ec": "#cbd5e1"},
    )

    fig.suptitle("YOLOv11辅助检测数据清洗与结果总览图", fontsize=17, fontweight="bold")
    fig.text(
        0.5,
        0.015,
        "汇总 split_manifest、clean_manifest、tower_clean_manifest、hard_clean_manifest、boost_manifest、issue_audit 与最终验证审计结果",
        ha="center",
        fontsize=10,
    )
    _save(fig, output_path)


def _plot_global_ranking_from_summary(reference_summary: dict[str, Any], output_path: Path) -> None:
    leaderboard = reference_summary["leaderboard"][:12]
    labels = [item["run_name"][:34] for item in leaderboard]
    values = [item["mAP50"] for item in leaderboard]
    colors = ["#16a34a" if item["run_name"] == reference_summary["current_run_name"] else "#475569" for item in leaderboard]

    fig, ax = plt.subplots(figsize=(12.5, 6.8))
    ax.barh(labels, values, color=colors)
    ax.invert_yaxis()
    ax.set_title("基于 all_results_summary 的全局训练目录 mAP50 排名", fontsize=16, fontweight="bold")
    ax.set_xlabel("mAP50")
    ax.grid(axis="x", alpha=0.25)
    top = reference_summary["top_entry"]
    ax.axvline(top["mAP50"], linestyle="--", linewidth=1.2, color="#16a34a", alpha=0.75)
    fig.text(
        0.5,
        0.02,
        f"最高成绩: {top['run_name']} | {top['dataset_name']} | mAP50={top['mAP50']:.5f} | mAP50-95={top['mAP50_95']:.5f}",
        ha="center",
        fontsize=10,
    )
    fig.tight_layout(rect=(0, 0.05, 1, 0.95))
    _save(fig, output_path)


def _plot_core_dataset_versions(reference_summary: dict[str, Any], output_path: Path) -> None:
    rows = reference_summary["core_dataset_best"]
    labels = [item["dataset_name"].replace("highquality-v2-pure-yolo-", "") for item in rows]
    map50_values = [item["mAP50"] for item in rows]
    map95_values = [item["mAP50_95"] for item in rows]
    x = np.arange(len(labels))
    width = 0.36

    fig, ax = plt.subplots(figsize=(13.5, 6.8))
    ax.bar(x - width / 2, map50_values, width=width, label="mAP50", color="#2563eb")
    ax.bar(x + width / 2, map95_values, width=width, label="mAP50-95", color="#059669")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylabel("Metric")
    ax.set_title("基于 all_results_summary 的核心清洗版本对比图", fontsize=16, fontweight="bold")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.text(
        0.5,
        0.02,
        f"当前显式核心版本数={len(rows)}，相对 dataset.yaml 训练目录数={len(reference_summary['relative_dataset_runs'])}",
        ha="center",
        fontsize=10,
    )
    fig.tight_layout(rect=(0, 0.05, 1, 0.95))
    _save(fig, output_path)


def render_figures(
    *,
    run_root: Path,
    dataset_root: Path,
    output_dir: Path,
    summary_csv: Path = DEFAULT_ALL_RESULTS_SUMMARY_CSV,
) -> dict[str, str]:
    _configure_matplotlib()
    training_summary = summarize_training_run_from_all_results(run_root, summary_csv)
    all_runs_epoch_summary = summarize_all_results_epoch_runs(summary_csv)
    dataset_summary = summarize_dataset_cleanup(dataset_root)
    reference_summary = summarize_all_results_context(
        current_run_root=run_root,
        current_dataset_root=dataset_root,
        summary_csv=summary_csv,
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    outputs = {
        "loss_curve": output_dir / "1.YOLOv11辅助检测训练损失曲线.png",
        "metrics_curve": output_dir / "2.YOLOv11辅助检测指标图.png",
        "overview": output_dir / "3.YOLOv11辅助检测数据清洗与结果总览图.png",
        "global_ranking": output_dir / "4.基于all_results_summary的全局训练排名图.png",
        "core_dataset_compare": output_dir / "5.基于all_results_summary的核心清洗版本对比图.png",
        "summary_json": output_dir / "yolo11_image2_training_summary.json",
    }

    _plot_loss_curve(training_summary, all_runs_epoch_summary, outputs["loss_curve"])
    _plot_metrics_curve(training_summary, all_runs_epoch_summary, outputs["metrics_curve"])
    _plot_cleanup_overview(training_summary, dataset_summary, reference_summary, outputs["overview"])
    _plot_global_ranking_from_summary(reference_summary, outputs["global_ranking"])
    _plot_core_dataset_versions(reference_summary, outputs["core_dataset_compare"])

    outputs["summary_json"].write_text(
        json.dumps(
            {
                "training_summary": training_summary,
                "dataset_summary": dataset_summary,
                "reference_summary": reference_summary,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return {key: str(value) for key, value in outputs.items()}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate YOLOv11 training figures for the image-2 thesis deck.")
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT, help="Directory that contains results.csv and args.yaml.")
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT, help="Directory that contains split and cleaning manifests.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory where PNG figures will be written.")
    parser.add_argument("--summary-csv", type=Path, default=DEFAULT_ALL_RESULTS_SUMMARY_CSV, help="CSV that summarizes all training results.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    report = render_figures(run_root=args.run_root, dataset_root=args.dataset_root, output_dir=args.output_dir, summary_csv=args.summary_csv)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
