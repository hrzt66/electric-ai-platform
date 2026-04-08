from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

try:
    from scripts.bootstrap import ensure_project_root_on_path
except ImportError:  # pragma: no cover - direct script execution path
    from bootstrap import ensure_project_root_on_path

project_root = ensure_project_root_on_path()
repo_root = project_root.parent

from app.benchmark_utils import parse_generation_training_log, parse_monitor_history, parse_prompt_module_text, summarize_benchmark_rows  # noqa: E402
from app.core.settings import get_settings  # noqa: E402
from app.dependencies import build_generation_service, build_runtime_registry  # noqa: E402
from app.runtimes.scorers.aesthetic_runtime import AestheticRuntime  # noqa: E402
from app.runtimes.scorers.clip_iqa_runtime import ClipIQARuntime  # noqa: E402
from app.runtimes.scorers.image_reward_runtime import ImageRewardRuntime  # noqa: E402
from app.runtimes.scorers.power_score_runtime import PowerScoreRuntime  # noqa: E402
from app.schemas.jobs import GenerateJob  # noqa: E402
from app.services.scoring_service import ScoringService  # noqa: E402


DEFAULT_GENERATION_MODELS = [
    "sd15-electric",
    "sd15-electric-specialized",
    "unipic2-kontext",
]
DEFAULT_SCORING_MODELS = [
    "electric-score-v1",
    "electric-score-v2",
    "electric-score-v3",
]
CHART_PALETTE = {
    "sd15-electric": "#34699A",
    "sd15-electric-specialized": "#F97316",
    "unipic2-kontext": "#059669",
    "electric-score-v1": "#4B5563",
    "electric-score-v2": "#2563EB",
    "electric-score-v3": "#DC2626",
}


@dataclass(slots=True)
class EvaluationPaths:
    output_root: Path
    charts_dir: Path
    tables_dir: Path
    prompt_source: Path
    generation_log: Path
    monitor_history: Path
    yolo_results: Path
    v2_metrics: Path
    evaluation_report: Path


def parse_args() -> argparse.Namespace:
    settings = get_settings()
    runtime_root = settings.runtime_root

    parser = argparse.ArgumentParser(description="Run real image generation benchmarks and build documentation charts.")
    parser.add_argument("--output-root", default=str(repo_root / "docs" / "assets" / "real-evaluation"))
    parser.add_argument(
        "--prompt-source",
        default=str(repo_root / "web-console" / "src" / "views" / "generate-defaults.ts"),
    )
    parser.add_argument(
        "--generation-log",
        default=str(
            runtime_root
            / "training"
            / "generation"
            / "sd15-electric-specialized"
            / "session-logs"
            / "train-generation-20260407-183903.err.log"
        ),
    )
    parser.add_argument(
        "--monitor-history",
        default=str(
            runtime_root
            / "training"
            / "generation"
            / "sd15-electric-specialized"
            / "session-logs"
            / "monitor-history.log"
        ),
    )
    parser.add_argument(
        "--yolo-results",
        default=str(
            runtime_root
            / "training"
            / "power-four-score"
            / "artifacts"
            / "yolo"
            / "electric-aux-detector"
            / "results.csv"
        ),
    )
    parser.add_argument(
        "--v2-metrics",
        default=str(runtime_root / "models" / "scoring" / "electric-score-v2" / "metrics.json"),
    )
    parser.add_argument(
        "--evaluation-report",
        default=str(
            runtime_root
            / "training"
            / "generation"
            / "sd15-electric-specialized"
            / "evaluation"
            / "evaluation_report.json"
        ),
    )
    parser.add_argument("--generation-models", nargs="*", default=DEFAULT_GENERATION_MODELS)
    parser.add_argument("--scoring-models", nargs="*", default=DEFAULT_SCORING_MODELS)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--guidance-scale", type=float, default=7.5)
    parser.add_argument("--width", type=int, default=512)
    parser.add_argument("--height", type=int, default=512)
    parser.add_argument("--limit-prompts", type=int, default=None)
    parser.add_argument("--skip-benchmark", action="store_true")
    parser.add_argument("--skip-charts", action="store_true")
    return parser.parse_args()


