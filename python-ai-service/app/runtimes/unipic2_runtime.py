from __future__ import annotations

from dataclasses import asdict
import gc
import logging
from pathlib import Path

from app.core.runtime_logging import configure_runtime_logging
from app.runtimes.base import GeneratedImageRecord

configure_runtime_logging()
logger = logging.getLogger("electric_ai.runtime.unipic2")


class UniPic2Runtime:
    def __init__(self, model_dir: Path, output_dir: Path, pipeline=None, offload_mode: str = "model") -> None:
        self.model_dir = Path(model_dir)
        self.output_dir = Path(output_dir)
        self._pipeline = pipeline
        self.offload_mode = offload_mode.strip().lower()

    def prepare(self, job=None) -> None:
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            "prepared unipic2 runtime model_dir=%s output_dir=%s offload_mode=%s",
            self.model_dir,
            self.output_dir,
            self.offload_mode,
        )

    def _build_default_pipeline(self):
        import torch
        from diffusers import AutoencoderKL, FlowMatchEulerDiscreteScheduler
        from transformers import (
            CLIPTextModelWithProjection,
            CLIPTokenizer,
            T5EncoderModel,
            T5TokenizerFast,
        )

        from unipicv2.pipeline_stable_diffusion_3_kontext import StableDiffusion3KontextPipeline
        from unipicv2.transformer_sd3_kontext import SD3Transformer2DKontextModel

        dtype = torch.float16 if torch.cuda.is_available() else torch.float32

        transformer = SD3Transformer2DKontextModel.from_pretrained(
            self.model_dir,
            subfolder="transformer",
            torch_dtype=dtype,
            local_files_only=True,
        )
        vae = AutoencoderKL.from_pretrained(
            self.model_dir,
            subfolder="vae",
            torch_dtype=dtype,
            local_files_only=True,
        )
        text_encoder = CLIPTextModelWithProjection.from_pretrained(
            self.model_dir,
            subfolder="text_encoder",
            torch_dtype=dtype,
            local_files_only=True,
        )
        tokenizer = CLIPTokenizer.from_pretrained(
            self.model_dir,
            subfolder="tokenizer",
            local_files_only=True,
        )
        text_encoder_2 = CLIPTextModelWithProjection.from_pretrained(
            self.model_dir,
            subfolder="text_encoder_2",
            torch_dtype=dtype,
            local_files_only=True,
        )
        tokenizer_2 = CLIPTokenizer.from_pretrained(
            self.model_dir,
            subfolder="tokenizer_2",
            local_files_only=True,
        )
        text_encoder_3 = T5EncoderModel.from_pretrained(
            self.model_dir,
            subfolder="text_encoder_3",
            torch_dtype=dtype,
            local_files_only=True,
        )
        tokenizer_3 = T5TokenizerFast.from_pretrained(
            self.model_dir,
            subfolder="tokenizer_3",
            local_files_only=True,
        )
        scheduler = FlowMatchEulerDiscreteScheduler.from_pretrained(
            self.model_dir,
            subfolder="scheduler",
            local_files_only=True,
        )

        pipe = StableDiffusion3KontextPipeline(
            transformer=transformer,
            vae=vae,
            text_encoder=text_encoder,
            tokenizer=tokenizer,
            text_encoder_2=text_encoder_2,
            tokenizer_2=tokenizer_2,
            text_encoder_3=text_encoder_3,
            tokenizer_3=tokenizer_3,
            scheduler=scheduler,
        )
        if hasattr(pipe, "set_progress_bar_config"):
            pipe.set_progress_bar_config(disable=True)
        if hasattr(pipe, "enable_attention_slicing"):
            pipe.enable_attention_slicing("auto")
        if hasattr(pipe.vae, "enable_slicing"):
            pipe.vae.enable_slicing()
        if hasattr(pipe.transformer, "enable_forward_chunking"):
            pipe.transformer.enable_forward_chunking(chunk_size=1, dim=1)

        return self._apply_execution_strategy(pipe, cuda_available=bool(torch.cuda.is_available()))

    def _apply_execution_strategy(self, pipe, *, cuda_available: bool):
        logger.info(
            "applying unipic2 execution strategy cuda=%s offload_mode=%s",
            cuda_available,
            self.offload_mode,
        )
        if not cuda_available:
            logger.info("enabled unipic2 strategy=cpu")
            return pipe.to("cpu")

        if self.offload_mode == "none":
            logger.info("enabled unipic2 strategy=cuda")
            return pipe.to("cuda")

        strategy_order = {
            "model": ("enable_model_cpu_offload", "enable_sequential_cpu_offload"),
            "sequential": ("enable_sequential_cpu_offload", "enable_model_cpu_offload"),
        }.get(self.offload_mode, ("enable_model_cpu_offload", "enable_sequential_cpu_offload"))

        for method_name in strategy_order:
            if hasattr(pipe, method_name):
                getattr(pipe, method_name)()
                strategy_name = "model" if method_name == "enable_model_cpu_offload" else "sequential"
                logger.info("enabled unipic2 strategy=%s", strategy_name)
                return pipe
        logger.warning("unipic2 runtime did not expose cpu offload hooks, falling back to cuda")
        return pipe.to("cuda")

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
        logger.info(
            "job %s unipic2 generation started images=%s size=%sx%s steps=%s guidance_scale=%s",
            job_id,
            num_images,
            width,
            height,
            steps,
            guidance_scale,
        )
        result = pipeline(
            prompt=prompt,
            negative_prompt=negative_prompt,
            height=height,
            width=width,
            num_inference_steps=steps,
            guidance_scale=guidance_scale,
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
        logger.info("job %s unipic2 generation completed count=%s", job_id, len(saved))
        return saved

    def _build_generator(self, seed: int):
        try:
            import torch
        except ImportError:
            return None

        generator = torch.Generator(device="cuda" if torch.cuda.is_available() else "cpu")
        generator.manual_seed(seed)
        return generator

    def unload(self) -> None:
        if self._pipeline is not None:
            logger.info("unloading unipic2 runtime pipeline")
            del self._pipeline
            self._pipeline = None
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            return
