from __future__ import annotations

"""FastAPI entrypoint for health checks, runtime probes and internal generation."""

from fastapi import FastAPI

from app.dependencies import build_generation_service, build_runtime_registry, build_scoring_service
from app.schemas.jobs import GenerateJob


def create_app(*, runtime_registry=None, generation_service=None, scoring_service=None) -> FastAPI:
    """Create the app while lazily constructing heavyweight runtime dependencies."""
    registry = runtime_registry
    generator = generation_service
    scorer = scoring_service

    def get_registry():
        nonlocal registry
        if registry is None:
            registry = build_runtime_registry()
        return registry

    def get_generator():
        nonlocal generator
        if generator is None:
            generator = build_generation_service()
        return generator

    def get_scorer():
        nonlocal scorer
        if scorer is None:
            scorer = build_scoring_service(release_after_batch=False)
        return scorer

    app = FastAPI(title="python-ai-service")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/runtime/status")
    def runtime_status() -> dict:
        return get_registry().build_status()

    @app.get("/runtime/models")
    def runtime_models() -> dict:
        return get_registry().list_models()

    @app.post("/internal/generate")
    def generate(request: GenerateJob) -> dict:
        runtime = get_registry().get_generation_runtime(request.model_name)
        generated_images = get_generator().generate(request, runtime)
        scored_results = get_scorer().score_batch(request, generated_images)
        return {
            "code": 0,
            "message": "success",
            "data": {
                "job_id": request.job_id,
                "results": scored_results,
            },
            "trace_id": f"job-{request.job_id}",
        }

    return app


app = create_app()
