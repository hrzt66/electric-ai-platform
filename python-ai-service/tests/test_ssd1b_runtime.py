from pathlib import Path
from types import SimpleNamespace
import sys

from PIL import Image


class FakeXLRuntimePipeline:
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
        images = [Image.new("RGB", (width, height), color=(22, 66, 99)) for _ in range(num_images_per_prompt)]
        return SimpleNamespace(images=images)


def test_ssd1b_runtime_returns_saved_images(tmp_path):
    from app.runtimes.ssd1b_runtime import SSD1BRuntime

    runtime = SSD1BRuntime(
        model_dir=tmp_path / "ssd1b-electric",
        output_dir=tmp_path / "outputs",
        pipeline=FakeXLRuntimePipeline(),
    )

    result = runtime.generate(
        job_id=9,
        prompt="wind turbines on grassland",
        negative_prompt="blurry",
        seed=17,
        width=512,
        height=512,
        steps=12,
        guidance_scale=7.0,
        num_images=1,
        model_name="ssd1b-electric",
    )

    assert len(result) == 1
    assert Path(result[0]["file_path"]).exists()
    assert result[0]["model_name"] == "ssd1b-electric"


def test_ssd1b_runtime_builds_mps_pipeline_with_float32_when_available(tmp_path, monkeypatch):
    from app.runtimes.ssd1b_runtime import SSD1BRuntime

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

    monkeypatch.setattr("app.runtimes.ssd1b_runtime.preferred_torch_device_type", lambda: "mps", raising=False)
    monkeypatch.setitem(sys.modules, "torch", FakeTorch)
    monkeypatch.setitem(sys.modules, "diffusers", type("FakeDiffusers", (), {"StableDiffusionXLPipeline": FakePipelineClass}))

    runtime = SSD1BRuntime(model_dir=tmp_path / "ssd1b-electric", output_dir=tmp_path / "outputs")
    runtime._build_default_pipeline()

    assert dtype_args == ["float32"]
    assert moved_to == ["mps"]


def test_ssd1b_runtime_uses_fp16_variant_for_mps_loading(tmp_path, monkeypatch):
    from app.runtimes.ssd1b_runtime import SSD1BRuntime

    variants: list[str | None] = []

    class FakeLoadedPipeline:
        def enable_attention_slicing(self):
            return None

        def enable_vae_slicing(self):
            return None

        def to(self, device: str):
            return self

    class FakePipelineClass:
        @staticmethod
        def from_pretrained(*args, **kwargs):
            variants.append(kwargs.get("variant"))
            return FakeLoadedPipeline()

    class FakeTorch:
        float16 = "float16"
        float32 = "float32"

    monkeypatch.setattr("app.runtimes.ssd1b_runtime.preferred_torch_device_type", lambda: "mps", raising=False)
    monkeypatch.setitem(sys.modules, "torch", FakeTorch)
    monkeypatch.setitem(sys.modules, "diffusers", type("FakeDiffusers", (), {"StableDiffusionXLPipeline": FakePipelineClass}))

    runtime = SSD1BRuntime(model_dir=tmp_path / "ssd1b-electric", output_dir=tmp_path / "outputs")
    runtime._build_default_pipeline()

    assert variants == ["fp16"]


def test_ssd1b_runtime_builds_mps_generator(tmp_path, monkeypatch):
    from app.runtimes.ssd1b_runtime import SSD1BRuntime

    devices: list[str] = []

    class FakeGenerator:
        def manual_seed(self, seed: int):
            return self

    class FakeTorch:
        @staticmethod
        def Generator(device: str):
            devices.append(device)
            return FakeGenerator()

    monkeypatch.setattr("app.runtimes.ssd1b_runtime.preferred_torch_device_type", lambda: "mps", raising=False)
    monkeypatch.setitem(sys.modules, "torch", FakeTorch)

    runtime = SSD1BRuntime(model_dir=tmp_path / "ssd1b-electric", output_dir=tmp_path / "outputs")
    runtime._build_generator(321)

    assert devices == ["mps"]
