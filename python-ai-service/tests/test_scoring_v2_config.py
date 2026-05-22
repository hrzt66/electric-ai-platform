import json
from pathlib import Path

from PIL import Image
import torch

from training.common.jsonl import write_jsonl


def _write_fake_manifest(manifest_root: Path) -> dict[str, str]:
    return _write_fake_manifest_with_yolo_dim(manifest_root, yolo_dim=16)


def _write_fake_manifest_with_yolo_dim(manifest_root: Path, *, yolo_dim: int) -> dict[str, str]:
    image_root = manifest_root / "images"
    image_root.mkdir(parents=True, exist_ok=True)
    rows: dict[str, list[dict[str, object]]] = {"train": [], "val": [], "test": []}
    for split_index, split in enumerate(rows):
        for item_index in range(2):
            image_path = image_root / f"{split}_{item_index}.png"
            Image.new("RGB", (96, 96), color=(120 + item_index * 10, 128, 136)).save(image_path)
            rows[split].append(
                {
                    "image_path": str(image_path),
                    "prompt": "realistic electric power inspection photo with tower and insulator",
                    "split": split,
                    "source_name": "unit-test",
                    "detections": [
                        {"class_name": "tower", "confidence": 1.0, "bbox": [0.5, 0.5, 0.3, 0.4]},
                        {"class_name": "insulator", "confidence": 1.0, "bbox": [0.6, 0.4, 0.12, 0.12]},
                    ],
                    "yolo_features": [0.0] * yolo_dim,
                    "targets": {
                        "visual_fidelity": 82.0,
                        "text_consistency": 88.0,
                        "physical_plausibility": 85.0,
                        "composition_aesthetics": 79.0,
                    },
                }
            )
    manifests = {}
    for split, split_rows in rows.items():
        path = manifest_root / f"{split}.jsonl"
        write_jsonl(path, split_rows)
        manifests[split] = str(path)
    return manifests


def test_scoring_v2_defaults_target_100_epochs() -> None:
    from training.scoring.config import ScoringTrainingConfig

    config = ScoringTrainingConfig()

    assert config.bundle_name == "electric-score-v2"
    assert config.epochs == 100
    assert config.device_preference == "mps"
    assert config.yolo_model_name == "yolo11s.pt"
    assert config.yolo_image_size == 640
    assert config.yolo_batch_size == 6
    assert config.yolo_epochs == 40
    assert config.yolo_profile == "yolo11s_640_best_import_v1"
    assert config.yolo_train_variant == "imported_remap_v1"
    assert config.physical_part_yolo_profile == "electric_physical_parts_blade_focus_v1"
    assert config.physical_part_yolo_train_variant == "blade_focus_v1"
    assert config.reuse_existing_physical_part_yolo_aux is True
    assert config.physical_part_yolo_dataset_yaml == "datasets/yolo-physical-parts-v1/dataset.yaml"
    assert config.yolo_optimizer == "AdamW"
    assert config.yolo_learning_rate == 2e-4
    assert config.yolo_lrf == 0.05
    assert config.yolo_weight_decay == 5e-4
    assert config.yolo_warmup_epochs == 3.0
    assert config.yolo_patience == 10
    assert config.yolo_validate_each_epoch is True
    assert config.yolo_run_final_validation is True
    assert config.yolo_rect is False
    assert config.yolo_mosaic == 0.1
    assert config.yolo_close_mosaic == 10
    assert config.yolo_mixup == 0.0
    assert config.yolo_copy_paste == 0.0
    assert config.yolo_translate == 0.02
    assert config.yolo_scale == 0.15
    assert config.yolo_hsv_h == 0.01
    assert config.yolo_hsv_s == 0.4
    assert config.yolo_hsv_v == 0.25
    assert config.yolo_min_train_instances == 50
    assert config.yolo_min_val_instances == 10
    assert config.yolo_dataset_yaml == "datasets/yolo-image2-remapped-scoring-6class-v1/dataset.yaml"
    assert config.power_classes == [
        "substation_primary",
        "transmission_tower",
        "insulator_string",
        "wind_turbine",
        "solar_panel",
        "dam",
    ]
    assert config.total_weights["text_consistency"] == 0.37
    assert config.use_pretrained_image_backbone is True
    assert config.image_backbone_trainable_stages == 2
    assert config.max_train_samples == 1536
    assert config.max_val_samples == 256
    assert config.max_test_samples == 256
    source_names = [str(source["name"]) for source in config.dataset_sources]
    source_kinds = {str(source["name"]): str(source["kind"]) for source in config.dataset_sources}
    assert source_names == [
        "substation-object-detection-yolo",
        "powerline-components-and-faults",
        "dior-superclasses",
        "wind-turbine-aerial",
        "solar-plants-brazil-yolo",
    ]
    assert source_kinds["substation-object-detection-yolo"] == "local_detection"
    assert source_kinds["powerline-components-and-faults"] == "local_detection"
    assert source_kinds["dior-superclasses"] == "local_detection"
    assert source_kinds["wind-turbine-aerial"] == "local_detection"
    assert source_kinds["solar-plants-brazil-yolo"] == "local_detection"
    assert "score_bands" not in config.bundle_payload()
    assert config.bundle_payload()["yolo_profile"] == "yolo11s_640_best_import_v1"
    assert config.bundle_payload()["yolo_train_variant"] == "imported_remap_v1"
    assert config.bundle_payload()["physical_part_yolo_profile"] == "electric_physical_parts_blade_focus_v1"
    assert config.bundle_payload()["physical_part_yolo_train_variant"] == "blade_focus_v1"
    assert config.bundle_payload()["physical_part_yolo_dataset_yaml"] == "datasets/yolo-physical-parts-v1/dataset.yaml"


