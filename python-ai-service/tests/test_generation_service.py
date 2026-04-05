from app.schemas.jobs import GenerateJob


class FakeRuntime:
    def __init__(self, result=None) -> None:
        self.calls: list[dict] = []
        self.result = result or [{"file_path": "G:/electric-ai-runtime/outputs/images/test.png"}]

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        return list(self.result)


def build_job(*, seed: int) -> GenerateJob:
    return GenerateJob(
        job_id=9,
        prompt="500kV substation, industrial realism",
        negative_prompt="blurry",
        model_name="sd15-electric",
        seed=seed,
        steps=20,
        guidance_scale=7.5,
        width=512,
        height=512,
        num_images=1,
    )


def test_generation_service_treats_negative_seed_as_random(monkeypatch):
    import app.services.generation_service as generation_service_module
    from app.services.generation_service import GenerationService

    monkeypatch.setattr(
        generation_service_module,
        "secrets",
        type("FakeSecrets", (), {"randbelow": staticmethod(lambda upper: 20260404)})(),
        raising=False,
    )

    runtime = FakeRuntime()
    service = GenerationService()

    images = service.generate(build_job(seed=-1), runtime)

    assert runtime.calls[0]["seed"] == 20260405
    assert images[0]["seed"] == 20260405


def test_generation_service_keeps_explicit_seed():
    from app.services.generation_service import GenerationService

    runtime = FakeRuntime()
    service = GenerationService()

    images = service.generate(build_job(seed=42), runtime)

    assert runtime.calls[0]["seed"] == 42
    assert images[0]["seed"] == 42
