from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class GenerationLogRow:
    step: int
    total_steps: int
    elapsed_seconds: float
    seconds_per_iteration: float | None
    iterations_per_second: float | None
    learning_rate: float
    step_loss: float


@dataclass(slots=True)
class YoloMetricRow:
    epoch: int
    elapsed_seconds: float
    train_box_loss: float
    train_cls_loss: float
    train_dfl_loss: float
    precision: float
    recall: float
    map50: float
    map50_95: float
    lr_pg0: float
    lr_pg1: float
    lr_pg2: float


GENERATION_STEP_PATTERN = re.compile(
    r"Steps:\s+\d+%\|.*?\|\s*(?P<step>\d+)/(?P<total>\d+)\s*\[(?P<elapsed>[0-9:]+)<[^,]*,\s*(?P<speed>[^,\]]+),\s*lr=(?P<lr>[0-9.eE+-]+),\s*step_loss=(?P<loss>[0-9.eE+-]+)\]"
)


def _parse_duration_seconds(value: str) -> float:
    chunks = [int(item) for item in value.split(":")]
    if len(chunks) == 2:
        minutes, seconds = chunks
        return float(minutes * 60 + seconds)
    if len(chunks) == 3:
        hours, minutes, seconds = chunks
        return float(hours * 3600 + minutes * 60 + seconds)
    raise ValueError(f"unsupported duration value: {value}")


def _parse_speed(value: str) -> tuple[float | None, float | None]:
    cleaned = value.strip()
    if cleaned.startswith("?"):
        return None, None
    if cleaned.endswith("s/it"):
        return float(cleaned[:-4]), None
    if cleaned.endswith("it/s"):
        return None, float(cleaned[:-4])
    return None, None


def parse_generation_training_log(path: Path) -> list[GenerationLogRow]:
    rows: list[GenerationLogRow] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = GENERATION_STEP_PATTERN.search(line)
        if match is None:
            continue
        seconds_per_iteration, iterations_per_second = _parse_speed(match.group("speed"))
        rows.append(
            GenerationLogRow(
                step=int(match.group("step")),
                total_steps=int(match.group("total")),
                elapsed_seconds=_parse_duration_seconds(match.group("elapsed")),
                seconds_per_iteration=seconds_per_iteration,
                iterations_per_second=iterations_per_second,
                learning_rate=float(match.group("lr")),
                step_loss=float(match.group("loss")),
            )
        )
    return rows


def load_yolo_results(path: Path) -> list[YoloMetricRow]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            YoloMetricRow(
                epoch=int(row["epoch"]),
                elapsed_seconds=float(row["time"]),
                train_box_loss=float(row["train/box_loss"]),
                train_cls_loss=float(row["train/cls_loss"]),
                train_dfl_loss=float(row["train/dfl_loss"]),
                precision=float(row["metrics/precision(B)"]),
                recall=float(row["metrics/recall(B)"]),
                map50=float(row["metrics/mAP50(B)"]),
                map50_95=float(row["metrics/mAP50-95(B)"]),
                lr_pg0=float(row["lr/pg0"]),
                lr_pg1=float(row["lr/pg1"]),
                lr_pg2=float(row["lr/pg2"]),
            )
            for row in reader
        ]


def load_scoring_v2_history(path: Path) -> list[dict[str, float]]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_scoring_v2_metrics(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))
