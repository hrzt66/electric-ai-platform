from __future__ import annotations

import json
import math
import shutil
import time
from pathlib import Path
from types import SimpleNamespace

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import patches
from PIL import Image

from app.core.settings import Settings
from app.dependencies import build_runtime_registry, build_scoring_service
from training.reporting.thesis_figure_config import (
    FigureSpec,
    MODEL_COLORS,
    build_prompt_suite,
    expected_figure_inventory,
)
from training.reporting.thesis_figure_data import (
    load_scoring_v2_history,
    load_scoring_v2_metrics,
    load_yolo_results,
    parse_generation_training_log,
)


def ensure_output_dirs(root: Path) -> dict[str, Path]:
    output_dirs = {
        "generation_comparison": root / "generation-comparison",
        "generation_training": root / "generation-training",
        "scoring_training": root / "scoring-training",
        "evaluation_stats": root / "evaluation-stats",
        "paper_ready": root / "paper-ready",
    }
    for path in output_dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return output_dirs


def write_figure_manifest(path: Path, figure_specs: list[FigureSpec]) -> None:
    payload = [spec.to_manifest_record() for spec in figure_specs]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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


def _target_group_for_filename(filename: str) -> str:
    index = int(filename.split("_", 1)[0])
    if index <= 9:
        return "generation_comparison"
    if index <= 12:
        return "generation_training"
    if index <= 21:
        return "scoring_training"
    return "evaluation_stats"


def _save_figure(fig: plt.Figure, output_dirs: dict[str, Path], filename: str) -> Path:
    group = _target_group_for_filename(filename)
    target_path = output_dirs[group] / filename
    fig.savefig(target_path, bbox_inches="tight")
    paper_ready_path = output_dirs["paper_ready"] / filename
    shutil.copy2(target_path, paper_ready_path)
    plt.close(fig)
    return target_path


def _read_image_array(image_path: str | Path) -> np.ndarray:
    return np.asarray(Image.open(image_path).convert("RGB"))


def _plot_image_strip(
    *,
    title: str,
    prompt: str,
    records: list[dict[str, object]],
    output_dirs: dict[str, Path],
    filename: str,
) -> None:
    fig, axes = plt.subplots(1, len(records), figsize=(15, 4.8))
    if len(records) == 1:
        axes = [axes]
    for axis, record in zip(axes, records, strict=True):
        axis.imshow(_read_image_array(record["image_path"]))
        axis.set_title(str(record["model_name"]), fontsize=11, color=MODEL_COLORS.get(str(record["model_name"]), "#000000"))
        axis.axis("off")
        axis.set_xlabel(
            f"耗时 {record['generation_seconds']:.2f}s\nV1 {record['scores']['electric-score-v1']['total_score']:.2f} / "
            f"V2 {record['scores']['electric-score-v2']['total_score']:.2f}",
            fontsize=9,
        )
    fig.suptitle(title, fontsize=16, fontweight="bold")
    fig.text(0.5, 0.02, prompt, ha="center", fontsize=10)
    fig.tight_layout(rect=(0, 0.05, 1, 0.92))
    _save_figure(fig, output_dirs, filename)


def _plot_overview_grid(records: list[dict[str, object]], output_dirs: dict[str, Path], filename: str) -> None:
    suite = build_prompt_suite()
    fig, axes = plt.subplots(len(suite.prompts), len(suite.generation_models), figsize=(13, 26))
    for row_index, prompt in enumerate(suite.prompts):
        for col_index, model_name in enumerate(suite.generation_models):
            axis = axes[row_index][col_index]
            record = next(
                item
                for item in records
                if item["prompt_index"] == row_index + 1 and item["model_name"] == model_name
            )
            axis.imshow(_read_image_array(record["image_path"]))
            axis.axis("off")
            if row_index == 0:
                axis.set_title(model_name, fontsize=11, color=MODEL_COLORS.get(model_name, "#000000"))
            if col_index == 0:
                axis.set_ylabel(f"Prompt {row_index + 1}", fontsize=10)
    fig.suptitle("固定 Prompt 集生成结果总览", fontsize=18, fontweight="bold")
    fig.text(0.5, 0.01, "三模型统一 seed=42，负向提示词保持一致", ha="center", fontsize=10)
    fig.tight_layout(rect=(0, 0.02, 1, 0.98))
    _save_figure(fig, output_dirs, filename)


