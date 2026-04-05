from pathlib import Path
from types import SimpleNamespace

from PIL import Image


class FakeDiffusionPipeline:
    def __call__(
        self,
        prompt: str,
        negative_prompt: str,
        num_inference_steps: int,
        guidance_scale: float,
        width: int,
        height: int,
        num_images_per_prompt: int,
        generator,
    ):
        images = [Image.new("RGB", (width, height), color=(12, 45, 78)) for _ in range(num_images_per_prompt)]
        return SimpleNamespace(images=images)


def test_sd15_runtime_returns_saved_images(tmp_path):
    from app.runtimes.sd15_runtime import SD15Runtime

    runtime = SD15Runtime(
        model_dir=tmp_path / "sd15-electric",
        output_dir=tmp_path / "outputs",
        pipeline=FakeDiffusionPipeline(),
    )

    result = runtime.generate(
        job_id=7,
        prompt="500kV substation at sunset",
        negative_prompt="blurry",
        seed=11,
        width=512,
        height=512,
        steps=20,
        guidance_scale=7.5,
        num_images=1,
        model_name="sd15-electric",
    )

    assert len(result) == 1
    assert Path(result[0]["file_path"]).exists()
    assert result[0]["seed"] == 11
