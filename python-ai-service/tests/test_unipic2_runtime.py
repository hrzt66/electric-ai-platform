from pathlib import Path
from types import SimpleNamespace

from PIL import Image


class FakeUniPic2Pipeline:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def __call__(
        self,
        prompt: str,
        negative_prompt: str,
        height: int,
        width: int,
        num_inference_steps: int,
        guidance_scale: float,
        num_images_per_prompt: int,
        generator,
    ):
        self.calls.append(
            {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "height": height,
                "width": width,
                "num_inference_steps": num_inference_steps,
                "guidance_scale": guidance_scale,
                "num_images_per_prompt": num_images_per_prompt,
                "generator": generator,
            }
        )
        images = [Image.new("RGB", (width, height), color=(80, 120, 160)) for _ in range(num_images_per_prompt)]
        return SimpleNamespace(images=images)


class FakeAccelerationPipeline:
    def __init__(self) -> None:
        self.strategy: str | None = None
        self.device: str | None = None

    def enable_sequential_cpu_offload(self) -> None:
        self.strategy = "sequential"

    def enable_model_cpu_offload(self) -> None:
        self.strategy = "model"

    def to(self, device: str):
        self.device = device
        return self


def test_unipic2_runtime_returns_saved_images(tmp_path):
    from app.runtimes.unipic2_runtime import UniPic2Runtime

    fake_pipeline = FakeUniPic2Pipeline()
    runtime = UniPic2Runtime(
        model_dir=tmp_path / "unipic2-kontext",
        output_dir=tmp_path / "outputs",
        pipeline=fake_pipeline,
    )

    result = runtime.generate(
        job_id=9,
        prompt="An ultra-detailed power dispatch center, cinematic industrial lighting",
        negative_prompt="blurry",
        seed=23,
        width=640,
        height=384,
        steps=30,
        guidance_scale=4.0,
        num_images=1,
        model_name="unipic2-kontext",
    )

    assert len(result) == 1
    assert Path(result[0]["file_path"]).exists()
    assert result[0]["seed"] == 23
    assert fake_pipeline.calls[0]["prompt"].startswith("An ultra-detailed")
    assert fake_pipeline.calls[0]["num_inference_steps"] == 30


def test_vendored_unipic2_modules_import_with_current_diffusers():
    import unipicv2.pipeline_stable_diffusion_3_kontext as pipeline_module
    import unipicv2.transformer_sd3_kontext as transformer_module

    assert pipeline_module.StableDiffusion3KontextPipeline is not None
    assert transformer_module.SD3Transformer2DKontextModel is not None


def test_unipic2_transformer_can_be_constructed():
    from unipicv2.transformer_sd3_kontext import SD3Transformer2DKontextModel

    model = SD3Transformer2DKontextModel()

    assert len(model.transformer_blocks) > 0


def test_unipic2_runtime_prefers_model_offload_for_cuda(tmp_path):
    from app.runtimes.unipic2_runtime import UniPic2Runtime

    runtime = UniPic2Runtime(
        model_dir=tmp_path / "unipic2-kontext",
        output_dir=tmp_path / "outputs",
        offload_mode="model",
    )
    pipeline = FakeAccelerationPipeline()

    runtime._apply_execution_strategy(pipeline, cuda_available=True)

    assert pipeline.strategy == "model"
    assert pipeline.device is None


def test_unipic2_runtime_can_disable_offload_for_cuda(tmp_path):
    from app.runtimes.unipic2_runtime import UniPic2Runtime

    runtime = UniPic2Runtime(
        model_dir=tmp_path / "unipic2-kontext",
        output_dir=tmp_path / "outputs",
        offload_mode="none",
    )
    pipeline = FakeAccelerationPipeline()

    runtime._apply_execution_strategy(pipeline, cuda_available=True)

    assert pipeline.strategy is None
    assert pipeline.device == "cuda"


def test_unipic2_runtime_logs_selected_execution_strategy(tmp_path, caplog):
    from app.runtimes.unipic2_runtime import UniPic2Runtime

    caplog.set_level("INFO", logger="electric_ai.runtime")

    runtime = UniPic2Runtime(
        model_dir=tmp_path / "unipic2-kontext",
        output_dir=tmp_path / "outputs",
        offload_mode="model",
    )
    pipeline = FakeAccelerationPipeline()

    runtime._apply_execution_strategy(pipeline, cuda_available=True)

    messages = "\n".join(record.getMessage() for record in caplog.records)
    assert "applying unipic2 execution strategy cuda=True offload_mode=model" in messages
    assert "enabled unipic2 strategy=model" in messages