def resolve_paths(args: argparse.Namespace) -> EvaluationPaths:
    output_root = Path(args.output_root)
    charts_dir = output_root / "charts"
    tables_dir = output_root / "tables"
    charts_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    return EvaluationPaths(
        output_root=output_root,
        charts_dir=charts_dir,
        tables_dir=tables_dir,
        prompt_source=Path(args.prompt_source),
        generation_log=Path(args.generation_log),
        monitor_history=Path(args.monitor_history),
        yolo_results=Path(args.yolo_results),
        v2_metrics=Path(args.v2_metrics),
        evaluation_report=Path(args.evaluation_report),
    )


def configure_matplotlib() -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 140
    plt.rcParams["savefig.bbox"] = "tight"


def short_prompt_label(prompt: str, index: int) -> str:
    tokens = [token.strip(",.") for token in prompt.split() if token.strip(",.")]
    return f"P{index}: {' '.join(tokens[:4]).title()}"


def run_isolated_benchmarks(
    *,
    args: argparse.Namespace,
    paths: EvaluationPaths,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    benchmark_rows: list[dict[str, Any]] = []
    generated_images: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    script_path = Path(__file__).resolve()
    for model_name in args.generation_models:
        model_output_root = paths.output_root / "runs" / model_name
        command = [
            sys.executable,
            str(script_path),
            "--output-root",
            str(model_output_root),
            "--prompt-source",
            str(paths.prompt_source),
            "--generation-log",
            str(paths.generation_log),
            "--monitor-history",
            str(paths.monitor_history),
            "--yolo-results",
            str(paths.yolo_results),
            "--v2-metrics",
            str(paths.v2_metrics),
            "--evaluation-report",
            str(paths.evaluation_report),
            "--generation-models",
            model_name,
            "--scoring-models",
            *args.scoring_models,
            "--seed",
            str(args.seed),
            "--steps",
            str(args.steps),
            "--guidance-scale",
            str(args.guidance_scale),
            "--width",
            str(args.width),
            "--height",
            str(args.height),
            "--skip-charts",
        ]
        if args.limit_prompts is not None:
            command.extend(["--limit-prompts", str(args.limit_prompts)])

        result = subprocess.run(command, capture_output=True, check=False)
        model_tables_dir = model_output_root / "tables"
        benchmark_file = model_tables_dir / "benchmark-results.json"
        generated_file = model_tables_dir / "generated-images.csv"
        failure_file = model_tables_dir / "benchmark-failures.json"

        if benchmark_file.exists():
            benchmark_rows.extend(json.loads(benchmark_file.read_text(encoding="utf-8")))
        if generated_file.exists():
            generated_images.extend(pd.read_csv(generated_file).to_dict(orient="records"))
        if failure_file.exists():
            failures.extend(json.loads(failure_file.read_text(encoding="utf-8")))

        if result.returncode != 0 and not failure_file.exists():
            failures.append(
                {
                    "stage": "process",
                    "generation_model": model_name,
                    "error_type": "SubprocessFailed",
                    "error_message": f"benchmark subprocess exited with code {result.returncode}",
                    "stdout_tail": decode_subprocess_stream(result.stdout),
                    "stderr_tail": decode_subprocess_stream(result.stderr),
                }
            )

    return benchmark_rows, generated_images, failures


def decode_subprocess_stream(payload: bytes | None) -> str:
    if not payload:
        return ""
    for encoding in ("utf-8", "gb18030"):
        try:
            return payload.decode(encoding)[-2000:]
        except UnicodeDecodeError:
            continue
    return payload.decode("utf-8", errors="ignore")[-2000:]


def run_generation_benchmark(
    *,
    args: argparse.Namespace,
    prompt_set,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    registry = build_runtime_registry()
    generator = build_generation_service()

    legacy_clip = ClipIQARuntime(mode="visual_fidelity", device="cpu")
    legacy_text = ImageRewardRuntime(device="cpu")
    legacy_aesthetic = AestheticRuntime(device="cpu")
    legacy_service = ScoringService(
        text_runtime=legacy_text,
        aesthetics_runtime=legacy_aesthetic,
        shared_clip_runtime=legacy_clip,
        release_after_batch=False,
    )
    v3_runtime = PowerScoreRuntime(
        get_settings().scoring_model_dir / "electric-score-v3",
        device="cpu",
        text_runtime=legacy_text,
        visual_runtime=legacy_clip,
        physical_runtime=legacy_clip,
        aesthetics_runtime=legacy_aesthetic,
    )

    prompt_rows = prompt_set.positive_prompts[: args.limit_prompts] if args.limit_prompts else list(prompt_set.positive_prompts)
    benchmark_rows: list[dict[str, Any]] = []
    generated_images: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    job_id = 930000
    try:
        for model_name in args.generation_models:
            model_generated: list[dict[str, Any]] = []
            generation_failed = False
            for prompt_index, prompt in enumerate(prompt_rows, start=1):
                job_id += 1
                job = GenerateJob(
                    job_id=job_id,
                    prompt=prompt,
                    negative_prompt=prompt_set.negative_prompt,
                    model_name=model_name,
                    scoring_model_name="electric-score-v1",
                    seed=args.seed,
                    steps=args.steps,
                    guidance_scale=args.guidance_scale,
                    width=args.width,
                    height=args.height,
                    num_images=1,
                )

                try:
                    runtime = registry.get_generation_runtime(model_name)
                    started_at = time.perf_counter()
                    images = generator.generate(job, runtime)
                    generation_seconds = round(time.perf_counter() - started_at, 2)
                except Exception as exc:
                    generation_failed = True
                    failures.append(
                        {
                            "stage": "generation",
                            "generation_model": model_name,
                            "prompt_index": prompt_index,
                            "prompt": prompt,
                            "error_type": type(exc).__name__,
                            "error_message": str(exc),
                            "traceback": traceback.format_exc(),
                        }
                    )
                    break

                generated_record = {
                    "generation_model": model_name,
                    "prompt_index": prompt_index,
                    "prompt_label": short_prompt_label(prompt, prompt_index),
                    "prompt": prompt,
                    "negative_prompt": prompt_set.negative_prompt,
                    "image_path": images[0]["file_path"],
                    "seed": args.seed,
                    "steps": args.steps,
                    "guidance_scale": args.guidance_scale,
                    "generation_seconds": generation_seconds,
                }
                generated_images.append(generated_record)
                model_generated.append(generated_record)

            registry.release_generation_runtime(model_name)
            if generation_failed or not model_generated:
                continue

            if "electric-score-v2" in args.scoring_models:
                benchmark_rows.extend(score_with_v2(model_generated))
            if "electric-score-v1" in args.scoring_models:
                benchmark_rows.extend(score_with_v1(model_generated, legacy_service))
            if "electric-score-v3" in args.scoring_models:
                benchmark_rows.extend(score_with_v3(model_generated, v3_runtime))
    finally:
        try:
            registry.release_generation_runtime()
        except Exception:
            pass
        legacy_service.release_resources()
        v3_runtime.unload()

    return benchmark_rows, generated_images, failures


def score_with_v1(items: list[dict[str, Any]], service: ScoringService) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items:
        job = GenerateJob(
            job_id=0,
            prompt=item["prompt"],
            negative_prompt=item["negative_prompt"],
            model_name=item["generation_model"],
            scoring_model_name="electric-score-v1",
            seed=item["seed"],
            steps=item["steps"],
            guidance_scale=item["guidance_scale"],
            width=512,
            height=512,
            num_images=1,
        )
        started_at = time.perf_counter()
        scored = service.score_batch(job=job, images=[{"file_path": item["image_path"], "seed": item["seed"]}])[0]
        rows.append(
            build_result_row(
                source=item,
                scoring_model="electric-score-v1",
                score_payload=scored,
                scoring_seconds=round(time.perf_counter() - started_at, 2),
            )
        )
    return rows


def score_with_v2(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    runtime = PowerScoreRuntime(get_settings().scoring_model_dir / "electric-score-v2")
    rows: list[dict[str, Any]] = []
    try:
        for item in items:
            started_at = time.perf_counter()
            score_payload = runtime.score_image(item["image_path"], item["prompt"])
            rows.append(
                build_result_row(
                    source=item,
                    scoring_model="electric-score-v2",
                    score_payload=score_payload,
                    scoring_seconds=round(time.perf_counter() - started_at, 2),
                )
            )
    finally:
        runtime.unload()
    return rows


def score_with_v3(items: list[dict[str, Any]], runtime: PowerScoreRuntime) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items:
        started_at = time.perf_counter()
        score_payload = runtime.score_image(item["image_path"], item["prompt"])
        rows.append(
            build_result_row(
                source=item,
                scoring_model="electric-score-v3",
                score_payload=score_payload,
                scoring_seconds=round(time.perf_counter() - started_at, 2),
            )
        )
    return rows


def build_result_row(
    *,
    source: dict[str, Any],
    scoring_model: str,
    score_payload: dict[str, Any],
    scoring_seconds: float,
) -> dict[str, Any]:
    return {
        "generation_model": source["generation_model"],
        "scoring_model": scoring_model,
        "prompt_index": source["prompt_index"],
        "prompt_label": source["prompt_label"],
        "prompt": source["prompt"],
        "negative_prompt": source["negative_prompt"],
        "seed": source["seed"],
        "steps": source["steps"],
        "guidance_scale": source["guidance_scale"],
        "image_path": source["image_path"],
        "generation_seconds": source["generation_seconds"],
        "scoring_seconds": scoring_seconds,
        "visual_fidelity": round(float(score_payload["visual_fidelity"]), 2),
        "text_consistency": round(float(score_payload["text_consistency"]), 2),
        "physical_plausibility": round(float(score_payload["physical_plausibility"]), 2),
        "composition_aesthetics": round(float(score_payload["composition_aesthetics"]), 2),
        "total_score": round(float(score_payload["total_score"]), 2),
    }


def save_tables(
    *,
    benchmark_rows: list[dict[str, Any]],
    generated_images: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    paths: EvaluationPaths,
    args: argparse.Namespace,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    benchmark_df = pd.DataFrame(benchmark_rows)
    generated_df = pd.DataFrame(generated_images)
    summary_df = pd.DataFrame(summarize_benchmark_rows(benchmark_rows)) if benchmark_rows else pd.DataFrame()

    if not benchmark_df.empty:
        benchmark_df.to_csv(paths.tables_dir / "benchmark-results.csv", index=False, encoding="utf-8-sig")
        benchmark_df.to_json(paths.tables_dir / "benchmark-results.json", orient="records", indent=2, force_ascii=False)
    if not summary_df.empty:
        summary_df.to_csv(paths.tables_dir / "benchmark-summary.csv", index=False, encoding="utf-8-sig")
        summary_df.to_json(paths.tables_dir / "benchmark-summary.json", orient="records", indent=2, force_ascii=False)
    if not generated_df.empty:
        generated_df.to_csv(paths.tables_dir / "generated-images.csv", index=False, encoding="utf-8-sig")
    (paths.tables_dir / "benchmark-failures.json").write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8")

    run_summary = {
        "run_timestamp": pd.Timestamp.now(tz="Asia/Shanghai").isoformat(),
        "prompt_source": str(paths.prompt_source),
        "generation_models_requested": args.generation_models,
        "generation_models_completed": sorted({row["generation_model"] for row in benchmark_rows}),
        "scoring_models_completed": sorted({row["scoring_model"] for row in benchmark_rows}),
        "seed": args.seed,
        "steps": args.steps,
        "guidance_scale": args.guidance_scale,
        "width": args.width,
        "height": args.height,
        "benchmark_row_count": len(benchmark_rows),
        "failure_count": len(failures),
    }
    (paths.tables_dir / "run-summary.json").write_text(json.dumps(run_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return benchmark_df, summary_df


def build_charts(
    *,
    benchmark_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    generated_images: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    paths: EvaluationPaths,
) -> None:
    configure_matplotlib()

    generation_log_text = paths.generation_log.read_text(encoding="utf-8", errors="ignore")
    generation_loss_df = pd.DataFrame(parse_generation_training_log(generation_log_text))
    if not generation_loss_df.empty:
        plot_generation_training_loss(generation_loss_df, paths.charts_dir / "generation-training-loss.png")

    monitor_history_text = paths.monitor_history.read_text(encoding="utf-8", errors="ignore")
    monitor_df = pd.DataFrame(parse_monitor_history(monitor_history_text))
    if not monitor_df.empty:
        plot_generation_progress(monitor_df, paths.charts_dir / "generation-training-progress.png")

    yolo_df = pd.read_csv(paths.yolo_results)
    if not yolo_df.empty:
        plot_yolo_metrics(yolo_df, paths.charts_dir / "scoring-yolo-metrics.png")
        plot_yolo_losses(yolo_df, paths.charts_dir / "scoring-yolo-losses.png")

    v2_metrics = json.loads(paths.v2_metrics.read_text(encoding="utf-8"))
    plot_v2_regression_metrics(v2_metrics, paths.charts_dir / "scoring-v2-regression-metrics.png")

    if not summary_df.empty:
        plot_average_total_scores(summary_df, paths.charts_dir / "fixed-prompt-total-scores.png")
        plot_generation_time(summary_df, paths.charts_dir / "fixed-prompt-generation-time.png")
        plot_v3_dimension_breakdown(summary_df, paths.charts_dir / "fixed-prompt-v3-dimension-breakdown.png")
    if not benchmark_df.empty:
        plot_v3_prompt_lines(benchmark_df, paths.charts_dir / "fixed-prompt-v3-lines.png")
        build_contact_sheet(generated_images, failures, paths.charts_dir / "generated-sample-grid.png")
    if paths.evaluation_report.exists():
        build_validation_grid(
            json.loads(paths.evaluation_report.read_text(encoding="utf-8")),
            paths.charts_dir / "generation-validation-grid.png",
        )


def plot_generation_training_loss(df: pd.DataFrame, output_path: Path) -> None:
    chart_df = df.copy()
    chart_df["smoothed_loss"] = chart_df["step_loss"].rolling(window=120, min_periods=1).mean()
    fig, ax = plt.subplots(figsize=(9.6, 4.8))
    ax.plot(chart_df["step"], chart_df["step_loss"], color="#CBD5E1", linewidth=0.7, label="Raw step loss")
    ax.plot(chart_df["step"], chart_df["smoothed_loss"], color="#DC2626", linewidth=2.0, label="Rolling mean (120)")
    ax.set_title("SD15 Specialized Training Loss (2026-04-07 to 2026-04-08)")
    ax.set_xlabel("Training step")
    ax.set_ylabel("Step loss")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False)
    fig.savefig(output_path)
    plt.close(fig)


def plot_generation_progress(df: pd.DataFrame, output_path: Path) -> None:
    chart_df = df.copy()
    chart_df["timestamp"] = pd.to_datetime(chart_df["timestamp"])
    fig, ax = plt.subplots(figsize=(9.6, 4.8))
    ax.plot(chart_df["timestamp"], chart_df["step"], color="#2563EB", linewidth=2.0)
    ax.set_title("SD15 Specialized Training Progress Over Wall-Clock Time")
    ax.set_xlabel("Timestamp")
    ax.set_ylabel("Completed step")
    ax.grid(alpha=0.25)
    fig.autofmt_xdate()
    fig.savefig(output_path)
    plt.close(fig)


def plot_yolo_metrics(df: pd.DataFrame, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9.6, 4.8))
    for column in ["metrics/precision(B)", "metrics/recall(B)", "metrics/mAP50(B)", "metrics/mAP50-95(B)"]:
        ax.plot(df["epoch"], df[column], marker="o", linewidth=2.0, label=column.replace("metrics/", ""))
    ax.set_title("Electric Auxiliary Detector Metrics by Epoch")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Score")
    ax.set_xticks(df["epoch"].tolist())
    ax.grid(alpha=0.25)
    ax.legend(frameon=False, ncol=2)
    fig.savefig(output_path)
    plt.close(fig)


def plot_yolo_losses(df: pd.DataFrame, output_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), sharex=True)
    for column in ["train/box_loss", "train/cls_loss", "train/dfl_loss"]:
        axes[0].plot(df["epoch"], df[column], marker="o", linewidth=2.0, label=column.replace("train/", ""))
    axes[0].set_title("YOLO Train Loss")
    axes[0].set_xlabel("Epoch")
    axes[0].set_ylabel("Loss")
    axes[0].grid(alpha=0.25)
    axes[0].legend(frameon=False)

    for column in ["val/box_loss", "val/cls_loss", "val/dfl_loss"]:
        axes[1].plot(df["epoch"], df[column], marker="o", linewidth=2.0, label=column.replace("val/", ""))
    axes[1].set_title("YOLO Validation Loss")
    axes[1].set_xlabel("Epoch")
    axes[1].grid(alpha=0.25)
    axes[1].legend(frameon=False)
    fig.savefig(output_path)
    plt.close(fig)


def plot_v2_regression_metrics(metrics: dict[str, Any], output_path: Path) -> None:
    labels = ["text_consistency", "visual_fidelity", "composition_aesthetics", "physical_plausibility"]
    mae = [metrics[f"{label}_mae"] for label in labels]
    rmse = [metrics[f"{label}_rmse"] for label in labels]
    x = range(len(labels))
    fig, ax = plt.subplots(figsize=(10.5, 4.8))
    ax.bar([item - 0.18 for item in x], mae, width=0.36, label="MAE", color="#2563EB")
    ax.bar([item + 0.18 for item in x], rmse, width=0.36, label="RMSE", color="#F97316")
    ax.set_title("Electric Score V2 Regression Error by Dimension")
    ax.set_xlabel("Dimension")
    ax.set_ylabel("Error")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=12, ha="right")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False)
    fig.savefig(output_path)
    plt.close(fig)


def plot_average_total_scores(summary_df: pd.DataFrame, output_path: Path) -> None:
    pivot = summary_df.pivot(index="generation_model", columns="scoring_model", values="avg_total_score")
    models = list(pivot.index)
    scorers = list(pivot.columns)
    x = list(range(len(models)))
    width = 0.8 / max(len(scorers), 1)
    fig, ax = plt.subplots(figsize=(9.6, 4.8))
    for index, scorer in enumerate(scorers):
        offsets = [value - 0.4 + width / 2 + index * width for value in x]
        ax.bar(offsets, pivot[scorer].tolist(), width=width, label=scorer, color=CHART_PALETTE.get(scorer, "#6B7280"))
    ax.set_title("Average Total Score on the Fixed 7-Prompt Set")
    ax.set_xlabel("Generation model")
    ax.set_ylabel("Average total score")
    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=8)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False)
    fig.savefig(output_path)
    plt.close(fig)


