from __future__ import annotations

from pathlib import Path

import torch
from diffusers import StableDiffusionPipeline


def merge_lora_weights(
    *,
    base_model_name_or_path: str,
    lora_output_dir: Path,
    merged_model_dir: Path,
) -> Path:
    dtype = torch.float16
    pipeline = StableDiffusionPipeline.from_pretrained(
        base_model_name_or_path,
        torch_dtype=dtype,
        safety_checker=None,
        feature_extractor=None,
    )
    pipeline.load_lora_weights(str(lora_output_dir))
    pipeline.fuse_lora()
    pipeline.unload_lora_weights()

    merged_model_dir.mkdir(parents=True, exist_ok=True)
    pipeline.save_pretrained(merged_model_dir, safe_serialization=True)
    return merged_model_dir
