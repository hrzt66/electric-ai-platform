from __future__ import annotations

import csv
import json
import os
from collections.abc import Mapping
from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(slots=True)
class YoloEpochMetricsRecord:
    epoch: int
    checked_at: str
    mAP50: float
    mAP50_95: float
    precision: float
    recall: float
    status: str
    weights_path: str


def read_latest_epoch(results_csv: Path) -> int | None:
    if not results_csv.exists():
        return None

    latest_epoch: int | None = None
    with results_csv.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            raw_epoch = str(row.get("epoch", "")).strip()
            if not raw_epoch:
                continue
            try:
                latest_epoch = int(raw_epoch)
            except ValueError:
                continue
    return latest_epoch


def read_epoch_row(results_csv: Path, epoch: int) -> dict[str, str] | None:
    if not results_csv.exists():
        return None

    target = str(epoch)
    with results_csv.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if str(row.get("epoch", "")).strip() == target:
                return dict(row)
    return None


def read_logged_epochs(metrics_log: Path) -> set[int]:
    if not metrics_log.exists():
        return set()

    epochs: set[int] = set()
    with metrics_log.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            raw_epoch = payload.get("epoch")
            try:
                epochs.add(int(raw_epoch))
            except (TypeError, ValueError):
                continue
    return epochs


def next_pending_epoch(*, results_csv: Path, metrics_log: Path) -> int | None:
    latest_epoch = read_latest_epoch(results_csv)
    if latest_epoch is None:
        return None
    if latest_epoch in read_logged_epochs(metrics_log):
        return None
    return latest_epoch


def append_metrics_record(metrics_log: Path, record: Mapping[str, object] | YoloEpochMetricsRecord) -> None:
    payload = asdict(record) if isinstance(record, YoloEpochMetricsRecord) else dict(record)
    metrics_log.parent.mkdir(parents=True, exist_ok=True)
    with metrics_log.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def build_metrics_payload(*, record: YoloEpochMetricsRecord, extra: Mapping[str, object] | None = None) -> dict[str, object]:
    payload = asdict(record)
    if extra:
        payload.update(dict(extra))
    return payload


def build_metrics_record(*, epoch: int, weights_path: Path, metrics: Mapping[str, object], status: str = "ok") -> YoloEpochMetricsRecord:
    def _float(key: str) -> float:
        try:
            return round(float(metrics.get(key, 0.0)), 6)
        except (TypeError, ValueError):
            return 0.0

    return YoloEpochMetricsRecord(
        epoch=epoch,
        checked_at=datetime.now(timezone.utc).isoformat(),
        mAP50=_float("metrics/mAP50(B)"),
        mAP50_95=_float("metrics/mAP50-95(B)"),
        precision=_float("metrics/precision(B)"),
        recall=_float("metrics/recall(B)"),
        status=status,
        weights_path=str(weights_path),
    )


def build_metrics_record_from_results_row(*, row: Mapping[str, object], weights_path: Path, status: str = "ok") -> YoloEpochMetricsRecord:
    raw_epoch = row.get("epoch")
    try:
        epoch = int(float(raw_epoch))
    except (TypeError, ValueError):
        raise ValueError(f"invalid epoch value in results row: {raw_epoch!r}") from None
    return build_metrics_record(epoch=epoch, weights_path=weights_path, metrics=row, status=status)


def build_error_record(*, epoch: int, weights_path: Path, message: str) -> dict[str, object]:
    return {
        "epoch": epoch,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "status": "error",
        "error": message,
        "weights_path": str(weights_path),
    }


def process_is_running(pid: int | None) -> bool:
    if pid is None or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True
