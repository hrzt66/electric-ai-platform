from __future__ import annotations

import csv
from pathlib import Path


def test_build_metrics_record_from_results_row_reads_builtin_map_columns() -> None:
    from training.reporting.yolo_epoch_metrics import build_metrics_record_from_results_row

    record = build_metrics_record_from_results_row(
        row={
            "epoch": "20",
            "metrics/precision(B)": "0.8123",
            "metrics/recall(B)": "0.4567",
            "metrics/mAP50(B)": "0.6123",
            "metrics/mAP50-95(B)": "0.4012",
        },
        weights_path=Path("/tmp/last.pt"),
    )

    assert record.epoch == 20
    assert record.precision == 0.8123
    assert record.recall == 0.4567
    assert record.mAP50 == 0.6123
    assert record.mAP50_95 == 0.4012
    assert record.weights_path == "/tmp/last.pt"


def test_read_epoch_row_returns_specific_epoch_metrics_row(tmp_path: Path) -> None:
    from training.reporting.yolo_epoch_metrics import read_epoch_row

    results_csv = tmp_path / "results.csv"
    with results_csv.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "epoch",
                "metrics/precision(B)",
                "metrics/recall(B)",
                "metrics/mAP50(B)",
                "metrics/mAP50-95(B)",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "epoch": "19",
                "metrics/precision(B)": "0.80",
                "metrics/recall(B)": "0.40",
                "metrics/mAP50(B)": "0.50",
                "metrics/mAP50-95(B)": "0.30",
            }
        )
        writer.writerow(
            {
                "epoch": "20",
                "metrics/precision(B)": "0.82",
                "metrics/recall(B)": "0.46",
                "metrics/mAP50(B)": "0.61",
                "metrics/mAP50-95(B)": "0.40",
            }
        )

    row = read_epoch_row(results_csv, 20)

    assert row is not None
    assert row["epoch"] == "20"
    assert row["metrics/mAP50(B)"] == "0.61"


def test_build_metrics_payload_merges_extra_run_metadata() -> None:
    from training.reporting.yolo_epoch_metrics import YoloEpochMetricsRecord, build_metrics_payload

    payload = build_metrics_payload(
        record=YoloEpochMetricsRecord(
            epoch=5,
            checked_at="2026-04-24T00:00:00+00:00",
            mAP50=0.5123,
            mAP50_95=0.3012,
            precision=0.6,
            recall=0.4,
            status="ok",
            weights_path="/tmp/last.pt",
        ),
        extra={"profile": "high_map", "dataset_variant": "high_map_v1"},
    )

    assert payload["epoch"] == 5
    assert payload["profile"] == "high_map"
    assert payload["dataset_variant"] == "high_map_v1"
