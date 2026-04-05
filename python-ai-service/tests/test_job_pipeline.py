from pathlib import Path


class FakeTaskClient:
    def __init__(self) -> None:
        self.statuses: list[tuple[int, str, str, str | None]] = []

    def update_status(self, job_id: int, status: str, stage: str, error_message: str | None = None) -> None:
        self.statuses.append((job_id, status, stage, error_message))


class FakeAssetClient:
    def __init__(self) -> None:
        self.saved_payload: dict | None = None

    def save_results(self, job_id: int, results: list[dict]) -> None:
        self.saved_payload = {"job_id": job_id, "results": results}


class FakeAuditClient:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def record_event(self, event_type: str, payload: dict) -> None:
        self.events.append({"event_type": event_type, "payload": payload})


class FakeRuntime:
    def __init__(self) -> None:
        self.prepared_jobs: list[int] = []

    def prepare(self, job) -> None:
        self.prepared_jobs.append(job.job_id)


class FakeRuntimeRegistry:
    def __init__(self) -> None:
        self.runtime = FakeRuntime()

    def get_generation_runtime(self, model_name: str) -> FakeRuntime:
        assert model_name == "sd15-electric"
        return self.runtime


class FakeGenerationService:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    def generate(self, job, runtime) -> list[dict]:
        runtime.prepare(job)
        if self.fail:
            raise RuntimeError("generation exploded")
        return [{"file_path": str(Path("G:/electric-ai-runtime/outputs/images/job-7.png"))}]


class FakeScoringService:
    def score_batch(self, job, images: list[dict]) -> list[dict]:
        return [
            {
                **image,
                "scores": {
                    "visual_fidelity": 80.0,
                    "text_consistency": 90.0,
                    "physical_plausibility": 70.0,
                    "composition_aesthetics": 60.0,
                    "total_score": 77.5,
                },
            }
            for image in images
        ]


def build_job():
    from app.schemas.jobs import GenerateJob

    return GenerateJob(
        job_id=7,
        prompt="500kV substation in sunset light",
        negative_prompt="blurry",
        model_name="sd15-electric",
        seed=1234,
        steps=30,
        guidance_scale=7.5,
        width=512,
        height=512,
        num_images=1,
    )


def test_job_pipeline_updates_statuses_in_order():
    from app.services.job_pipeline import JobPipeline

    task_client = FakeTaskClient()
    asset_client = FakeAssetClient()
    audit_client = FakeAuditClient()
    pipeline = JobPipeline(
        task_client=task_client,
        asset_client=asset_client,
        audit_client=audit_client,
        runtime_registry=FakeRuntimeRegistry(),
        generation_service=FakeGenerationService(),
        scoring_service=FakeScoringService(),
    )

    pipeline.run(build_job())

    assert task_client.statuses == [
        (7, "preparing", "preparing", None),
        (7, "downloading", "downloading", None),
        (7, "generating", "generating", None),
        (7, "scoring", "scoring", None),
        (7, "persisting", "persisting", None),
        (7, "completed", "completed", None),
    ]
    assert asset_client.saved_payload is not None
    assert asset_client.saved_payload["job_id"] == 7
    assert len(audit_client.events) >= 2


def test_job_pipeline_marks_failed_on_generation_error():
    from app.services.job_pipeline import JobPipeline

    task_client = FakeTaskClient()
    pipeline = JobPipeline(
        task_client=task_client,
        asset_client=FakeAssetClient(),
        audit_client=FakeAuditClient(),
        runtime_registry=FakeRuntimeRegistry(),
        generation_service=FakeGenerationService(fail=True),
        scoring_service=FakeScoringService(),
    )

    pipeline.run(build_job())

    assert task_client.statuses[-1] == (7, "failed", "failed", "generation exploded")
