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
    max_train_samples: int | None = 1536
    max_val_samples: int | None = 256
    max_test_samples: int | None = 256
    seed: int = 42
    yolo_model_name: str = "yolo11s.pt"
    yolo_image_size: int = 640
    yolo_epochs: int = 40
    yolo_batch_size: int = 6
    yolo_profile: str = "yolo11s_640_best_import_v1"
    yolo_train_variant: str = "imported_remap_v1"
    physical_part_yolo_profile: str = "electric_physical_parts_blade_focus_v1"
    physical_part_yolo_train_variant: str = "blade_focus_v1"
    yolo_optimizer: str = "AdamW"
    yolo_learning_rate: float = 2e-4
    yolo_lrf: float = 0.05
    yolo_weight_decay: float = 5e-4
    yolo_warmup_epochs: float = 3.0
    yolo_patience: int = 10
    yolo_confidence: float = 0.15
    yolo_iou: float = 0.45
    yolo_validate_each_epoch: bool = True
    yolo_run_final_validation: bool = True
    reuse_existing_yolo_aux: bool = True
    reuse_existing_physical_part_yolo_aux: bool = True
    yolo_rect: bool = False
    yolo_mosaic: float = 0.1
    yolo_close_mosaic: int = 10
    yolo_mixup: float = 0.0
    yolo_copy_paste: float = 0.0
    yolo_translate: float = 0.02
    yolo_scale: float = 0.15
    yolo_hsv_h: float = 0.01
    yolo_hsv_s: float = 0.4
    yolo_hsv_v: float = 0.25
    yolo_dataset_yaml: str | None = "datasets/yolo-image2-remapped-scoring-6class-v1/dataset.yaml"
    physical_part_yolo_dataset_yaml: str | None = "datasets/yolo-physical-parts-v1/dataset.yaml"
    yolo_min_train_instances: int = 50
    yolo_min_val_instances: int = 10
    targets: list[str] = field(default_factory=lambda: list(DEFAULT_TARGET_COLUMNS))
    total_weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_TOTAL_WEIGHTS))
    power_classes: list[str] = field(
        default_factory=lambda: [
            "substation_primary",
            "transmission_tower",
            "insulator_string",
            "wind_turbine",
            "solar_panel",
            "dam",
        ]
    )
    dataset_sources: list[dict[str, object]] = field(
        default_factory=lambda: [
            {
                "name": "substation-object-detection-yolo",
                "kind": "local_detection",
                "dataset_root": "raw/extracted/substation-object-detection/substation-object-detection-yolo",
                "enabled": True,
            },
            {
                "name": "powerline-components-and-faults",
                "kind": "local_detection",
                "dataset_root": "raw/hf/powerline-components-and-faults",
                "enabled": True,
            },
            {
                "name": "dior-superclasses",
                "kind": "local_detection",
                "dataset_root": "raw/hf/dior-superclasses",
                "enabled": True,
            },
            {
                "name": "wind-turbine-aerial",
                "kind": "local_detection",
                "dataset_root": "raw/local/wind-turbine-aerial",
                "enabled": True,
            },
            {
                "name": "solar-plants-brazil-yolo",
                "kind": "local_detection",
                "dataset_root": "raw/local/solar-plants-brazil-yolo",
                "enabled": True,
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
            "yolo_imgsz": self.yolo_image_size,
            "yolo_conf": self.yolo_confidence,
            "yolo_iou": self.yolo_iou,
            "yolo_profile": self.yolo_profile,
            "yolo_train_variant": self.yolo_train_variant,
            "physical_part_yolo_profile": self.physical_part_yolo_profile,
            "physical_part_yolo_train_variant": self.physical_part_yolo_train_variant,
            "physical_part_yolo_dataset_yaml": self.physical_part_yolo_dataset_yaml,
        }
