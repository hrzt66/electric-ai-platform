from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.core.settings import Settings


@dataclass(slots=True)
class GenerationTrainingConfig:
    base_model_name: str = "runwayml/stable-diffusion-v1-5"
    output_model_name: str = "sd15-electric-specialized"
    diffusers_example_ref: str = "v0.35.1"
    resolution: int = 512
    rank: int = 32
    alpha: int = 32
    train_batch_size: int = 1
    gradient_accumulation_steps: int = 8
    learning_rate: float = 5e-5
    lr_scheduler: str = "cosine"
    lr_warmup_steps: int = 200
    report_to: str = "all"
    num_train_epochs: int = 100
    max_train_steps: int | None = None
    checkpointing_steps: int = 500
    enable_training_validation: bool = False
    validation_epochs: int = 1
    num_validation_images: int = 2
    mixed_precision: str = "no"
    use_8bit_adam: bool = False
    allow_tf32: bool = False
    gradient_checkpointing: bool = True
    random_flip: bool = True
    center_crop: bool = True
    dataloader_num_workers: int = 0
    seed: int = 42
    max_train_samples: int | None = None
    num_inference_steps: int = 28
    guidance_scale: float = 7.0
    validation_prompts: list[str] = field(
        default_factory=lambda: [
            "ultra realistic electric power substation, steel gantries, insulators, transformers, daytime industrial photography",
            "high fidelity transmission line inspection photo, transmission tower, insulator string, conductors, realistic outdoor lighting",
            "aerial inspection view of wind turbine farm in electric utility context, sharp details, natural landscape",
            "power equipment yard with breaker, transformer, busbar, realistic industrial documentation photo",
        ]
    )

    def resolve_generation_model_root(self, settings: Settings) -> Path:
        legacy_root = settings.runtime_root / "generation"
        if legacy_root.exists():
            return legacy_root
        return settings.generation_model_dir

    def resolve_base_model_source(self, settings: Settings) -> str:
        candidate = self.resolve_generation_model_root(settings) / "sd15-electric"
        if candidate.exists() and any(candidate.iterdir()):
            return str(candidate)
        return self.base_model_name

    def resolve_output_model_dir(self, settings: Settings) -> Path:
        return self.resolve_generation_model_root(settings) / self.output_model_name