def _plot_line_chart(
    *,
    x: list[float],
    series: list[tuple[str, list[float], str]],
    title: str,
    xlabel: str,
    ylabel: str,
    output_dirs: dict[str, Path],
    filename: str,
) -> None:
    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    for label, values, color in series:
        ax.plot(x, values, label=label, color=color, linewidth=2)
    ax.set_title(title, fontsize=15, fontweight="bold")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    _save_figure(fig, output_dirs, filename)


def _plot_dual_axis_chart(
    *,
    x: list[float],
    left_values: list[float],
    right_values: list[float],
    left_label: str,
    right_label: str,
    title: str,
    xlabel: str,
    left_color: str,
    right_color: str,
    output_dirs: dict[str, Path],
    filename: str,
) -> None:
    fig, ax_left = plt.subplots(figsize=(10.5, 5.2))
    ax_left.plot(x, left_values, color=left_color, linewidth=2, label=left_label)
    ax_left.set_xlabel(xlabel)
    ax_left.set_ylabel(left_label, color=left_color)
    ax_left.tick_params(axis="y", labelcolor=left_color)
    ax_left.grid(alpha=0.25)

    ax_right = ax_left.twinx()
    ax_right.plot(x, right_values, color=right_color, linewidth=2, label=right_label)
    ax_right.set_ylabel(right_label, color=right_color)
    ax_right.tick_params(axis="y", labelcolor=right_color)

    fig.suptitle(title, fontsize=15, fontweight="bold")
    fig.tight_layout()
    _save_figure(fig, output_dirs, filename)


def _plot_grouped_bar_chart(
    *,
    categories: list[str],
    series: list[tuple[str, list[float], str]],
    title: str,
    ylabel: str,
    output_dirs: dict[str, Path],
    filename: str,
) -> None:
    fig, ax = plt.subplots(figsize=(11, 5.4))
    x = np.arange(len(categories))
    width = 0.8 / max(len(series), 1)
    for index, (label, values, color) in enumerate(series):
        offset = (index - (len(series) - 1) / 2) * width
        ax.bar(x + offset, values, width=width, label=label, color=color)
    ax.set_xticks(x)
    ax.set_xticklabels(categories)
    ax.set_title(title, fontsize=15, fontweight="bold")
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    _save_figure(fig, output_dirs, filename)


def _plot_boxplot(
    *,
    labels: list[str],
    values: list[list[float]],
    title: str,
    ylabel: str,
    output_dirs: dict[str, Path],
    filename: str,
) -> None:
    fig, ax = plt.subplots(figsize=(12, 5.6))
    box = ax.boxplot(values, patch_artist=True, labels=labels)
    palette = [
        MODEL_COLORS["electric-score-v1"],
        MODEL_COLORS["electric-score-v2"],
        MODEL_COLORS["sd15-electric"],
        MODEL_COLORS["sd15-electric-specialized"],
        MODEL_COLORS["ssd1b-electric"],
        "#475569",
    ]
    for patch, color in zip(box["boxes"], palette * math.ceil(len(labels) / len(palette)), strict=False):
        patch.set_facecolor(color)
        patch.set_alpha(0.55)
    ax.set_title(title, fontsize=15, fontweight="bold")
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    _save_figure(fig, output_dirs, filename)


