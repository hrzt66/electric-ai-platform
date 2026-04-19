from __future__ import annotations

from dataclasses import dataclass, field

from training.scoring.modeling import DEFAULT_TARGET_COLUMNS, DEFAULT_TOTAL_WEIGHTS


@dataclass(slots=True)
class ScoringTrainingConfig:
    bundle_name: str = "electric-score-v2"
    runtime_type: str = "student"
    dataset_name: str = "scoring-v2"
    device_preference: str = "mps"
    image_size: int = 224
    train_batch_size: int = 4
    eval_batch_size: int = 8
    num_workers: int = 0
    epochs: int = 100
    learning_rate: float = 3e-4
    weight_decay: float = 1e-4
    use_pretrained_image_backbone: bool = True
    image_backbone_trainable_stages: int = 2
    score_calibration: dict[str, dict[str, float]] = field(
        default_factory=lambda: {
            "visual_fidelity": {"target": 64.0, "gain": 0.50},
            "text_consistency": {"target": 58.0, "gain": 0.65},
            "physical_plausibility": {"target": 54.0, "gain": 0.60},
            "composition_aesthetics": {"target": 76.0, "gain": 0.40},
        }
    )
    max_train_samples: int | None = 1536
    max_val_samples: int | None = 256
    max_test_samples: int | None = 256
    seed: int = 42
    yolo_model_name: str = "yolov8n.pt"
    yolo_image_size: int = 384
    yolo_epochs: int = 5
    yolo_batch_size: int = 12
    yolo_confidence: float = 0.15
    yolo_iou: float = 0.45
    yolo_validate_each_epoch: bool = False
    yolo_run_final_validation: bool = True
    yolo_min_train_instances: int = 50
    yolo_min_val_instances: int = 10
    targets: list[str] = field(default_factory=lambda: list(DEFAULT_TARGET_COLUMNS))
    total_weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_TOTAL_WEIGHTS))
    power_classes: list[str] = field(
        default_factory=lambda: [
            "capacitor",
            "bus",
            "pipe",
            "filter",
            "gis",
            "bushing",
            "switch",
            "line",
            "pt",
            "breaker",
            "arrester",
            "insulator",
            "ct",
            "tower",
            "frame",
        ]
    )
    dataset_sources: list[dict[str, str | bool]] = field(
        default_factory=lambda: [
            {
                "name": "substation-object-detection",
                "url": "https://huggingface.co/datasets/sxiong/Power-equipment-image-dataset/resolve/main/substation%20object%20detection.zip?download=1",
                "archive_name": "substation-object-detection.zip",
                "kind": "detection",
                "enabled": True,
            },
            {
                "name": "transmission-line-classification",
                "url": "https://huggingface.co/datasets/sxiong/Power-equipment-image-dataset/resolve/main/transmission%20line%20classification.zip?download=1",
                "archive_name": "transmission-line-classification.zip",
                "kind": "classification",
                "enabled": True,
            },
            {
                "name": "transmission-line-object-detection",
                "url": "https://huggingface.co/datasets/sxiong/Power-equipment-image-dataset/resolve/main/transmission%20line%20object%20detection.zip?download=1",
                "archive_name": "transmission-line-object-detection.zip",
                "kind": "detection",
                "enabled": True,
            },
            {
                "name": "powerline-components-and-faults",
                "dataset_id": "docmhvr/powerline-components-and-faults",
                "kind": "hf_detection_bboxes_labels",
                "enabled": True,
                "label_map": {
                    "Broken Cable": "line",
                    "Broken Insulator": "insulator",
                    "Cable": "line",
                    "Insulators": "insulator",
                    "Tower": "tower",
                },
            },
        ]
    )

    def bundle_payload(self) -> dict[str, object]:
        return {
            "runtime_type": self.runtime_type,
            "targets": self.targets,
            "classes": self.power_classes,
            "total_weights": self.total_weights,
            "image_size": self.image_size,
            "epochs": self.epochs,
            "device_preference": self.device_preference,
            "score_calibration": self.score_calibration,
            "yolo_imgsz": self.yolo_image_size,
            "yolo_conf": self.yolo_confidence,
            "yolo_iou": self.yolo_iou,
        }
