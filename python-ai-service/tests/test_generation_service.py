from app.schemas.jobs import GenerateJob


class FakeRuntime:
    def __init__(self, result=None) -> None:
        self.calls: list[dict] = []
        self.result = result or [{"file_path": "model/image/test.png"}]

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


def test_generation_service_derives_stable_seed_from_job_id():
    from app.services.generation_service import GenerationService

    runtime = FakeRuntime()
    service = GenerationService()

    images = service.generate(build_job(seed=-1), runtime)

    expected_seed = (9 * 1_103_515_245 + 12_345) % 2_147_483_647
    assert runtime.calls[0]["seed"] == expected_seed
    assert images[0]["seed"] == expected_seed


def test_generation_service_reuses_same_resolved_seed_for_retried_job(monkeypatch):
    from app.services.generation_service import GenerationService

    runtime = FakeRuntime()
    service = GenerationService()
    job = build_job(seed=-1)

    first_images = service.generate(job, runtime)
    second_images = service.generate(job, runtime)

    assert runtime.calls[0]["seed"] == runtime.calls[1]["seed"]
    assert first_images[0]["seed"] == second_images[0]["seed"]


def test_generation_service_keeps_explicit_seed():
    from app.services.generation_service import GenerationService

    runtime = FakeRuntime()
    service = GenerationService()

    images = service.generate(build_job(seed=42), runtime)

    assert runtime.calls[0]["seed"] == 42
    assert images[0]["seed"] == 42
