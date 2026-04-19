from __future__ import annotations

"""SSD-1B 生成运行时，负责模型加载、推理出图和资源释放。"""

from dataclasses import asdict
from pathlib import Path
import gc

from app.core.torch_cuda import best_effort_cleanup_torch, preferred_torch_device_type
from app.runtimes.base import GeneratedImageRecord


class SSD1BRuntime:
    """封装 SSD-1B 在当前平台中的执行方式。"""

    def __init__(self, model_dir: Path, output_dir: Path, pipeline=None) -> None:
        self.model_dir = Path(model_dir)
        self.output_dir = Path(output_dir)
        self._pipeline = pipeline

    def prepare(self, job=None) -> None:
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _build_default_pipeline(self):
        from diffusers import StableDiffusionXLPipeline
        import torch

        device_type = preferred_torch_device_type()
        dtype = torch.float16 if device_type == "cuda" else torch.float32
        variant = "fp16" if device_type in {"cuda", "mps"} else None
        pipe = StableDiffusionXLPipeline.from_pretrained(
            self.model_dir,
            torch_dtype=dtype,
            variant=variant,
            local_files_only=True,
        )
        pipe.enable_attention_slicing()
        pipe.enable_vae_slicing()
        if device_type == "cuda" and hasattr(pipe, "enable_model_cpu_offload"):
            pipe.enable_model_cpu_offload()
        else:
            pipe = pipe.to(device_type)
        return pipe

    def _resolve_pipeline(self):
        if self._pipeline is None:
            self._pipeline = self._build_default_pipeline()
        return self._pipeline

    def generate(
        self,
        *,
        job_id: int,
        prompt: str,
        negative_prompt: str,
        seed: int,
        width: int,
        height: int,
        steps: int,
        guidance_scale: float,
        num_images: int,
        model_name: str,
    ) -> list[dict]:
        self.prepare()
        pipeline = self._resolve_pipeline()
        generator = self._build_generator(seed)
        result = pipeline(
            prompt=prompt,
            negative_prompt=negative_prompt,
            num_inference_steps=steps,
            guidance_scale=guidance_scale,
            width=width,
            height=height,
            num_images_per_prompt=num_images,
            generator=generator,
        )

        saved: list[dict] = []
        for index, image in enumerate(result.images):
            image_path = self.output_dir / f"{job_id}_{index}_{seed}.png"
            image.save(image_path)
            saved.append(
                asdict(
                    GeneratedImageRecord(
                        file_path=str(image_path),
                        seed=seed,
                        width=width,
                        height=height,
                        model_name=model_name,
                    )
                )
            )
        return saved

    def _build_generator(self, seed: int):
        try:
            import torch
        except ImportError:
            return None

        generator = torch.Generator(device=preferred_torch_device_type())
        generator.manual_seed(seed)
        return generator

    def unload(self) -> None:
        if self._pipeline is not None:
            del self._pipeline
            self._pipeline = None
        gc.collect()
        best_effort_cleanup_torch(label="ssd1b-unload")
