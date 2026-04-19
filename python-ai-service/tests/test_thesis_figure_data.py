from pathlib import Path


def test_load_prompt_suite_returns_fixed_eight_prompts():
    from training.reporting.thesis_figure_config import build_prompt_suite

    suite = build_prompt_suite()

    assert suite.seed == 42
    assert len(suite.prompts) == 8
    assert suite.negative_prompt.startswith("cartoon, CGI, illustration")
    assert suite.generation_models == ["sd15-electric", "sd15-electric-specialized", "ssd1b-electric"]
    assert suite.scoring_models == ["electric-score-v1", "electric-score-v2"]


def test_parse_generation_training_log_extracts_loss_lr_and_progress(tmp_path: Path):
    from training.reporting.thesis_figure_data import parse_generation_training_log

    log_path = tmp_path / "training.log"
    log_path.write_text(
        "Steps:   0%|          | 0/500 [00:03<?, ?it/s, lr=0, step_loss=0.356]\n"
        "Steps:   1%|          | 3/500 [00:48<2:08:43, 15.54s/it, lr=7.5e-7, step_loss=0.00447]\n",
        encoding="utf-8",
    )

    rows = parse_generation_training_log(log_path)

    assert len(rows) == 2
    assert rows[0].learning_rate == 0.0
    assert rows[0].elapsed_seconds == 3.0
    assert rows[1].step == 3
    assert rows[1].total_steps == 500
    assert rows[1].seconds_per_iteration == 15.54
    assert rows[1].iterations_per_second is None
    assert rows[1].step_loss == 0.00447


def test_load_yolo_results_builds_metric_series(tmp_path: Path):
    from training.reporting.thesis_figure_data import load_yolo_results

    csv_path = tmp_path / "results.csv"
    csv_path.write_text(
        "epoch,time,train/box_loss,train/cls_loss,train/dfl_loss,metrics/precision(B),metrics/recall(B),metrics/mAP50(B),metrics/mAP50-95(B),val/box_loss,val/cls_loss,val/dfl_loss,lr/pg0,lr/pg1,lr/pg2\n"
        "1,10.0,2.1,4.4,1.8,0.1,0.2,0.3,0.15,0,0,0,0.001,0.001,0.001\n",
        encoding="utf-8",
    )

    rows = load_yolo_results(csv_path)

    assert len(rows) == 1
    assert rows[0].epoch == 1
    assert rows[0].elapsed_seconds == 10.0
    assert rows[0].train_box_loss == 2.1
    assert rows[0].precision == 0.1
    assert rows[0].map50 == 0.3
    assert rows[0].map50_95 == 0.15


def test_load_scoring_v2_metrics_and_history_round_trip(tmp_path: Path):
    from training.reporting.thesis_figure_data import load_scoring_v2_history, load_scoring_v2_metrics

    history_path = tmp_path / "history.json"
    history_path.write_text('[{"epoch": 1, "train_loss": 2.5, "val_mae": 9.1}]', encoding="utf-8")

    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text(
        '{"test_metrics": {"per_target_mae": {"visual_fidelity": 7.1, "text_consistency": 1.3}}}',
        encoding="utf-8",
    )

    history = load_scoring_v2_history(history_path)
    metrics = load_scoring_v2_metrics(metrics_path)

    assert history == [{"epoch": 1, "train_loss": 2.5, "val_mae": 9.1}]
    assert metrics["test_metrics"]["per_target_mae"]["visual_fidelity"] == 7.1