def plot_generation_time(summary_df: pd.DataFrame, output_path: Path) -> None:
    grouped = summary_df.sort_values("generation_model").drop_duplicates("generation_model")
    fig, ax = plt.subplots(figsize=(8.8, 4.8))
    colors = [CHART_PALETTE.get(model, "#6B7280") for model in grouped["generation_model"]]
    ax.bar(grouped["generation_model"], grouped["avg_generation_seconds"], color=colors)
    ax.set_title("Average Generation Time per Image")
    ax.set_xlabel("Generation model")
    ax.set_ylabel("Seconds")
    ax.grid(axis="y", alpha=0.25)
    fig.savefig(output_path)
    plt.close(fig)


def plot_v3_dimension_breakdown(summary_df: pd.DataFrame, output_path: Path) -> None:
    v3_df = summary_df[summary_df["scoring_model"] == "electric-score-v3"].copy()
    if v3_df.empty:
        return
    dimensions = [
        ("avg_visual_fidelity", "Visual"),
        ("avg_text_consistency", "Text"),
        ("avg_physical_plausibility", "Physical"),
        ("avg_composition_aesthetics", "Aesthetic"),
    ]
    models = v3_df["generation_model"].tolist()
    x = list(range(len(models)))
    width = 0.8 / len(dimensions)
    fig, ax = plt.subplots(figsize=(10.5, 4.8))
    for index, (column, label) in enumerate(dimensions):
        offsets = [value - 0.4 + width / 2 + index * width for value in x]
        ax.bar(offsets, v3_df[column].tolist(), width=width, label=label)
    ax.set_title("Electric Score V3 Dimension Breakdown")
    ax.set_xlabel("Generation model")
    ax.set_ylabel("Average score")
    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=8)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False, ncol=4)
    fig.savefig(output_path)
    plt.close(fig)


