from __future__ import annotations

import json
from pathlib import Path

import torch
from diffusers import StableDiffusionPipeline

from training.generation.config import GenerationTrainingConfig


def evaluate_generation_model(
    *,
    model_dir: Path,
    output_dir: Path,
    config: GenerationTrainingConfig,
) -> dict[str, object]:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32

    pipeline = StableDiffusionPipeline.from_pretrained(
        model_dir,
        torch_dtype=dtype,
        safety_checker=None,
        feature_extractor=None,
    )
    pipeline = pipeline.to(device)
    if device == "cuda":
        pipeline.enable_attention_slicing()

    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, str]] = []
    for index, prompt in enumerate(config.validation_prompts):
        generator = torch.Generator(device=device).manual_seed(config.seed + index)
        image = pipeline(
            prompt,
            num_inference_steps=config.num_inference_steps,
            guidance_scale=config.guidance_scale,
            generator=generator,
        ).images[0]
        image_path = output_dir / f"validation_{index:02d}.png"
        image.save(image_path)
        results.append({"prompt": prompt, "image_path": str(image_path)})

    report_path = output_dir / "evaluation_report.json"
    report_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"report_path": str(report_path), "images": results}