def test_scoring_v2_exposes_yolo11_training_profile() -> None:
    from training.scoring.config import ScoringTrainingConfig

    config = ScoringTrainingConfig()

    assert config.yolo_model_name == "yolo11s.pt"
    assert config.yolo_profile == "yolo11s_640_best_import_v1"
    assert config.yolo_train_variant == "imported_remap_v1"
    assert config.yolo_optimizer == "AdamW"
    assert config.yolo_learning_rate == 2e-4
    assert config.yolo_lrf == 0.05
    assert config.yolo_weight_decay == 5e-4
    assert config.yolo_warmup_epochs == 3.0
    assert config.yolo_image_size == 640
    assert config.yolo_batch_size == 6
    assert config.yolo_validate_each_epoch is True
    assert config.yolo_rect is False
    assert config.yolo_mosaic == 0.1
    assert config.yolo_close_mosaic == 10
    assert config.yolo_patience == 10
    assert config.yolo_mixup == 0.0
    assert config.yolo_copy_paste == 0.0
    assert config.yolo_translate == 0.02
    assert config.yolo_scale == 0.15
    assert config.yolo_hsv_h == 0.01
    assert config.yolo_hsv_s == 0.4
    assert config.yolo_hsv_v == 0.25


def test_scoring_v2_only_unfreezes_the_tail_backbone_stages() -> None:
    from training.scoring.modeling import FourDimScoreModel, configure_image_backbone_trainability

    model = FourDimScoreModel(vocab_size=4, yolo_feature_dim=16, target_dim=4, pretrained_backbone=False)
    configure_image_backbone_trainability(model.image_backbone, trainable_stages=2)

    stages = list(model.image_backbone.children())
    frozen_prefix = stages[:-2]
    trainable_tail = stages[-2:]

    assert frozen_prefix
    assert trainable_tail
    assert all(not parameter.requires_grad for stage in frozen_prefix for parameter in stage.parameters())
    assert all(any(parameter.requires_grad for parameter in stage.parameters()) for stage in trainable_tail)