def _plot_heatmap(
    *,
    matrix: np.ndarray,
    row_labels: list[str],
    col_labels: list[str],
    title: str,
    output_dirs: dict[str, Path],
    filename: str,
) -> None:
    fig, ax = plt.subplots(figsize=(15, 6))
    heatmap = ax.imshow(matrix, aspect="auto", cmap="YlOrRd")
    ax.set_xticks(np.arange(len(col_labels)))
    ax.set_xticklabels(col_labels, rotation=45, ha="right")
    ax.set_yticks(np.arange(len(row_labels)))
    ax.set_yticklabels(row_labels)
    ax.set_title(title, fontsize=15, fontweight="bold")
    fig.colorbar(heatmap, ax=ax, fraction=0.025, pad=0.02)
    fig.tight_layout()
    _save_figure(fig, output_dirs, filename)


def _plot_scoring_pipeline_figure(output_dirs: dict[str, Path], filename: str) -> None:
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.axis("off")

    left_boxes = [
        ((0.05, 0.68), "electric-score-v1\n主流评分模型组合基线"),
        ((0.05, 0.44), "ImageReward\n文本一致性"),
        ((0.05, 0.20), "CLIP-IQA + Aesthetic Predictor\n视觉保真 / 物理合理 / 构图美学"),
    ]
    right_boxes = [
        ((0.58, 0.68), "electric-score-v2\n自训练电力领域评分模型"),
        ((0.58, 0.44), "轻量四维回归模型\n视觉 / 文本 / 物理 / 美学"),
        ((0.58, 0.20), "YOLO 辅助检测特征\n设备与结构约束"),
    ]

    for (x, y), text in left_boxes:
        ax.add_patch(patches.FancyBboxPatch((x, y), 0.28, 0.16, boxstyle="round,pad=0.02", facecolor="#e2e8f0"))
        ax.text(x + 0.14, y + 0.08, text, ha="center", va="center", fontsize=12)
    for (x, y), text in right_boxes:
        ax.add_patch(patches.FancyBboxPatch((x, y), 0.28, 0.16, boxstyle="round,pad=0.02", facecolor="#fee2e2"))
        ax.text(x + 0.14, y + 0.08, text, ha="center", va="center", fontsize=12)

    for x_center in (0.19, 0.72):
        ax.annotate("", xy=(x_center, 0.60), xytext=(x_center, 0.44), arrowprops={"arrowstyle": "->", "lw": 2})
        ax.annotate("", xy=(x_center, 0.36), xytext=(x_center, 0.20), arrowprops={"arrowstyle": "->", "lw": 2})

    ax.text(0.5, 0.92, "主流评分模型组合基线与自训练评分器结构对比", ha="center", fontsize=16, fontweight="bold")
    fig.tight_layout()
    _save_figure(fig, output_dirs, filename)


