from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

try:
    from scripts.bootstrap import ensure_project_root_on_path
except ImportError:  # pragma: no cover - direct script execution path
    from bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from ultralytics import YOLO

from training.reporting.yolo_epoch_metrics import (
    append_metrics_record,
    build_metrics_payload,
    build_error_record,
    build_metrics_record,
    build_metrics_record_from_results_row,
    next_pending_epoch,
    process_is_running,
    read_epoch_row,
    read_latest_epoch,
    read_logged_epochs,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monitor YOLO training and log mAP metrics once per finished epoch.")
    parser.add_argument("--results-csv", type=Path, required=True, help="Ultralytics results.csv path.")
    parser.add_argument("--weights", type=Path, required=True, help="Path to last.pt to validate.")
    parser.add_argument("--data", type=Path, required=True, help="YOLO dataset yaml used for validation.")
    parser.add_argument("--metrics-log", type=Path, required=True, help="JSONL path to append epoch metrics.")
    parser.add_argument("--imgsz", type=int, default=512, help="Validation image size.")
    parser.add_argument("--batch", type=int, default=4, help="Validation batch size.")
    parser.add_argument("--device", type=str, default="cpu", help="Validation device, default cpu to avoid interfering with training.")
    parser.add_argument(
        "--mode",
        type=str,
        choices=("validate", "csv"),
        default="validate",
        help="validate: run model.val() on each finished epoch; csv: mirror Ultralytics built-in validation metrics from results.csv.",
    )
    parser.add_argument("--poll-seconds", type=float, default=20.0, help="Polling interval while waiting for a new epoch.")
    parser.add_argument("--watch-pid", type=int, default=None, help="Training PID. The monitor exits after the process ends and the latest epoch is logged.")
    parser.add_argument("--profile", type=str, default="unknown", help="Run profile label written into metrics_log.")
    parser.add_argument("--dataset-variant", type=str, default="unknown", help="Dataset variant label written into metrics_log.")
    return parser.parse_args()


def _validate_epoch(*, epoch: int, weights_path: Path, data_path: Path, imgsz: int, batch: int, device: str) -> dict[str, object]:
    model = YOLO(str(weights_path))
    metrics = model.val(
        data=str(data_path),
        imgsz=imgsz,
        batch=batch,
        device=device,
        split="val",
        rect=True,
        plots=False,
        verbose=False,
    )
    payload = getattr(metrics, "results_dict", None)
    if not isinstance(payload, dict):
        payload = {}
    record = build_metrics_record(epoch=epoch, weights_path=weights_path, metrics=payload)
    return {
        "epoch": record.epoch,
        "checked_at": record.checked_at,
        "mAP50": record.mAP50,
        "mAP50_95": record.mAP50_95,
        "precision": record.precision,
        "recall": record.recall,
        "status": record.status,
        "weights_path": record.weights_path,
    }


def main() -> int:
    args = _parse_args()
    extra = {"profile": args.profile, "dataset_variant": args.dataset_variant}

    while True:
        pending_epoch = next_pending_epoch(results_csv=args.results_csv, metrics_log=args.metrics_log)
        if pending_epoch is not None and (args.mode == "csv" or args.weights.exists()):
            try:
                if args.mode == "csv":
                    row = read_epoch_row(args.results_csv, pending_epoch)
                    if row is None:
                        raise RuntimeError(f"missing results.csv row for epoch {pending_epoch}")
                    metrics_record = build_metrics_record_from_results_row(row=row, weights_path=args.weights)
                    record = {
                        "epoch": metrics_record.epoch,
                        "checked_at": metrics_record.checked_at,
                        "mAP50": metrics_record.mAP50,
                        "mAP50_95": metrics_record.mAP50_95,
                        "precision": metrics_record.precision,
                        "recall": metrics_record.recall,
                        "status": metrics_record.status,
                        "weights_path": metrics_record.weights_path,
                    }
                else:
                    record = _validate_epoch(
                        epoch=pending_epoch,
                        weights_path=args.weights,
                        data_path=args.data,
                        imgsz=args.imgsz,
                        batch=args.batch,
                        device=args.device,
                    )
            except Exception as exc:  # pragma: no cover - runtime fallback
                record = build_error_record(epoch=pending_epoch, weights_path=args.weights, message=str(exc))
                print(f"[epoch {pending_epoch}] validation failed: {exc}", flush=True)
            else:
                print(
                    f"[epoch {pending_epoch}] mAP50={record['mAP50']:.4f} mAP50-95={record['mAP50_95']:.4f}",
                    flush=True,
                )
            if isinstance(record, dict) and record.get("status") == "error":
                payload = dict(record)
                payload.update(extra)
                append_metrics_record(args.metrics_log, payload)
            else:
                metrics_record = build_metrics_record_from_results_row(row=read_epoch_row(args.results_csv, pending_epoch) or {}, weights_path=args.weights) if args.mode == "csv" else None
                if metrics_record is not None:
                    append_metrics_record(args.metrics_log, build_metrics_payload(record=metrics_record, extra=extra))
                else:
                    append_metrics_record(args.metrics_log, {**record, **extra})
        else:
            latest_epoch = read_latest_epoch(args.results_csv)
            if args.watch_pid is not None and not process_is_running(args.watch_pid):
                if latest_epoch is None:
                    break
                if latest_epoch in read_logged_epochs(args.metrics_log):
                    break
            time.sleep(max(args.poll_seconds, 1.0))
            continue

        latest_epoch = read_latest_epoch(args.results_csv)
        if args.watch_pid is not None and not process_is_running(args.watch_pid):
            if latest_epoch is None or next_pending_epoch(results_csv=args.results_csv, metrics_log=args.metrics_log) is None:
                break

        time.sleep(max(args.poll_seconds, 1.0))

    print(
        json.dumps(
            {
                "status": "completed",
                "results_csv": str(args.results_csv),
                "metrics_log": str(args.metrics_log),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