def test_scoring_v2_pipeline_builds_student_bundle(monkeypatch, tmp_path) -> None:
    from app.core.settings import Settings
    from training.scoring.config import ScoringTrainingConfig
    from training.scoring import pipeline as pipeline_module

    manifest_root = tmp_path / "manifests"
    manifests = _write_fake_manifest_with_yolo_dim(manifest_root, yolo_dim=8)

    monkeypatch.setattr(pipeline_module, "download_dataset_archives", lambda *args, **kwargs: [])
    monkeypatch.setattr(pipeline_module, "extract_archives", lambda *args, **kwargs: [])
    monkeypatch.setattr(pipeline_module, "materialize_hf_detection_datasets", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        pipeline_module,
        "select_supported_power_classes",
        lambda **kwargs: {
            "classes": ["tower", "insulator"],
            "dropped_classes": ["line"],
            "all_train_counts": {"tower": 10, "insulator": 10, "line": 5},
            "all_val_counts": {"tower": 5, "insulator": 5, "line": 1},
        },
    )
    monkeypatch.setattr(
        pipeline_module,
        "build_scoring_manifests",
        lambda **kwargs: {
            "train_count": 2,
            "val_count": 2,
            "test_count": 2,
            "manifests": manifests,
            "yolo_datasets": [],
        },
    )

    settings = Settings(runtime_root=tmp_path)
    report = pipeline_module.run_scoring_training(
        settings=settings,
        config=ScoringTrainingConfig(
            epochs=1,
            train_batch_size=1,
            eval_batch_size=1,
            max_train_samples=2,
            max_val_samples=2,
            max_test_samples=2,
            yolo_dataset_yaml=None,
        ),
    )

    bundle_dir = tmp_path / "scoring" / "electric-score-v2"
    bundle_config = json.loads((bundle_dir / "bundle_config.json").read_text(encoding="utf-8"))
    metrics = json.loads((bundle_dir / "metrics.json").read_text(encoding="utf-8"))
    epoch_metrics = json.loads(
        (tmp_path / "training" / "scoring" / "electric-score-v2" / "epoch_metrics" / "epoch_001.json").read_text(
            encoding="utf-8"
        )
    )

    assert report["scoring_model_root"] == str(bundle_dir)
    assert report["epochs"] == 1
    assert report["active_classes"] == ["tower", "insulator"]
    assert report["epoch_metrics_dir"] == str(tmp_path / "training" / "scoring" / "electric-score-v2" / "epoch_metrics")
    assert bundle_config["runtime_type"] == "student"
    assert bundle_config["epochs"] == 1
    assert bundle_config["classes"] == ["tower", "insulator"]
    assert bundle_config["yolo_feature_dim"] == 8
    assert (bundle_dir / "student_best.pt").exists()
    assert (bundle_dir / "vocab.json").exists()
    assert metrics["test_metrics"]["mae"] >= 0.0
    assert epoch_metrics["epoch"] == 1
    assert "train_loss" in epoch_metrics
    assert "val_mae" in epoch_metrics
    assert "val_per_target_mae" in epoch_metrics


def test_scoring_v2_yolo_training_uses_explicit_high_map_profile(monkeypatch, tmp_path: Path) -> None:
    from training.scoring import pipeline as pipeline_module
    from training.scoring.config import ScoringTrainingConfig

    dataset_yaml = tmp_path / "tiny-dataset.yaml"
    dataset_yaml.write_text(
        "path: .\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n  - substation_primary\n  - transmission_tower\n  - insulator_string\n  - wind_turbine\n  - solar_panel\n  - dam\n",
        encoding="utf-8",
    )

    recorded: dict[str, object] = {}

    class _FakeMetrics:
        results_dict = {
            "metrics/mAP50(B)": 0.25,
            "metrics/mAP50-95(B)": 0.11,
        }

    class _FakeYOLO:
        def __init__(self, model_name: str) -> None:
            recorded["model_name"] = model_name

        def train(self, **kwargs):
            recorded["train"] = kwargs
            save_dir = tmp_path / "yolo-save"
            (save_dir / "weights").mkdir(parents=True, exist_ok=True)
            (save_dir / "weights" / "best.pt").write_bytes(b"fake-weights")
            return type("TrainResult", (), {"save_dir": str(save_dir)})()

        def val(self, **kwargs):
            recorded["val"] = kwargs
            return _FakeMetrics()

    monkeypatch.setattr(pipeline_module, "YOLO", _FakeYOLO)

    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    report = pipeline_module._train_yolo_auxiliary(
        training_root=tmp_path / "training",
        bundle_dir=bundle_dir,
        manifest_summary={"yolo_datasets": [str(dataset_yaml)]},
        config=ScoringTrainingConfig(yolo_dataset_yaml=str(dataset_yaml)),
        device=torch.device("mps"),
        active_classes=[
            "substation_primary",
            "transmission_tower",
            "insulator_string",
            "wind_turbine",
            "solar_panel",
            "dam",
        ],
    )

    train_kwargs = recorded["train"]
    val_kwargs = recorded["val"]

    assert recorded["model_name"] == "yolo11s.pt"
    assert train_kwargs["imgsz"] == 640
    assert train_kwargs["batch"] == 6
    assert train_kwargs["optimizer"] == "AdamW"
    assert train_kwargs["lr0"] == 2e-4
    assert train_kwargs["lrf"] == 0.05
    assert train_kwargs["weight_decay"] == 5e-4
    assert train_kwargs["patience"] == 10
    assert train_kwargs["warmup_epochs"] == 3.0
    assert train_kwargs["val"] is True
    assert train_kwargs["rect"] is False
    assert train_kwargs["mosaic"] == 0.1
    assert train_kwargs["mixup"] == 0.0
    assert train_kwargs["copy_paste"] == 0.0
    assert train_kwargs["translate"] == 0.02
    assert train_kwargs["scale"] == 0.15
    assert train_kwargs["hsv_h"] == 0.01
    assert train_kwargs["hsv_s"] == 0.4
    assert train_kwargs["hsv_v"] == 0.25
    assert train_kwargs["close_mosaic"] == 10
    assert train_kwargs["plots"] is False
    assert train_kwargs["data"] == str(dataset_yaml)
    assert val_kwargs["split"] == "val"
    assert report["validation"]["metrics/mAP50(B)"] == 0.25