def plot_v3_prompt_lines(benchmark_df: pd.DataFrame, output_path: Path) -> None:
    v3_df = benchmark_df[benchmark_df["scoring_model"] == "electric-score-v3"].copy()
    if v3_df.empty:
        return
    fig, ax = plt.subplots(figsize=(9.6, 4.8))
    for model_name in sorted(v3_df["generation_model"].unique()):
        model_df = v3_df[v3_df["generation_model"] == model_name].sort_values("prompt_index")
        ax.plot(
            model_df["prompt_index"],
            model_df["total_score"],
            marker="o",
            linewidth=2.0,
            label=model_name,
            color=CHART_PALETTE.get(model_name, "#6B7280"),
        )
    ax.set_title("Prompt-Wise Electric Score V3 Total Score")
    ax.set_xlabel("Prompt index")
    ax.set_ylabel("Total score")
    ax.set_xticks(sorted(v3_df["prompt_index"].unique()))
    ax.grid(alpha=0.25)
    ax.legend(frameon=False)
    fig.savefig(output_path)
    plt.close(fig)


def build_contact_sheet(generated_images: list[dict[str, Any]], failures: list[dict[str, Any]], output_path: Path) -> None:
    if not generated_images:
        return

    font = ImageFont.load_default()
    models = sorted({item["generation_model"] for item in generated_images})
    prompt_indices = sorted({int(item["prompt_index"]) for item in generated_images})
    cell_size = 210
    padding = 18
    header_height = 34
    row_label_width = 82

    canvas = Image.new(
        "RGB",
        (
            row_label_width + len(models) * (cell_size + padding) + padding,
            header_height + len(prompt_indices) * (cell_size + padding + 20) + padding,
        ),
        color="#F8FAFC",
    )
    draw = ImageDraw.Draw(canvas)

    for column_index, model_name in enumerate(models):
        x = row_label_width + padding + column_index * (cell_size + padding)
        draw.text((x, 8), model_name, fill="#111827", font=font)

    for row_index, prompt_index in enumerate(prompt_indices):
        y = header_height + padding + row_index * (cell_size + padding + 20)
        draw.text((10, y + cell_size // 2 - 6), f"P{prompt_index}", fill="#111827", font=font)

        for column_index, model_name in enumerate(models):
            x = row_label_width + padding + column_index * (cell_size + padding)
            cell = Image.new("RGB", (cell_size, cell_size + 20), color="white")
            cell_draw = ImageDraw.Draw(cell)

            matched = next(
                (
                    item
                    for item in generated_images
                    if int(item["prompt_index"]) == prompt_index and item["generation_model"] == model_name
                ),
                None,
            )
            if matched is not None and Path(matched["image_path"]).exists():
                with Image.open(matched["image_path"]).convert("RGB") as image:
                    image.thumbnail((cell_size, cell_size))
                    cell.paste(image, ((cell_size - image.width) // 2, (cell_size - image.height) // 2))
                cell_draw.rectangle((0, 0, cell_size - 1, cell_size - 1), outline="#CBD5E1", width=1)
                cell_draw.text((6, cell_size + 2), matched["prompt_label"], fill="#111827", font=font)
            else:
                failure = next(
                    (
                        item
                        for item in failures
                        if item.get("generation_model") == model_name and int(item.get("prompt_index", -1)) == prompt_index
                    ),
                    None,
                )
                cell_draw.rectangle((0, 0, cell_size - 1, cell_size - 1), outline="#DC2626", width=1)
                cell_draw.text((18, cell_size // 2 - 6), "Generation failed" if failure else "Missing sample", fill="#DC2626", font=font)

            canvas.paste(cell, (x, y))

    canvas.save(output_path)


def build_validation_grid(evaluation_items: list[dict[str, Any]], output_path: Path) -> None:
    if not evaluation_items:
        return

    font = ImageFont.load_default()
    columns = 2
    rows = math.ceil(len(evaluation_items) / columns)
    cell_width = 320
    cell_height = 260
    padding = 16
    canvas = Image.new(
        "RGB",
        (
            columns * (cell_width + padding) + padding,
            rows * (cell_height + padding) + padding,
        ),
        color="#F8FAFC",
    )
    for index, item in enumerate(evaluation_items):
        image_path = Path(item["image_path"])
        if not image_path.exists():
            continue
        with Image.open(image_path).convert("RGB") as image:
            image.thumbnail((cell_width, cell_height - 26))
            tile = Image.new("RGB", (cell_width, cell_height), color="white")
            tile.paste(image, ((cell_width - image.width) // 2, 8))
            draw = ImageDraw.Draw(tile)
            draw.text((8, cell_height - 20), short_prompt_label(item["prompt"], index + 1), fill="#111827", font=font)
        x = padding + (index % columns) * (cell_width + padding)
        y = padding + (index // columns) * (cell_height + padding)
        canvas.paste(tile, (x, y))
    canvas.save(output_path)


def main() -> int:
    args = parse_args()
    paths = resolve_paths(args)
    prompt_set = parse_prompt_module_text(paths.prompt_source.read_text(encoding="utf-8"))

    benchmark_rows: list[dict[str, Any]] = []
    generated_images: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    if not args.skip_benchmark:
        if len(args.generation_models) > 1:
            benchmark_rows, generated_images, failures = run_isolated_benchmarks(args=args, paths=paths)
        else:
            benchmark_rows, generated_images, failures = run_generation_benchmark(args=args, prompt_set=prompt_set)
    else:
        benchmark_file = paths.tables_dir / "benchmark-results.csv"
        generated_file = paths.tables_dir / "generated-images.csv"
        failure_file = paths.tables_dir / "benchmark-failures.json"
        if benchmark_file.exists():
            benchmark_rows = pd.read_csv(benchmark_file).to_dict(orient="records")
        if generated_file.exists():
            generated_images = pd.read_csv(generated_file).to_dict(orient="records")
        if failure_file.exists():
            failures = json.loads(failure_file.read_text(encoding="utf-8"))

    benchmark_df, summary_df = save_tables(
        benchmark_rows=benchmark_rows,
        generated_images=generated_images,
        failures=failures,
        paths=paths,
        args=args,
    )
    if not args.skip_charts:
        build_charts(
            benchmark_df=benchmark_df,
            summary_df=summary_df,
            generated_images=generated_images,
            failures=failures,
            paths=paths,
        )

    print(
        json.dumps(
            {
                "output_root": str(paths.output_root),
                "benchmark_rows": len(benchmark_rows),
                "generated_images": len(generated_images),
                "failures": len(failures),
                "tables_dir": str(paths.tables_dir),
                "charts_dir": str(paths.charts_dir),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
