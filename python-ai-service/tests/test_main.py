from fastapi.testclient import TestClient


class FakeRuntime:
    def __init__(self) -> None:
        self.unload_calls = 0

    def unload(self) -> None:
        self.unload_calls += 1


class FakeRuntimeRegistry:
    def __init__(self) -> None:
        self.runtime = FakeRuntime()

    def build_status(self) -> dict:
        return {"runtime_root": r"G:\electric-ai-runtime", "directories": {}, "models": []}

    def list_models(self) -> dict:
        return {
            "items": [
                {
                    "name": "sd15-electric",
                    "target": "generation",
                    "status": "available",
                }
            ]
        }

    def get_generation_runtime(self, model_name: str):
        assert model_name == "sd15-electric"
        return self.runtime


class FakeGenerationService:
    def generate(self, job, runtime):
        return [{"file_path": rf"G:\electric-ai-runtime\outputs\images\{job.job_id}_0_{job.seed}.png", "seed": job.seed}]


class FakeScoringService:
    def __init__(self) -> None:
        self.last_scoring_model_name = None

    def score_batch(self, job, images):
        self.last_scoring_model_name = job.scoring_model_name
        return [
            {
                **images[0],
                "model_name": job.model_name,
                "visual_fidelity": 80.0,
                "text_consistency": 90.0,
                "physical_plausibility": 70.0,
                "composition_aesthetics": 60.0,
                "total_score": 77.0,
            }
        ]


def test_internal_generate_uses_runtime_registry_and_real_services():
    from app.main import create_app

    scoring_service = FakeScoringService()
    client = TestClient(
        create_app(
            runtime_registry=FakeRuntimeRegistry(),
            generation_service=FakeGenerationService(),
            scoring_service=scoring_service,
        )
    )

    response = client.post(
        "/internal/generate",
        json={
            "job_id": 1,
            "prompt": "A wind turbine farm at sunset",
            "negative_prompt": "blurry",
            "model_name": "sd15-electric",
            "scoring_model_name": "electric-score-v2",
            "seed": 42,
            "steps": 20,
            "guidance_scale": 7.5,
            "width": 512,
            "height": 512,
            "num_images": 1,
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["results"][0]["file_path"].endswith("_0_42.png")
    assert payload["results"][0]["total_score"] == 77.0
    assert scoring_service.last_scoring_model_name == "electric-score-v2"


def test_runtime_endpoints_delegate_to_runtime_registry():
    from app.main import create_app

    client = TestClient(create_app(runtime_registry=FakeRuntimeRegistry()))

    status_response = client.get("/runtime/status")
    models_response = client.get("/runtime/models")

    assert status_response.status_code == 200
    assert status_response.json()["runtime_root"] == r"G:\electric-ai-runtime"
    assert models_response.status_code == 200
    assert models_response.json()["items"][0]["status"] == "available"


def test_internal_generate_keeps_runtime_loaded_for_following_jobs():
    from app.main import create_app

    runtime_registry = FakeRuntimeRegistry()
    client = TestClient(
        create_app(
            runtime_registry=runtime_registry,
            generation_service=FakeGenerationService(),
            scoring_service=FakeScoringService(),
        )
    )

    response = client.post(
        "/internal/generate",
        json={
            "job_id": 2,
            "prompt": "A transformer yard",
            "negative_prompt": "blurry",
            "model_name": "sd15-electric",
            "seed": 24,
            "steps": 20,
            "guidance_scale": 7.5,
            "width": 512,
            "height": 512,
            "num_images": 1,
        },
    )

    assert response.status_code == 200
    assert runtime_registry.runtime.unload_calls == 0


def test_create_app_builds_default_dependencies_lazily(monkeypatch):
    import app.main as main

    calls: list[str] = []

    def fake_registry():
        calls.append("registry")
        return FakeRuntimeRegistry()

    def fake_generator():
        calls.append("generator")
        return FakeGenerationService()

    def fake_scorer(*, release_after_batch=False):
        calls.append(f"scorer:{release_after_batch}")
        return FakeScoringService()

    monkeypatch.setattr(main, "build_runtime_registry", fake_registry)
    monkeypatch.setattr(main, "build_generation_service", fake_generator)
    monkeypatch.setattr(main, "build_scoring_service", fake_scorer)

    app = main.create_app()
    client = TestClient(app)

    assert calls == []

    health_response = client.get("/health")

    assert health_response.status_code == 200
    assert calls == []

    status_response = client.get("/runtime/status")

    assert status_response.status_code == 200
    assert calls == ["registry"]

    generate_response = client.post(
        "/internal/generate",
        json={
            "job_id": 3,
            "prompt": "A wind turbine farm at sunset",
            "negative_prompt": "blurry",
            "model_name": "sd15-electric",
            "scoring_model_name": "electric-score-v2",
            "seed": 42,
            "steps": 20,
            "guidance_scale": 7.5,
            "width": 512,
            "height": 512,
            "num_images": 1,
        },
    )

    assert generate_response.status_code == 200
    assert calls == ["registry", "generator", "scorer:False"]