def _build_generation_records(runtime_root: Path, output_root: Path) -> list[dict[str, object]]:
    cache_path = output_root / "comparison_records.json"
    suite = build_prompt_suite()
    settings = Settings(runtime_root=runtime_root.resolve())
    registry = build_runtime_registry(settings)
    raw_dir = output_root / "paper-ready" / "generated"
    raw_dir.mkdir(parents=True, exist_ok=True)
    cached_records = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else []
    record_map = {
        (int(item["prompt_index"]), str(item["model_name"])): item
        for item in cached_records
        if Path(item["image_path"]).exists()
    }

    def persist_records() -> None:
        ordered = []
        for prompt_index, _ in enumerate(suite.prompts, start=1):
            for model_name in suite.generation_models:
                item = record_map.get((prompt_index, model_name))
                if item is not None:
                    ordered.append(item)
        cache_path.write_text(json.dumps(ordered, ensure_ascii=False, indent=2), encoding="utf-8")

    for model_index, model_name in enumerate(suite.generation_models, start=1):
        runtime = registry.get_generation_runtime(model_name)
        try:
            for prompt_index, prompt in enumerate(suite.prompts, start=1):
                key = (prompt_index, model_name)
                existing = record_map.get(key)
                if existing is not None and Path(existing["image_path"]).exists():
                    continue

                job_id = 880000 + model_index * 100 + prompt_index
                start = time.perf_counter()
                generated = runtime.generate(
                    job_id=job_id,
                    prompt=prompt,
                    negative_prompt=suite.negative_prompt,
                    seed=suite.seed,
                    width=512,
                    height=512,
                    steps=20,
                    guidance_scale=7.5,
                    num_images=1,
                    model_name=model_name,
                )
                elapsed = time.perf_counter() - start
                source_path = Path(generated[0]["file_path"])
                copied_path = raw_dir / f"prompt_{prompt_index:02d}_{model_name}.png"
                shutil.copy2(source_path, copied_path)
                record_map[key] = {
                    "prompt_index": prompt_index,
                    "prompt": prompt,
                    "model_name": model_name,
                    "seed": suite.seed,
                    "image_path": str(copied_path),
                    "generation_seconds": round(elapsed, 4),
                    "scores": existing.get("scores", {}) if existing else {},
                }
                persist_records()
        finally:
            registry.release_generation_runtime(model_name)

    records = [
        record_map[(prompt_index, model_name)]
        for prompt_index, _ in enumerate(suite.prompts, start=1)
        for model_name in suite.generation_models
    ]

    for scoring_model_name in suite.scoring_models:
        scoring_service = build_scoring_service(settings=settings, release_after_batch=False)
        try:
            for record in records:
                if scoring_model_name in record["scores"]:
                    continue
                scores = scoring_service._score_image(
                    image_path=str(record["image_path"]),
                    prompt=str(record["prompt"]),
                    scoring_model_name=scoring_model_name,
                )
                record["scores"][scoring_model_name] = scores
                persist_records()
        finally:
            scoring_service.release_resources()

    persist_records()
    return records


def _build_heatmap_matrix(records: list[dict[str, object]], scoring_model_name: str) -> tuple[np.ndarray, list[str], list[str]]:
    suite = build_prompt_suite()
    metrics = ["visual_fidelity", "text_consistency", "physical_plausibility", "composition_aesthetics", "total_score"]
    rows: list[list[float]] = []
    row_labels = [f"P{index:02d}" for index in range(1, len(suite.prompts) + 1)]
    col_labels = [f"{model_name}-{metric}" for model_name in suite.generation_models for metric in metrics]
    for prompt_index in range(1, len(suite.prompts) + 1):
        row_values: list[float] = []
        for model_name in suite.generation_models:
            record = next(item for item in records if item["prompt_index"] == prompt_index and item["model_name"] == model_name)
            score_bundle = record["scores"][scoring_model_name]
            row_values.extend(float(score_bundle[metric]) for metric in metrics)
        rows.append(row_values)
    return np.array(rows, dtype=float), row_labels, col_labels


def _render_generation_comparison_figures(records: list[dict[str, object]], output_dirs: dict[str, Path]) -> None:
    _plot_overview_grid(records, output_dirs, "01_generation_prompt_overview_grid.png")
    for prompt_index in range(1, 9):
        prompt_records = [item for item in records if item["prompt_index"] == prompt_index]
        prompt_records.sort(key=lambda item: build_prompt_suite().generation_models.index(str(item["model_name"])))
        _plot_image_strip(
            title=f"Prompt {prompt_index:02d} 生成结果对比图",
            prompt=str(prompt_records[0]["prompt"]),
            records=prompt_records,
            output_dirs=output_dirs,
            filename=f"{prompt_index + 1:02d}_generation_prompt_{prompt_index:02d}_model_compare.png",
        )


