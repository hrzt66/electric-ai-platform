from __future__ import annotations

"""SD1.5 生成运行时，负责模型加载、推理出图和资源释放。"""

from dataclasses import asdict
from pathlib import Path
import gc

from app.core.torch_cuda import best_effort_cleanup_torch, preferred_torch_device_type
from app.runtimes.base import GeneratedImageRecord


class SD15Runtime:
    """封装 Stable Diffusion 1.5 在当前平台中的执行方式。"""

    def __init__(self, model_dir: Path, output_dir: Path, pipeline=None) -> None:
        """记录模型目录、输出目录以及可选的外部注入 pipeline。"""
        self.model_dir = Path(model_dir)
        self.output_dir = Path(output_dir)
        self._pipeline = pipeline

    def prepare(self, job=None) -> None:
        """确保模型目录和输出目录存在，供后续推理与图片保存使用。"""
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _build_default_pipeline(self):
        """按当前机器环境构建默认 SD1.5 pipeline，并启用基础显存优化。"""
        from diffusers import StableDiffusionPipeline
        import torch

        device_type = preferred_torch_device_type()
        dtype = torch.float16 if device_type == "cuda" else torch.float32
        pipe = StableDiffusionPipeline.from_pretrained(
            self.model_dir,
            torch_dtype=dtype,
            safety_checker=None,
            local_files_only=True,
        )
        pipe.enable_attention_slicing()
        pipe.enable_vae_slicing()
        if device_type == "cuda":
            if hasattr(pipe, "enable_model_cpu_offload"):
                pipe.enable_model_cpu_offload()
            else:
                pipe = pipe.to("cuda")
        elif device_type == "mps":
            pipe = pipe.to("mps")
        else:
            pipe = pipe.to("cpu")
        return pipe

    def _resolve_pipeline(self):
        """懒加载 pipeline，避免服务启动时就立刻占满显存。"""
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
        """执行一次真实生成任务，并把结果图片落盘后返回资产记录。"""
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
        """根据随机种子构建 torch generator，保证同种子结果可复现。"""
        try:
            import torch
        except ImportError:
            return None

        generator = torch.Generator(device=preferred_torch_device_type())
        generator.manual_seed(seed)
        return generator

    def unload(self) -> None:
        """释放 pipeline 与 CUDA 缓存，供后续模型切换重新分配显存。"""
        if self._pipeline is not None:
            del self._pipeline
            self._pipeline = None
        gc.collect()
        best_effort_cleanup_torch(label="sd15-unload")