def test_scoring_v2_trains_or_reuses_physical_part_yolo_weights(monkeypatch, tmp_path: Path) -> None:
    from training.scoring import pipeline as pipeline_module
    from training.scoring.config import ScoringTrainingConfig

    dataset_yaml = tmp_path / "physical-parts.yaml"
    dataset_yaml.write_text(
        "path: .\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n  - wind_blade\n",
        encoding="utf-8",
    )

    calls: dict[str, object] = {}

    class _FakeYOLO:
        def __init__(self, model_name: str) -> None:
            calls["model_name"] = model_name

        def train(self, **kwargs):
            calls["train"] = kwargs
            save_dir = tmp_path / "physical-save"
            (save_dir / "weights").mkdir(parents=True, exist_ok=True)
            (save_dir / "weights" / "best.pt").write_bytes(b"fake-part-weights")
            return type("TrainResult", (), {"save_dir": str(save_dir)})()

        def val(self, **kwargs):
            calls["val"] = kwargs
            return type("Metrics", (), {"results_dict": {"metrics/mAP50(B)": 0.31}})()

    monkeypatch.setattr(pipeline_module, "YOLO", _FakeYOLO)

    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    report = pipeline_module._train_physical_part_yolo_auxiliary(
        training_root=tmp_path / "training",
        bundle_dir=bundle_dir,
        config=ScoringTrainingConfig(physical_part_yolo_dataset_yaml=str(dataset_yaml)),
        device=torch.device("mps"),
    )

    assert (bundle_dir / "yolo_physical_parts.pt").exists()
    assert report["status"] == "trained"
    assert report["dataset"] == str(dataset_yaml)
    assert report["weights"] == str(bundle_dir / "yolo_physical_parts.pt")
    assert report["validation"]["metrics/mAP50(B)"] == 0.31
    assert report["dataset_variant"] == "blade_focus_v1"
    assert report["dataset"] == str(dataset_yaml)


def test_scoring_v2_reuses_existing_yolo_aux_without_retraining(tmp_path: Path) -> None:
    from training.scoring import pipeline as pipeline_module
    from training.scoring.config import ScoringTrainingConfig

    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    existing_weight = bundle_dir / "yolo_aux.pt"
    existing_weight.write_bytes(b"existing-weight")

    report = pipeline_module._train_yolo_auxiliary(
        training_root=tmp_path / "training",
        bundle_dir=bundle_dir,
        manifest_summary={"yolo_datasets": []},
        config=ScoringTrainingConfig(),
        device=torch.device("cpu"),
        active_classes=[
            "substation_primary",
            "transmission_tower",
            "insulator_string",
            "wind_turbine",
            "solar_panel",
            "dam",
        ],
    )

    assert report["status"] == "reused"
    assert report["reason"] == "reuse-existing-yolo-aux"
    assert report["weights"] == str(existing_weight)
