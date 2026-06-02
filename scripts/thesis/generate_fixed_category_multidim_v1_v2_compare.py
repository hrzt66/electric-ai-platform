#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "docs/image/thesis-refresh-20260427/图5.11_5类主目标检测样例评分统计_v1_v2.json"
OUT_PATH = ROOT / "docs/image/thesis-refresh-20260427/图5.11_固定类别多维评分细分统计（V1_V2对比）.png"


def configure() -> None:
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


def main() -> None:
    configure()
    rows = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    class_order = [
        ("solar_panel", "光伏板/光伏场"),
        ("transmission_tower", "输电塔"),
        ("wind_turbine", "风力发电机"),
        ("dam", "水电大坝"),
        ("substation_primary", "变电站一次设备"),
    ]
    model_order = [
        ("sd15-electric", "SD15 基础版"),
        ("sd15-electric-specialized", "SD15 电力专版"),
        ("ssd1b-electric", "SSD1B 电力版"),
        ("gpt-image-2", "GPT-Image-2"),
    ]
    dimensions = [
        ("visual_fidelity", "视觉保真"),
        ("text_consistency", "文本一致"),
        ("physical_plausibility", "物理合理"),
        ("composition_aesthetics", "构图美感"),
        ("total_score", "总分"),
    ]

    value_map = {(row["class_key"], row["model_key"]): row for row in rows}
    groups = len(class_order)
    models = len(model_order)
    dims = len(dimensions)
    gap = 1.4

    fig, axes = plt.subplots(2, 1, figsize=(15.5, 10.2), sharex=True)
    x_positions = []
    tick_labels = []

    for group_index, (class_key, class_label) in enumerate(class_order):
        group_base = group_index * (models * dims + gap)
        for model_index, (model_key, model_label) in enumerate(model_order):
            model_base = group_base + model_index * dims
            center = model_base + (dims - 1) / 2
            x_positions.append(center)
            tick_labels.append(model_label)

    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#6b7280"]

    for ax, prefix, title in [
        (axes[0], "v1", "V1 评分器细分结果"),
        (axes[1], "v2", "V2 评分器细分结果"),
    ]:
        for group_index, (class_key, class_label) in enumerate(class_order):
            group_base = group_index * (models * dims + gap)
            for model_index, (model_key, model_label) in enumerate(model_order):
                record = value_map[(class_key, model_key)]
                model_base = group_base + model_index * dims
                values = [record[f"{prefix}_{dim_key}"] for dim_key, _ in dimensions]
                bars = ax.bar(
                    np.arange(model_base, model_base + dims),
                    values,
                    color=colors,
                    width=0.82,
                    edgecolor="white",
                    linewidth=0.5,
                )
                for bar, value in zip(bars, values, strict=True):
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + 0.9,
                        f"{value:.1f}",
                        ha="center",
                        va="bottom",
                        fontsize=7,
                        rotation=90,
                        color="#374151",
                    )

            left = group_base - 0.6
            right = group_base + models * dims - 0.4
            ax.axvspan(left, right, color="#f8fafc" if group_index % 2 == 0 else "#ffffff", zorder=0)
            ax.text(
                (left + right) / 2,
                103.5,
                class_label,
                ha="center",
                va="bottom",
                fontsize=11,
                color="#111827",
                fontweight="bold",
            )

        ax.set_ylim(0, 108)
        ax.set_ylabel("评分")
        ax.set_title(title, fontsize=16, fontweight="bold")
        ax.grid(axis="y", alpha=0.25)

    axes[1].set_xticks(x_positions)
    axes[1].set_xticklabels(tick_labels, rotation=20, ha="right", fontsize=9)

    legend_handles = [plt.Rectangle((0, 0), 1, 1, color=color) for color in colors]
    fig.legend(
        legend_handles,
        [label for _, label in dimensions],
        loc="upper center",
        ncol=5,
        frameon=False,
        bbox_to_anchor=(0.5, 0.965),
    )
    fig.suptitle("固定类别多维评分细分统计（V1/V2 对比）", fontsize=22, fontweight="bold", y=0.995)
    fig.text(0.5, 0.02, "固定类别顺序：光伏板/光伏场、输电塔、风力发电机、水电大坝、变电站一次设备", ha="center", fontsize=10)
    fig.tight_layout(rect=(0.02, 0.05, 0.98, 0.93))

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, bbox_inches="tight")
    plt.close(fig)
    print(OUT_PATH)


if __name__ == "__main__":
    main()