def _render_generation_training_figures(runtime_root: Path, output_dirs: dict[str, Path]) -> None:
    rows = parse_generation_training_log(runtime_root / "training" / "generation" / "sd15-electric-specialized-v2" / "training.log")
    if not rows:
        raise RuntimeError("generation training log did not yield any parsed rows")

    x = [row.step for row in rows]
    loss = [row.step_loss for row in rows]
    lr = [row.learning_rate for row in rows]
    elapsed_hours = [row.elapsed_seconds / 3600.0 for row in rows]
    throughput = [
        row.iterations_per_second if row.iterations_per_second is not None else (1.0 / row.seconds_per_iteration if row.seconds_per_iteration else 0.0)
        for row in rows
    ]

    _plot_line_chart(
        x=x,
        series=[("step_loss", loss, MODEL_COLORS["sd15-electric-specialized"])],
        title="生成模型训练损失曲线",
        xlabel="训练步数",
        ylabel="step loss",
        output_dirs=output_dirs,
        filename="10_generation_training_loss_curve.png",
    )
    _plot_line_chart(
        x=x,
        series=[("learning rate", lr, MODEL_COLORS["sd15-electric"])],
        title="生成模型学习率衰减曲线",
        xlabel="训练步数",
        ylabel="learning rate",
        output_dirs=output_dirs,
        filename="11_generation_lr_decay_curve.png",
    )
    _plot_dual_axis_chart(
        x=x,
        left_values=elapsed_hours,
        right_values=throughput,
        left_label="累计训练时长（小时）",
        right_label="吞吐率（it/s）",
        title="生成模型训练进度与吞吐率图",
        xlabel="训练步数",
        left_color=MODEL_COLORS["sd15-electric"],
        right_color=MODEL_COLORS["sd15-electric-specialized"],
        output_dirs=output_dirs,
        filename="12_generation_progress_throughput_curve.png",
    )


def _render_scoring_training_figures(runtime_root: Path, output_dirs: dict[str, Path]) -> None:
    scoring_root = runtime_root / "training" / "scoring" / "electric-score-v2"
    history = load_scoring_v2_history(scoring_root / "history.json")
    metrics = load_scoring_v2_metrics(runtime_root / "scoring" / "electric-score-v2" / "metrics.json")
    yolo_rows = load_yolo_results(scoring_root / "yolo-mps-compact-noval" / "train100" / "results.csv")

    epochs = [int(item["epoch"]) for item in history]
    train_loss = [float(item["train_loss"]) for item in history]
    progress = [epoch / max(epochs) * 100.0 for epoch in epochs]
    learning_rate = [3e-4 for _ in epochs]
    per_target_mae = metrics["test_metrics"]["per_target_mae"]

    _plot_scoring_pipeline_figure(output_dirs, "13_scoring_pipeline_baseline_vs_student.png")
    _plot_line_chart(
        x=epochs,
        series=[("train_loss", train_loss, MODEL_COLORS["electric-score-v2"])],
        title="自训练评分模型训练损失曲线",
        xlabel="训练轮次",
        ylabel="train loss",
        output_dirs=output_dirs,
        filename="14_scoring_v2_training_loss_curve.png",
    )
    _plot_line_chart(
        x=epochs,
        series=[("learning rate", learning_rate, MODEL_COLORS["electric-score-v1"])],
        title="自训练评分模型学习率曲线",
        xlabel="训练轮次",
        ylabel="learning rate",
        output_dirs=output_dirs,
        filename="15_scoring_v2_lr_curve.png",
    )
    _plot_line_chart(
        x=epochs,
        series=[("训练进度", progress, MODEL_COLORS["electric-score-v2"])],
        title="自训练评分模型训练进度图",
        xlabel="训练轮次",
        ylabel="进度（%）",
        output_dirs=output_dirs,
        filename="16_scoring_v2_progress_curve.png",
    )
    _plot_grouped_bar_chart(
        categories=list(per_target_mae.keys()),
        series=[("MAE", [float(value) for value in per_target_mae.values()], MODEL_COLORS["electric-score-v2"])],
        title="自训练评分模型各维度回归误差图",
        ylabel="MAE",
        output_dirs=output_dirs,
        filename="17_scoring_v2_regression_mae.png",
    )

    yolo_epochs = [row.epoch for row in yolo_rows]
    yolo_time_hours = [row.elapsed_seconds / 3600.0 for row in yolo_rows]
    yolo_throughput = [row.epoch / (row.elapsed_seconds / 3600.0) if row.elapsed_seconds else 0.0 for row in yolo_rows]

    _plot_line_chart(
        x=yolo_epochs,
        series=[
            ("box_loss", [row.train_box_loss for row in yolo_rows], "#0f766e"),
            ("cls_loss", [row.train_cls_loss for row in yolo_rows], "#d97706"),
            ("dfl_loss", [row.train_dfl_loss for row in yolo_rows], "#1f4e79"),
        ],
        title="YOLO 辅助检测训练损失曲线",
        xlabel="训练轮次",
        ylabel="loss",
        output_dirs=output_dirs,
        filename="18_yolo_training_loss_curve.png",
    )
    _plot_line_chart(
        x=yolo_epochs,
        series=[
            ("lr/pg0", [row.lr_pg0 for row in yolo_rows], "#0f766e"),
            ("lr/pg1", [row.lr_pg1 for row in yolo_rows], "#d97706"),
            ("lr/pg2", [row.lr_pg2 for row in yolo_rows], "#1f4e79"),
        ],
        title="YOLO 辅助检测学习率曲线",
        xlabel="训练轮次",
        ylabel="learning rate",
        output_dirs=output_dirs,
        filename="19_yolo_lr_curve.png",
    )
    _plot_dual_axis_chart(
        x=yolo_epochs,
        left_values=yolo_time_hours,
        right_values=yolo_throughput,
        left_label="累计训练时长（小时）",
        right_label="吞吐率（epoch/h）",
        title="YOLO 辅助检测训练进度与吞吐率图",
        xlabel="训练轮次",
        left_color="#0f766e",
        right_color="#b91c1c",
        output_dirs=output_dirs,
        filename="20_yolo_progress_throughput_curve.png",
    )
    _plot_line_chart(
        x=yolo_epochs,
        series=[
            ("precision", [row.precision for row in yolo_rows], "#0f766e"),
            ("recall", [row.recall for row in yolo_rows], "#d97706"),
            ("mAP50", [row.map50 for row in yolo_rows], "#1f4e79"),
            ("mAP50-95", [row.map50_95 for row in yolo_rows], "#b91c1c"),
        ],
        title="YOLO 辅助检测指标图",
        xlabel="训练轮次",
        ylabel="指标值",
        output_dirs=output_dirs,
        filename="21_yolo_detection_metrics.png",
    )


