import json
from pathlib import Path

from PIL import Image
import torch

from training.common.jsonl import write_jsonl


def _write_fake_manifest(manifest_root: Path) -> dict[str, str]:
    return _write_fake_manifest_with_yolo_dim(manifest_root, yolo_dim=34)


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
    assert config.yolo_model_name == "yolov8n.pt"
    assert config.yolo_image_size == 384
    assert config.yolo_batch_size == 12
    assert config.yolo_validate_each_epoch is False
    assert config.yolo_run_final_validation is True
    assert config.yolo_min_train_instances == 50
    assert config.yolo_min_val_instances == 10
    assert config.total_weights["text_consistency"] == 0.37
    assert config.score_calibration["visual_fidelity"] == {"target": 64.0, "gain": 0.5}
    assert config.score_calibration["composition_aesthetics"] == {"target": 76.0, "gain": 0.4}
    assert config.use_pretrained_image_backbone is True
    assert config.image_backbone_trainable_stages == 2
    assert config.max_train_samples == 1536
    assert config.max_val_samples == 256
    assert config.max_test_samples == 256
    assert any(source["name"] == "powerline-components-and-faults" for source in config.dataset_sources)
    transmission_detection = next(source for source in config.dataset_sources if source["name"] == "transmission-line-object-detection")
    assert transmission_detection["enabled"] is True
    assert "score_bands" not in config.bundle_payload()


def test_scoring_v2_only_unfreezes_the_tail_backbone_stages() -> None:
    from training.scoring.modeling import FourDimScoreModel, configure_image_backbone_trainability

    model = FourDimScoreModel(vocab_size=4, yolo_feature_dim=34, target_dim=4, pretrained_backbone=False)
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
        ),
    )

    bundle_dir = tmp_path / "scoring" / "electric-score-v2"
    bundle_config = json.loads((bundle_dir / "bundle_config.json").read_text(encoding="utf-8"))
    metrics = json.loads((bundle_dir / "metrics.json").read_text(encoding="utf-8"))

    assert report["scoring_model_root"] == str(bundle_dir)
    assert report["epochs"] == 1
    assert report["active_classes"] == ["tower", "insulator"]
    assert bundle_config["runtime_type"] == "student"
    assert bundle_config["epochs"] == 1
    assert bundle_config["classes"] == ["tower", "insulator"]
    assert bundle_config["yolo_feature_dim"] == 8
    assert (bundle_dir / "student_best.pt").exists()
    assert (bundle_dir / "vocab.json").exists()
    assert metrics["test_metrics"]["mae"] >= 0.0


def test_scoring_v2_yolo_training_prefers_local_friendly_train_and_final_val(monkeypatch, tmp_path: Path) -> None:
    from training.scoring import pipeline as pipeline_module
    from training.scoring.config import ScoringTrainingConfig

    dataset_yaml = tmp_path / "tiny-dataset.yaml"
    dataset_yaml.write_text("path: .\ntrain: images/train\nval: images/val\ntest: images/test\n", encoding="utf-8")

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
        config=ScoringTrainingConfig(),
        device=torch.device("mps"),
    )

    train_kwargs = recorded["train"]
    val_kwargs = recorded["val"]

    assert train_kwargs["imgsz"] == 384
    assert train_kwargs["batch"] == 12
    assert train_kwargs["val"] is False
    assert train_kwargs["rect"] is True
    assert train_kwargs["plots"] is False
    assert val_kwargs["split"] == "val"
    assert report["validation"]["metrics/mAP50(B)"] == 0.25
    assert (bundle_dir / "yolo_aux.pt").exists()
