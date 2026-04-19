from pathlib import Path
from types import SimpleNamespace
import sys

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


def test_sd15_runtime_builds_mps_pipeline_with_float32_when_available(tmp_path, monkeypatch):
    from app.runtimes.sd15_runtime import SD15Runtime

    moved_to: list[str] = []
    dtype_args: list[str] = []

    class FakeLoadedPipeline:
        def enable_attention_slicing(self):
            return None

        def enable_vae_slicing(self):
            return None

        def to(self, device: str):
            moved_to.append(device)
            return self

    class FakePipelineClass:
        @staticmethod
        def from_pretrained(*args, **kwargs):
            dtype_args.append(kwargs["torch_dtype"])
            return FakeLoadedPipeline()

    class FakeTorch:
        float16 = "float16"
        float32 = "float32"

        class cuda:
            @staticmethod
            def is_available() -> bool:
                return False

    monkeypatch.setattr("app.runtimes.sd15_runtime.preferred_torch_device_type", lambda: "mps", raising=False)
    monkeypatch.setitem(sys.modules, "torch", FakeTorch)
    monkeypatch.setitem(sys.modules, "diffusers", type("FakeDiffusers", (), {"StableDiffusionPipeline": FakePipelineClass}))

    runtime = SD15Runtime(model_dir=tmp_path / "sd15-electric", output_dir=tmp_path / "outputs")
    runtime._build_default_pipeline()

    assert dtype_args == ["float32"]
    assert moved_to == ["mps"]


def test_sd15_runtime_builds_mps_generator(tmp_path, monkeypatch):
    from app.runtimes.sd15_runtime import SD15Runtime

    devices: list[str] = []

    class FakeGenerator:
        def manual_seed(self, seed: int):
            return self

    class FakeTorch:
        @staticmethod
        def Generator(device: str):
            devices.append(device)
            return FakeGenerator()

    monkeypatch.setattr("app.runtimes.sd15_runtime.preferred_torch_device_type", lambda: "mps", raising=False)
    monkeypatch.setitem(sys.modules, "torch", FakeTorch)

    runtime = SD15Runtime(model_dir=tmp_path / "sd15-electric", output_dir=tmp_path / "outputs")
    runtime._build_generator(123)

    assert devices == ["mps"]