def _render_evaluation_stats(records: list[dict[str, object]], output_dirs: dict[str, Path]) -> None:
    suite = build_prompt_suite()
    dimensions = ["visual_fidelity", "text_consistency", "physical_plausibility", "composition_aesthetics"]

    avg_total_scores = {
        scoring_model: [
            float(np.mean([item["scores"][scoring_model]["total_score"] for item in records if item["model_name"] == model_name]))
            for model_name in suite.generation_models
        ]
        for scoring_model in suite.scoring_models
    }
    _plot_grouped_bar_chart(
        categories=suite.generation_models,
        series=[
            ("electric-score-v1", avg_total_scores["electric-score-v1"], MODEL_COLORS["electric-score-v1"]),
            ("electric-score-v2", avg_total_scores["electric-score-v2"], MODEL_COLORS["electric-score-v2"]),
        ],
        title="固定 Prompt 集平均总分对比图",
        ylabel="平均总分",
        output_dirs=output_dirs,
        filename="22_average_total_score_compare.png",
    )

    gain_series = []
    for model_name in suite.generation_models:
        gains = []
        model_records = [item for item in records if item["model_name"] == model_name]
        for dimension in dimensions:
            v1_avg = float(np.mean([item["scores"]["electric-score-v1"][dimension] for item in model_records]))
            v2_avg = float(np.mean([item["scores"]["electric-score-v2"][dimension] for item in model_records]))
            gains.append(v2_avg - v1_avg)
        gain_series.append((model_name, gains, MODEL_COLORS[model_name]))
    _plot_grouped_bar_chart(
        categories=dimensions,
        series=gain_series,
        title="各维度增益对比图",
        ylabel="分数增益（V2 - V1）",
        output_dirs=output_dirs,
        filename="23_dimension_gain_compare.png",
    )

    boxplot_labels: list[str] = []
    boxplot_values: list[list[float]] = []
    for model_name in suite.generation_models:
        for scoring_model_name in suite.scoring_models:
            boxplot_labels.append(f"{model_name}\n{scoring_model_name}")
            boxplot_values.append(
                [float(item["scores"][scoring_model_name]["total_score"]) for item in records if item["model_name"] == model_name]
            )
    _plot_boxplot(
        labels=boxplot_labels,
        values=boxplot_values,
        title="总分箱线图",
        ylabel="总分",
        output_dirs=output_dirs,
        filename="24_total_score_boxplot.png",
    )

    heatmap_v1, row_labels, col_labels = _build_heatmap_matrix(records, "electric-score-v1")
    _plot_heatmap(
        matrix=heatmap_v1,
        row_labels=row_labels,
        col_labels=col_labels,
        title="多维度评分热力图（基线评分器）",
        output_dirs=output_dirs,
        filename="25_multidim_score_heatmap_v1.png",
    )
    heatmap_v2, row_labels, col_labels = _build_heatmap_matrix(records, "electric-score-v2")
    _plot_heatmap(
        matrix=heatmap_v2,
        row_labels=row_labels,
        col_labels=col_labels,
        title="多维度评分热力图（自训练评分器）",
        output_dirs=output_dirs,
        filename="26_multidim_score_heatmap_v2.png",
    )

    win_counts = {scoring_model: {model_name: 0 for model_name in suite.generation_models} for scoring_model in suite.scoring_models}
    for prompt_index in range(1, len(suite.prompts) + 1):
        prompt_records = [item for item in records if item["prompt_index"] == prompt_index]
        for scoring_model_name in suite.scoring_models:
            winner = max(prompt_records, key=lambda item: item["scores"][scoring_model_name]["total_score"])
            win_counts[scoring_model_name][str(winner["model_name"])] += 1
    _plot_grouped_bar_chart(
        categories=suite.generation_models,
        series=[
            ("electric-score-v1", [win_counts["electric-score-v1"][model_name] for model_name in suite.generation_models], MODEL_COLORS["electric-score-v1"]),
            ("electric-score-v2", [win_counts["electric-score-v2"][model_name] for model_name in suite.generation_models], MODEL_COLORS["electric-score-v2"]),
        ],
        title="固定 Prompt 集获胜次数统计图",
        ylabel="获胜次数",
        output_dirs=output_dirs,
        filename="27_prompt_win_count_compare.png",
    )

    avg_generation_time = [
        float(np.mean([item["generation_seconds"] for item in records if item["model_name"] == model_name]))
        for model_name in suite.generation_models
    ]
    _plot_grouped_bar_chart(
        categories=suite.generation_models,
        series=[("平均耗时", avg_generation_time, MODEL_COLORS["sd15-electric-specialized"])],
        title="生成耗时对比图",
        ylabel="平均耗时（秒）",
        output_dirs=output_dirs,
        filename="28_generation_time_compare.png",
    )


def generate_thesis_figure_package(runtime_root: str | Path, output_dir: str | Path) -> dict[str, object]:
    _configure_matplotlib()
    runtime_root_path = Path(runtime_root)
    output_root = Path(output_dir)
    output_dirs = ensure_output_dirs(output_root)
    figure_specs = expected_figure_inventory()

    records = _build_generation_records(runtime_root_path, output_root)
    _render_generation_comparison_figures(records, output_dirs)
    _render_generation_training_figures(runtime_root_path, output_dirs)
    _render_scoring_training_figures(runtime_root_path, output_dirs)
    _render_evaluation_stats(records, output_dirs)
    write_figure_manifest(output_root / "figure_manifest.json", figure_specs)

    return {
        "figure_count": len(figure_specs),
        "manifest_path": str(output_root / "figure_manifest.json"),
        "output_dir": str(output_root),
        "paper_ready_dir": str(output_dirs["paper_ready"]),
    }
